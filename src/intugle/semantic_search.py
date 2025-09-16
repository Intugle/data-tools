import asyncio
import threading

from typing import Awaitable, TypeVar

import pandas as pd

from intugle.core import settings
from intugle.core.llms.embeddings import Embeddings
from intugle.core.semantic_search.crud import SemanticSearchCRUD
from intugle.core.semantic_search.semantic_search import HybridDenseLateSearch
from intugle.core.utilities.processing import string_standardization
from intugle.parser.manifest import ManifestLoader

T = TypeVar("T")


def _run_async_in_sync(coro: Awaitable[T]) -> T:
    """
    Runs an async coroutine in a sync context, handling cases where an event loop is already running.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    if loop.is_running():
        result = None
        exc = None

        def thread_target():
            nonlocal result, exc
            try:
                result = asyncio.run(coro)
            except Exception as e:
                exc = e

        thread = threading.Thread(target=thread_target)
        thread.start()
        thread.join()

        if exc:
            raise exc
        return result
    else:
        return loop.run_until_complete(coro)


class SemanticSearch:
    def __init__(
        self, project_base: str = settings.PROJECT_BASE, collection_name: str = settings.VECTOR_COLLECTION_NAME
    ):
        self.manifest_loader = ManifestLoader(project_base)
        self.manifest_loader.load()
        self.manifest = self.manifest_loader.manifest
        self.collection_name = collection_name

        self.project_base = project_base

    def get_column_details(self):
        sources = self.manifest.sources
        models = self.manifest.models

        column_details = []
        for source in sources.values():
            table = source.table
            for column in table.columns:
                metrics = column.profiling_metrics.model_dump()
                count = metrics.get("count", 0)
                distinct_count = metrics.get("distinct_count", 0)
                null_count = metrics.get("null_count", 0)

                uniqueness = distinct_count / count if count > 0 else 0
                completeness = (count - null_count) / count if count > 0 else 0

                column_detail = {
                    "id": f"{table.name}.{column.name}",
                    "column_name": column.name,
                    "column_glossary": column.description,
                    "column_tags": column.tags,
                    "category": column.category,
                    "table_name": table.name,
                    "table_glossary": table.description,
                    "uniqueness": uniqueness,
                    "completeness": completeness,
                    **metrics,
                }
                column_details.append(column_detail)

        for model in models.values():
            for column in model.columns:
                metrics = column.profiling_metrics.model_dump()
                count = metrics.get("count", 0)
                distinct_count = metrics.get("distinct_count", 0)
                null_count = metrics.get("null_count", 0)

                uniqueness = distinct_count / count if count > 0 else 0
                completeness = (count - null_count) / count if count > 0 else 0

                column_detail = {
                    "id": f"{table.name}.{column.name}",
                    "column_name": column.name,
                    "column_glossary": column.description,
                    "column_tags": column.tags,
                    "category": column.category,
                    "table_name": table.name,
                    "table_glossary": table.description,
                    "uniqueness": uniqueness,
                    "completeness": completeness,
                    **metrics,
                }
                column_details.append(column_detail)

        return column_details

    async def _async_initialize(self):
        embeddings = Embeddings(settings.EMBEDDING_MODEL_NAME, settings.TOKENIZER_MODEL_NAME)
        semantic_search_crud = SemanticSearchCRUD(self.collection_name, [embeddings])
        column_details = self.get_column_details()
        column_details = pd.DataFrame.from_records(column_details)
        await semantic_search_crud.initialize(column_details)

    def initialize(self):
        return _run_async_in_sync(self._async_initialize())

    async def _search_async(self, query):
        embeddings = Embeddings(settings.EMBEDDING_MODEL_NAME, settings.TOKENIZER_MODEL_NAME)
        semantic_search = HybridDenseLateSearch(self.collection_name, embeddings)

        data = await semantic_search.search(string_standardization(query))
        return data

    def search(self, query):
        search_results = _run_async_in_sync(self._search_async(query))
        if search_results.shape[0] == 0:
            return search_results
        search_results.sort_values(by="score", ascending=False, inplace=True)

        column_details = self.get_column_details()
        column_details_df = pd.DataFrame.from_records(column_details)
        merged_df = pd.merge(
            search_results, column_details_df, left_on="column_id", right_on="id", how="left"
        ).drop(columns=["id"])
        return merged_df