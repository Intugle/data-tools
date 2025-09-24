import asyncio
import itertools
import logging

from typing import List, Optional
from uuid import uuid4

import pandas as pd

from qdrant_client import models

from intugle.core.llms.embeddings import Embeddings, EmbeddingsType
from intugle.core.semantic_search.utils import batched
from intugle.core.settings import settings
from intugle.core.utilities.processing import string_standardization
from intugle.core.vector_store import VectorStoreService
from intugle.core.vector_store.qdrant import QdrantVectorConfiguration

log = logging.getLogger(__name__)


class SemanticSearchCRUD:
    def __init__(self, collection_name: str, embeddings: List[Embeddings], batch_size: int = 30):
        self.collection_name = collection_name
        self.embeddings = embeddings
        self.batch_size = batch_size

    @property
    def vector_store(self):
        client_config = {"url": settings.QDRANT_URL, "api_key": settings.QDRANT_API_KEY}
        return VectorStoreService(
            collection_name=self.collection_name,
            collection_configurations=self.configuration,
            client_config=client_config,
        )

    @property
    def configuration(self):
        embeddings_configurations = {}
        for embedding in self.embeddings:
            config = {
                f"{embedding.model_name}-{EmbeddingsType.DENSE}": models.VectorParams(
                    size=embedding.embeddings_size, distance=models.Distance.COSINE
                ),
                f"{embedding.model_name}-{EmbeddingsType.LATE}": models.VectorParams(
                    size=embedding.embeddings_size,
                    distance=models.Distance.COSINE,
                    multivector_config=models.MultiVectorConfig(comparator=models.MultiVectorComparator.MAX_SIM),
                ),
            }
            embeddings_configurations = {**embeddings_configurations, **config}

        configuration = QdrantVectorConfiguration(vectors_config=embeddings_configurations)

        return configuration

    def create_content_for_vectorization(self, _: int, row: pd.Series) -> pd.DataFrame:
        """
        Generate Contents for Vectorization from all the column details 
        (i.e Column Name, Business Tags, Business Glossary)

        Args:
            i (int): integer
            row (pd.Series): a column information as pandas series level

        Returns:
            pd.DataFrame: returns pandas dataframe with contents of the columns.
        """

        tags_content = []
        glossary_content = []
        column_name_content = []

        if len(row["column_tags"]) > 0:
            tags_content = [
                {
                    "content": tag,
                    "type": "tag",
                }
                for tag in row["column_tags"]
            ]

        if not pd.isna(row["column_glossary"]):
            glossary_content = [
                {
                    "content": row["column_glossary"],
                    "type": "glossary",
                }
            ]

        if not pd.isna(row["column_name"]):
            column_name_content = [
                {
                    "content": row["column_name"],
                    "type": "column_name",
                }
            ]

        final_consolidated_content = pd.DataFrame(tags_content + glossary_content + column_name_content)

        if final_consolidated_content.shape[0] <= 0:
            return pd.DataFrame()

        final_consolidated_content["column_id"] = row["id"]

        # The content needs to be cleaned using String Standardization Methods
        final_consolidated_content["content"] = final_consolidated_content.content.apply(string_standardization)

        return final_consolidated_content[final_consolidated_content.content != ""]

    async def vectorize(self, content: pd.DataFrame) -> List[models.PointStruct]:
        tags_and_columns = content.loc[content.type.isin(["tag", "column_name"])].reset_index(drop=True)
        business_glossary = content.loc[content.type.isin(["glossary"])].reset_index(drop=True)

        tags_and_columns_content = tags_and_columns["content"].tolist()
        business_glossary_content = business_glossary["content"].tolist()
        log.info(f"tags_column: {tags_and_columns_content}")
        log.info(f"business glossary: {business_glossary_content}")

        async def run():
            # Run tags col and glossary concurrenty
            try:
                coroutines = []
                embedding_map = []
                for embedding in self.embeddings:
                    coroutines.append(
                        embedding.aencode(tags_and_columns_content, embeddings_types=[EmbeddingsType.DENSE])
                    )
                    embedding_map.append((embedding, "tags_col"))
                    coroutines.append(
                        embedding.aencode(business_glossary_content, embeddings_types=[EmbeddingsType.LATE])
                    )
                    embedding_map.append((embedding, "glossary"))

                gathered_results = await asyncio.gather(*coroutines)

                results = {"tags_col": {}, "glossary": {}}
                for (model, typ), result in zip(embedding_map, gathered_results):
                    if typ == "tags_col":
                        results["tags_col"][model] = result
                    else:
                        results["glossary"][model] = result

                return results
            except Exception as ex:
                raise Exception(f"[!] Semantic Search: Couldnot vectorize => {ex}")

        # Run all type of embeddings concurrenlty
        results = await run()

        points = []
        point = self.convert_to_qdrant_point(tags_and_columns, results["tags_col"])
        points.extend(point)
        point = self.convert_to_qdrant_point(business_glossary, results["glossary"])
        points.extend(point)

        return points

    @staticmethod
    def convert_to_qdrant_point(
        content: pd.DataFrame, embeddings: dict[Embeddings, dict], ids: Optional[list[int]] = None
    ):
        if ids is None:
            ids = [str(uuid4()) for _ in content]
        points = []
        for idx, row in content.iterrows():
            payload = {"column_id": row["column_id"], "type": row["type"]}
            vectors = {}
            for embedding_model, embedding in embeddings.items():
                for key, embed in embedding.items():
                    vectors[f"{embedding_model.model_name}-{key}"] = embed[idx]
            points.append(models.PointStruct(id=str(uuid4()), vector=vectors, payload=payload))

        return points

    @staticmethod
    def convert_to_qdrant_points(
        content: pd.DataFrame,
        embeddings_ada: List[float],
        embeddings_bge: List[float],
        vector_name_ada: EmbeddingsType,
        vector_name_bge: EmbeddingsType,
        ids: Optional[int] = None,
    ):
        points = []
        if ids is None:
            ids = [str(uuid4()) for _ in embeddings_ada]
        for (_, row), vector_ada, vector_bge_m3, _id in zip(content.iterrows(), embeddings_ada, embeddings_bge, ids):
            payload = {"column_id": row["column_id"], "type": row["type"]}
            points.append(
                models.PointStruct(
                    id=_id,
                    vector={
                        vector_name_ada: vector_ada,
                        vector_name_bge: vector_bge_m3,
                    },
                    payload=payload,
                )
            )
        return points

    async def clean_collection(self):
        async with self.vector_store as vdb:
            await vdb.delete_collection()
            await vdb.create_collection()

    async def initialize(self, column_details: list[dict]):
        await self.clean_collection()
        async with self.vector_store as vdb:
            column_details = pd.DataFrame(column_details)

            for batch in batched(column_details, self.batch_size):
                content = list(itertools.starmap(self.create_content_for_vectorization, batch.iterrows()))

                content = pd.concat(content, axis=0).reset_index(drop=True)

                points = await self.vectorize(content)

                await vdb.bulk_insert(points)
