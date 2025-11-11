import asyncio
import logging

import pandas as pd

from langchain_core.documents import Document
from qdrant_client import models

from intugle.core import settings
from intugle.core.conceptual_search.graph_based_column_search.retreiver import (
    GraphSearch as ColumnGraphSearch,
)
from intugle.core.conceptual_search.graph_based_table_search.retreiver import (
    GraphSearch as TableGraphSearch,
)
from intugle.core.llms.embeddings import Embeddings, EmbeddingsType
from intugle.core.vector_store import AsyncQdrantService
from intugle.core.vector_store.qdrant import (
    QdrantVectorConfiguration,
    VectorSearchKwargs,
)

log = logging.getLogger(__name__)


def data_products_collection_name():
    return f"{settings.PROJECT_ID}_data_products"


DATA_PRODUCTS_COLLECTION_NAME = data_products_collection_name()


class ConceptualSearchRetrievers:
    def to_documents(self, results: pd.DataFrame) -> list[Document]:
        docs = []
        if results.empty:
            return docs

        for _, row in results.iterrows():
            source = row.get("source", "")
            content = row.get("content", "")
            table_column = source.split("$$##$$")

            if len(table_column) > 1:
                table, column = table_column
                meta_data = {"table": table, "column": column}
            else:
                meta_data = {"table": table_column[0]}

            docs.append(Document(page_content=content, metadata=meta_data))

        return docs

    def __init__(self):
        self.table_graph = TableGraphSearch()
        self.column_graph = ColumnGraphSearch()
        self.embedding_model = Embeddings(
            model_name=settings.EMBEDDING_MODEL_NAME,
            tokenizer_model=settings.TOKENIZER_MODEL_NAME,
        )

    async def data_products_retriever(
        self,
        query: str,
    ) -> list[Document]:
        """
        Retrieves existing data products from the vector store.
        """
        log.info(f"Retrieving data products for query: '{query}'")

        # 1. Vectorize query
        vectors = await self.embedding_model.aencode(
            [query], embeddings_types=[EmbeddingsType.DENSE]
        )
        query_vector = vectors[EmbeddingsType.DENSE][0]
        vector_name = f"{self.embedding_model.model_name}-{EmbeddingsType.DENSE}"

        # 2. Configure Qdrant
        vectors_config = {
            vector_name: models.VectorParams(
                size=self.embedding_model.embeddings_size,
                distance=models.Distance.COSINE,
            )
        }
        configuration = QdrantVectorConfiguration(vectors_config=vectors_config)

        # 3. Search Qdrant
        async with AsyncQdrantService(
            collection_name=DATA_PRODUCTS_COLLECTION_NAME,
            collection_configurations=configuration,
        ) as qdb:
            try:
                results = await qdb.search(
                    query=query_vector,
                    search_using=vector_name,
                    includes=["metadata"],
                    search_kwargs=dict(
                        VectorSearchKwargs(
                            search_type="similarity",
                            score_threshold=0.5,
                            top_k=2,
                            search_params=models.SearchParams(
                                hnsw_ef=128,
                                exact=False,
                            ),
                        )
                    ),
                )
            except Exception as e:
                log.error(
                    f"Failed to search data products collection '{DATA_PRODUCTS_COLLECTION_NAME}': {e}",
                    exc_info=True,
                )
                return []

        if not results or not results.points:
            log.info("No data products found for the query.")
            return []

        # 4. Format results
        formatted_results = [
            Document(
                page_content=res.payload.get("content", ""),
                metadata={
                    "Dimensions": res.payload.get("Dimensions"),
                    "Measures": res.payload.get("Measures"),
                },
            )
            for res in results.points
        ]
        log.info(f"Found {len(formatted_results)} data products.")
        return formatted_results

    async def table_retriever(self, query: str) -> list[Document]:
        results = await self.table_graph.get_shortlisted_tables(query)
        return self.to_documents(results)

    async def column_retriever(
        self, attribute_name: str, attribute_description: str = ""
    ) -> list[Document]:
        # Run column searches concurrently
        results = await asyncio.gather(
            self.column_graph.get_shortlisted_columns(query=attribute_name),
            self.column_graph.get_shortlisted_columns(query=attribute_description),
        )
        results_attribute_name, results_attribue_description = results

        if results_attribute_name.empty and results_attribue_description.empty:
            return []

        results = pd.concat(
            [results_attribute_name, results_attribue_description]
        ).drop_duplicates()

        return self.to_documents(results=results)
