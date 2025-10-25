import asyncio
import logging

import pandas as pd

from langchain_core.documents import Document

from intugle.core.conceptual_search.graph_based_column_search.retreiver import (
    GraphSearch as ColumnGraphSearch,
)
from intugle.core.conceptual_search.graph_based_table_search.retreiver import (
    GraphSearch as TableGraphSearch,
)

log = logging.getLogger(__name__)


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

    def data_products_retriever(
        self,
        query: str,
    ) -> list[Document]:
        """
        Retrieves existing data products.
        NOTE: This is a placeholder and currently returns no documents.
        """
        log.warning(
            f"Attempted to retrieve data products for query: '{query}'. This feature is not yet implemented."
        )
        return []

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
