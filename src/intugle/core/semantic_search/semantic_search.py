import asyncio
import logging
import sys

from typing import Optional

import numpy as np
import pandas as pd

from qdrant_client import models

from intugle.core.llms.embeddings import Embeddings, EmbeddingsType
from intugle.core.semantic_search.models import RelevancyCategory
from intugle.core.semantic_search.utils import relevancy_adder
from intugle.core.settings import settings
from intugle.core.vector_store import VectorStoreService
from intugle.core.vector_store.qdrant import VectorSearchKwargs

log = logging.getLogger(__name__)


# class HybridDenseLateSearch:
#     def __init__(self):
#         pass


class HybridDenseLateSearch:
    def __init__(
        self,
        collection_name: str,
        embeddings: Embeddings,
        threshold_for_less_relevant_result: float = 0.5,
        relevancy_config: Optional[dict] = None,
    ):
        self.collection_name = collection_name
        self.embeddings = embeddings
        self.threshold_for_less_relevant_result = threshold_for_less_relevant_result

        if relevancy_config is None:
            relevancy_config = (
                {
                    RelevancyCategory.MOST_RELEVANT: 0.85,
                    RelevancyCategory.RELEVANT: 0.8,
                    RelevancyCategory.LESS_RELEVANT: 0.75,
                }
            )
        self.relevancy_config = relevancy_config

    @property
    def vector_store(self):
        client_config = {"url": settings.QDRANT_URL, "api_key": settings.QDRANT_API_KEY}
        return VectorStoreService(
            collection_name=self.collection_name, collection_configurations=None, client_config=client_config
        )

    async def __vector_search__(
        self,
        query_vector: np.ndarray | list,
        using: str,
        score_threshold: float = None,
        query_filter: models.Filter = None,
        limit: int = sys.maxsize,
    ) -> pd.DataFrame:
        query_vector = query_vector.tolist() if isinstance(query_vector, np.ndarray) else query_vector

        search_result = pd.DataFrame()

        qdrant_points = await self.vector_store.search(
            query=query_vector,
            search_using=using,
            includes=["metadata"],
            search_kwargs=dict(
                VectorSearchKwargs(
                    search_type="similarity",
                    top_k=limit,
                    filter=query_filter,
                    search_params=models.SearchParams(
                        hnsw_ef=limit,
                        exact=True,
                    ),
                    score_threshold=score_threshold,
                ),
            ),
        )

        search_result = pd.DataFrame(qdrant_points.model_dump()["points"])

        if search_result.shape[0] > 0:
            search_result = search_result[["id", "score", "payload"]].reset_index(drop=True)

            search_result = pd.concat([search_result, pd.json_normalize(search_result.payload)], axis=1)[
                ["score", "column_id", "type"]
            ]

        else:
            log.warning(f"[!] No results found when searched {using}")

        return search_result

    async def fetch(
        self,
        # query_term: str,
        dense_vector: np.ndarray,
        late_vector: np.ndarray,
        add_relevancy: bool = True,
        *args,
        **kwargs,
    ) -> pd.DataFrame:
        hybrid_result = pd.DataFrame()

        filter_condition_column_tag = models.Filter(
            must=[models.FieldCondition(key="type", match=models.MatchAny(any=["column_name", "tag"]))]
        )

        filter_condition_glossary = models.Filter(
            must=[models.FieldCondition(key="type", match=models.MatchValue(value="glossary"))]
        )

        async with asyncio.TaskGroup() as tg:
            task1 = tg.create_task(
                self.__vector_search__(
                    query_vector=dense_vector,
                    using=f"{self.embeddings.model_name}-{EmbeddingsType.DENSE}",
                    score_threshold=self.threshold_for_less_relevant_result,
                    query_filter=filter_condition_column_tag,
                )
            )
            task2 = tg.create_task(
                self.__vector_search__(
                    query_vector=late_vector,
                    using=f"{self.embeddings.model_name}-{EmbeddingsType.LATE}",
                    # score_threshold=self.threshold_for_less_relevant_result,
                    query_filter=filter_condition_glossary,
                )
            )

        try:
            dense_embedding_result = task1.result()
            dense_embedding_result = dense_embedding_result[["column_id", "score"]]
        except Exception as ex:
            log.error(ex)
            log.error(f"[*] Error while performing dense search \nReason: {ex}")
            late_embedding_result_glossary = pd.DataFrame()
            dense_embedding_result = pd.DataFrame()

        try:
            # Do a late embedding search across glossary
            late_embedding_result_glossary = task2.result()
            late_embedding_result_glossary = late_embedding_result_glossary[["column_id", "score"]]
        except Exception as ex:
            log.error(f"[*] Error while performing late search \nReason: {ex}")
            late_embedding_result_glossary = pd.DataFrame()

        if late_embedding_result_glossary.shape[0] > 0:
            # The final score will be total score by no of query embeddings in late vectors
            late_embedding_result_glossary["score"] = late_embedding_result_glossary["score"] / len(late_vector)

            # filter out results that are below designated threshold
            late_embedding_result_glossary = late_embedding_result_glossary.loc[
                late_embedding_result_glossary.score >= self.threshold_for_less_relevant_result
            ].reset_index(drop=True)

        hybrid_result = pd.DataFrame()

        # check if we have results in all cases
        late_shape, dense_shape = (
            late_embedding_result_glossary.shape[0],
            dense_embedding_result.shape[0],
        )

        shapes = [late_shape, dense_shape]

        # Should only merge result if atleast one of the cases of result is present
        if sum(shapes) > 0:
            # filter out results that came out empty
            merging_results = [
                result
                for shape, result in zip(
                    shapes,
                    [
                        late_embedding_result_glossary,
                        dense_embedding_result,
                    ],
                )
                if shape > 0
            ]

            if len(merging_results) == 1:
                # if only one result came then no need to merge

                hybrid_result = merging_results[-1]

            else:
                # merge all non empty results in one go using redude
                hybrid_result = pd.concat(merging_results, axis=0).reset_index(drop=True)[["column_id", "score"]]

        if hybrid_result.shape[0] > 0:
            # Apply max logic to get score
            hybrid_result = hybrid_result.groupby("column_id").agg({"score": "max"}).reset_index()

            if add_relevancy:
                # add the relevancy
                hybrid_result = relevancy_adder(
                    result=hybrid_result,
                    relevancy_scores=self.relevancy_config,
                    i_column="score",
                    o_column="relevancy",
                )

            # hybrid_result.rename(columns={"score": self.hybrid_model}, inplace=True)

        return hybrid_result
    
    async def search(self, query):

        vectors = await self.embeddings.aencode([query], embeddings_types=[EmbeddingsType.DENSE, EmbeddingsType.LATE])

        result = await self.fetch(vectors["dense"][0], vectors["late"][0])

        return result
