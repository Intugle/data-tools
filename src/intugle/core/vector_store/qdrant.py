import logging
import sys

from typing import Any, Dict, List, Literal, Mapping, Optional

import numpy as np
import qdrant_client.models as models

from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient
from qdrant_client.conversions import common_types as qdrant_types

from intugle.core.vector_store.utils import maximal_marginal_relevance

log = logging.getLogger(__name__)


class QdrantVectorConfiguration(BaseModel):

    vectors_config: Optional[qdrant_types.VectorParams | Mapping[str, qdrant_types.VectorParams]] = None

    sparse_vectors_config: Optional[Mapping[str, qdrant_types.SparseVectorParams]] = None


# Used for standardization

class VDocument(BaseModel):

    id: Optional[str | int] = None

    page_content: Optional[str] = None

    metadata: Optional[Dict[str, Any]] = None

    options: Dict[str, Any] = {}  # Refere to QDocumentOptions

    embeddings: Optional[Dict[str, List[float] | List[List[float]]]] = None


# Used for standardization
class VectorSearchKwargs(BaseModel):
    search_type: Literal["similarity", "mmr", "hybrid"] = "similarity"
    top_k: Optional[int] = None
    score_threshold: Optional[float] = None
    fetch_k: Optional[int] = None
    filter: Optional[models.Filter] = None
    prefetch_using: List[str] = None
    search_params: Optional[models.SearchParams] = None
    lambda_mult: Optional[float] = None

    def model_post_init(self, __context__):
        if self.search_type == "similarity":
            if self.top_k is None and self.score_threshold is None:
                raise ValueError("did not pass top k or threshold")
        elif self.search_type == "mmr":
            if (self.fetch_k is None and self.score_threshold is None) or self.top_k is None:
                raise ValueError("did not pass fetch k or threshold or top k")
        elif self.search_type == "hybrid":
            if self.prefetch_using is None:
                raise ValueError("did not pass prefetch using")
        else:
            raise ValueError("search type not similarity, mmr, hybrid")


