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
    def __init__(self, collection_name: str, embeddings: List[Embeddings], batch_size: Optional[int] = None):
        if not collection_name or not isinstance(collection_name, str):
            raise ValueError("collection_name must be a non-empty string")
        if not embeddings or not isinstance(embeddings, list) or len(embeddings) == 0:
            raise ValueError("embeddings must be a non-empty list of Embeddings")

        self.collection_name = collection_name
        self.embeddings = embeddings
        self.batch_size = batch_size if batch_size is not None else settings.QDRANT_INSERT_BATCH_SIZE

        if self.batch_size <= 0:
            raise ValueError("batch_size must be a positive integer")

        log.info(f"SemanticSearchCRUD initialized with collection_name='{self.collection_name}', "
                f"embeddings_count={len(self.embeddings)}, batch_size={self.batch_size}")

    @property
    def vector_store(self):
        if not settings.QDRANT_URL:
            raise ValueError("QDRANT_URL setting is required but not configured")

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
        """Vectorize content using configured embeddings."""
        if content is None or content.empty:
            log.warning("Empty content provided for vectorization")
            return []

        if not isinstance(content, pd.DataFrame):
            raise ValueError("content must be a pandas DataFrame")

        required_columns = ["content", "type", "column_id"]
        missing_columns = [col for col in required_columns if col not in content.columns]
        if missing_columns:
            raise ValueError(f"Content DataFrame is missing required columns: {missing_columns}")

        tags_and_columns = content.loc[content.type.isin(["tag", "column_name"])].reset_index(drop=True)
        business_glossary = content.loc[content.type.isin(["glossary"])].reset_index(drop=True)

        tags_and_columns_content = tags_and_columns["content"].tolist() if not tags_and_columns.empty else []
        business_glossary_content = business_glossary["content"].tolist() if not business_glossary.empty else []

        log.debug(f"Vectorizing {len(tags_and_columns_content)} tag/column items and {len(business_glossary_content)} glossary items")

        if not tags_and_columns_content and not business_glossary_content:
            log.warning("No content to vectorize")
            return []

        async def run():
            # Run tags col and glossary concurrently
            try:
                coroutines = []
                embedding_map = []
                for embedding in self.embeddings:
                    if tags_and_columns_content:
                        coroutines.append(
                            embedding.aencode(tags_and_columns_content, embeddings_types=[EmbeddingsType.DENSE])
                        )
                        embedding_map.append((embedding, "tags_col"))
                    if business_glossary_content:
                        coroutines.append(
                            embedding.aencode(business_glossary_content, embeddings_types=[EmbeddingsType.LATE])
                        )
                        embedding_map.append((embedding, "glossary"))

                if not coroutines:
                    return {"tags_col": {}, "glossary": {}}

                gathered_results = await asyncio.gather(*coroutines)

                results = {"tags_col": {}, "glossary": {}}
                for (model, typ), result in zip(embedding_map, gathered_results):
                    if typ == "tags_col":
                        results["tags_col"][model] = result
                    else:
                        results["glossary"][model] = result

                return results
            except Exception as ex:
                log.error(f"Vectorization failed: {ex}")
                raise RuntimeError(f"Semantic Search vectorization failed: {ex}") from ex

        # Run all type of embeddings concurrently
        results = await run()

        points = []
        if not tags_and_columns.empty and results["tags_col"]:
            point = self.convert_to_qdrant_point(tags_and_columns, results["tags_col"])
            points.extend(point)
        if not business_glossary.empty and results["glossary"]:
            point = self.convert_to_qdrant_point(business_glossary, results["glossary"])
            points.extend(point)

        log.debug(f"Generated {len(points)} points from vectorization")
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
            # Create keyword index for the "type" payload field
            # This is required for filtering operations on the "type" field
            await vdb.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="type",
                field_type=models.PayloadSchemaType.KEYWORD
            )

    async def initialize(self, column_details: list[dict]):
        """Initialize the semantic search collection with column details."""
        if not column_details or not isinstance(column_details, list):
            raise ValueError("column_details must be a non-empty list of dictionaries")

        log.info(f"Starting initialization with {len(column_details)} column details, batch_size={self.batch_size}")

        try:
            await self.clean_collection()
            log.info("Collection cleaned successfully")
        except Exception as e:
            log.error(f"Failed to clean collection: {e}")
            raise RuntimeError(f"Failed to initialize collection: {e}") from e

        async with self.vector_store as vdb:
            column_details_df = pd.DataFrame(column_details)
            total_batches = (len(column_details_df) + self.batch_size - 1) // self.batch_size
            log.info(f"Processing {len(column_details_df)} columns in {total_batches} batches")

            batch_count = 0
            for batch in batched(column_details_df, self.batch_size):
                batch_count += 1
                try:
                    log.debug(f"Processing batch {batch_count}/{total_batches}")

                    content = list(itertools.starmap(self.create_content_for_vectorization, batch.iterrows()))
                    if not content:
                        log.warning(f"Batch {batch_count} produced no content, skipping")
                        continue

                    content_df = pd.concat(content, axis=0).reset_index(drop=True)
                    if content_df.empty:
                        log.warning(f"Batch {batch_count} content is empty, skipping")
                        continue

                    log.debug(f"Batch {batch_count}: Created {len(content_df)} content items")

                    points = await self.vectorize(content_df)
                    if not points:
                        log.warning(f"Batch {batch_count}: No points generated, skipping")
                        continue

                    log.debug(f"Batch {batch_count}: Generated {len(points)} points")

                    await vdb.bulk_insert(points)
                    log.info(f"Batch {batch_count}/{total_batches} completed successfully")

                except Exception as e:
                    log.error(f"Failed to process batch {batch_count}: {e}")
                    raise RuntimeError(f"Batch processing failed at batch {batch_count}: {e}") from e

        log.info("Semantic search initialization completed successfully")