class AsyncQdrantService:
    def __init__(
        self, collection_name: str, collection_configurations: QdrantVectorConfiguration, client_config: dict = {}
    ):
        self.collection_name = collection_name
        if isinstance(collection_configurations, Dict):
            collection_configurations = QdrantVectorConfiguration(**collection_configurations)
        self.collection_configurations = collection_configurations
        self.client_config = client_config
        self._client = None

    async def __aenter__(self) -> 'AsyncQdrantService':
        await self.create_collection()
        return self

    @property
    def client(self):
        if self._client is None:
            log.debug("AsyncQdrantClient: init")
            self._client = AsyncQdrantClient(**self.client_config)
        return self._client

    async def __aexit__(self, *args, **kwargs):
        if isinstance(self.client, AsyncQdrantClient):
            await self.client.close()
            log.debug("AsyncQdrantService: closed")
        else:
            log.warning("client is not of type AsyncQdrantClient")

    async def delete_collection(self) -> bool:
        try:
            deleted = await self.client.delete_collection(self.collection_name)
            if deleted:
                log.debug(f"AsyncQdrantService: deleted collection {self.collection_name}")
            else:
                log.warning(f"AsyncQdrantService: couldn't delete collection {self.collection_name}")
            return deleted
        except Exception as e:
            log.error(f"AsyncQdrantService: Couldn't delete collection, reason: {e}")
            raise e

    async def create_collection(
        self,
    ) -> bool:
        try:
            exists = await self.client.collection_exists(collection_name=self.collection_name)

            if exists:
                log.debug(f"AsyncQdrantService: collection {self.collection_name} already exists")
                return True

            created = await self.client.create_collection(
                collection_name=self.collection_name, **(dict(self.collection_configurations))
            )
            if created:
                log.debug(f"AsyncQdrantService: created collection {self.collection_name}")
            else:
                log.warning(f"AsyncQdrantService: couldn't create collection {self.collection_name}")
            return created

        except Exception as e:
            log.error(f"AsyncQdrantService: Couldn't create collection, reason: {e}")
            raise e

    async def count(self) -> qdrant_types.CountResult:
        try:
            return await self.client.count(collection_name=self.collection_name)
        except Exception as e:
            log.error(f"AsyncQdrantService: Couldn't count collection, reason: {e}")
            raise e

    def bulk_insert(self, points: models.PointStruct | List[models.PointStruct]):
        try:
            result = self.upload_point(points)
            log.debug(f"Upload Status: {result}")
            return result
        except Exception as e:
            log.error(f"Couldn't bulk insert data: {e}")
            raise e

    def upload_point(self, points):
        try:
            self.client.upload_points(
                collection_name=self.collection_name,
                points=points,
                parallel=1,  # number of vectors points to insert parallely,
                max_retries=5,
            )
            log.debug(f"batch uploaded: {len(points)}")
            return True
        except Exception as e:
            log.error(f"Coulnd't uploading points: {e}")
            raise e

    async def get(
        self,
        ids: int | List[int] | str | List[str] = None,
        filter: models.Filter = None,
        includes: List[Literal["metadata", "embeddings"]] = [],
        return_document: Optional[bool] = True,
    ):
        try:
            with_payload = False
            with_vectors = False
            for include in includes:
                if include == "metadata":
                    with_payload = True
                elif include == "embeddings":
                    with_vectors = True
            result = []
            if ids is not None:
                _ids = []
                if isinstance(ids, (int, str)):
                    _ids.append(ids)
                elif isinstance(ids, List):
                    _ids.extend(ids)
                else:
                    raise TypeError("ids is neither int or str or list")
                result = await self.client.retrieve(
                    collection_name=self.collection_name,
                    ids=_ids,
                    with_payload=with_payload,
                    with_vectors=with_vectors,
                )
            # NOTE: this might become issue later, need to research
            elif filter is not None:
                result, _ = await self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=filter,
                    limit=sys.maxsize,
                    with_payload=with_payload,
                    with_vectors=with_vectors,
                )
            else:
                result, _ = await self.client.scroll(
                    collection_name=self.collection_name,
                    limit=sys.maxsize,
                    with_payload=with_payload,
                    with_vectors=with_vectors,
                )
            if return_document:
                documents: List[VDocument] = []
                for record in result:
                    page_content = record.payload.get("content", None) if record.payload is not None else None
                    if page_content is not None:
                        record.payload.pop("content")
                    documents.append(
                        VDocument(
                            id=record.id,
                            page_content=page_content,
                            metadata=record.payload,
                            embeddings=record.vector,
                        )
                    )
                return documents
            else:
                return result
        except Exception as e:
            log.error(f"Couldn't get from qdrant: {e}")
            raise e

    # NOTE: Don't use numerical ids as it causes issue in deletion
    async def delete(
        self,
        ids: int | str | List[int] | List[str] = None,
        filter: models.Filter = None,
    ) -> bool:
        try:
            if ids is not None:
                points_selector = None
                if isinstance(ids, (str, int)):
                    points_selector = models.PointIdsList(points=[ids])
                elif isinstance(ids, list):
                    points_selector = models.PointIdsList(points=[*ids])
                else:
                    raise TypeError("ids is neither list or ids")
                result = await self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=points_selector,
                )
            elif filter is not None:
                result = await self.client.delete(collection_name=self.collection_name, points_selector=filter)
            return result.status == models.UpdateStatus.COMPLETED
        except Exception as e:
            log.error(f"Couldn't delete from qdrant: {e}")
            raise e

    async def search(
        self,
        query: str | np.ndarray,
        search_using: str,
        search_kwargs: VectorSearchKwargs = {},
        includes: List[Literal["metadata", "embeddings"]] = [],
    ) -> models.QueryResponse:
        with_payload = False
        with_vectors = False
        for include in includes:
            if include == "metadata":
                with_payload = True
            elif include == "embeddings":
                with_vectors = True

        if not isinstance(query, (list, np.ndarray)):
            raise ValueError(f"[!] Async QdrantClient: Query can be only list of floating point values not {type(str)}")

        search_type = search_kwargs.get("search_type", "similarity")
        if search_type == "similarity":
            result = await self.client.query_points(
                collection_name=self.collection_name,
                query=query,
                using=search_using,
                query_filter=search_kwargs.get("filter", None),
                search_params=search_kwargs.get("search_params", None),
                limit=search_kwargs.get("top_k", None),
                with_payload=with_payload,
                with_vectors=with_vectors,
                score_threshold=search_kwargs.get("score_threshold", None),
            )
        elif search_type == "mmr":
            log.debug(f"mmr search using {search_using}")
            result = await self.client.query_points(
                collection_name=self.collection_name,
                query=query,
                using=search_using,
                query_filter=search_kwargs.get("filter", None),
                search_params=search_kwargs.get("search_params", None),
                limit=search_kwargs.get("fetch_k", None),
                with_payload=with_payload,
                with_vectors=True,
                score_threshold=search_kwargs.get("score_threshold", None),
            )

            result = result.points
            if len(result):
                vectors = [point.vector.get(search_using) for point in result]
                indexes = maximal_marginal_relevance(
                    query_embedding=np.array(query),
                    embedding_list=vectors,
                    lambda_mult=search_kwargs.get("lambda_mult", 0.5),
                    k=search_kwargs.get("top_k", 4),
                )

                if with_vectors:
                    result = [result[i] for i in indexes]
                else:
                    result = [self._remove_vector(result[i]) for i in indexes]
        elif search_type == "hybrid":
            log.debug("hybrid search")
            raise NotImplementedError("[!] Hybrid search not implemented")
        return result

    def _remove_vector(self, point: models.PointStruct) -> models.ScoredPoint:
        _d_ = point.model_dump()
        _d_.pop("vector")
        return models.ScoredPoint(**_d_)
