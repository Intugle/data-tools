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
        self, models_dir_path: str = settings.MODELS_DIR, collection_name: str = settings.PROJECT_ID
    ):
        """
        Initialize the SemanticSearch object from a persisted manifest.

        Loads datasets and models metadata from the manifest. This does **not** index
        the data into the vector database—`initialize()` must be called before
        performing searches.

        Parameters
        ----------
        models_dir_path : str, optional
            Directory path where model manifests are stored (default: settings.MODELS_DIR)
        collection_name : str, optional
            Name of the vector database collection used for embeddings
            (default: settings.VECTOR_COLLECTION_NAME)

        Example
        -------
        >>> ss = SemanticSearch(models_dir_path="manifests/", collection_name="my_collection")
        """
        self.manifest_loader = ManifestLoader(models_dir_path)
        self.manifest_loader.load()
        self.manifest = self.manifest_loader.manifest
        self.collection_name = collection_name
        self.models_dir_path = models_dir_path

    def get_column_details(self):
        """
        Extract column metadata from all sources and models in the manifest.

        Returns
        -------
        List[dict]
            A list of dictionaries containing column-level information:
            - id: 'table_name.column_name'
            - column_name, column_glossary, column_tags, category
            - table_name, table_glossary
            - uniqueness, completeness, and all profiling metrics

        Notes
        -----
        - Used internally to create embeddings and for merging search results.
        - Handles both source tables and modeled tables.

        Example
        -------
        >>> details = ss.get_column_details()
        >>> details[0]["column_name"]
        'user_id'
        """
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
        """
        Internal method to index column metadata into the vector database.

        Embeddings are created for all columns and stored in the configured
        collection. Must be run before performing semantic searches.
        """
        embeddings = Embeddings(settings.EMBEDDING_MODEL_NAME, settings.TOKENIZER_MODEL_NAME)
        semantic_search_crud = SemanticSearchCRUD(self.collection_name, [embeddings])
        column_details = self.get_column_details()
        column_details = pd.DataFrame.from_records(column_details)
        await semantic_search_crud.initialize(column_details)

    def initialize(self):
        """
        Index columns into the vector database (sync wrapper).

        Runs the asynchronous `_async_initialize` method in a synchronous context,
        so it can be called directly from regular Python scripts.

        Example
        -------
        >>> ss.initialize()
        """
        return _run_async_in_sync(self._async_initialize())

    async def _search_async(self, query):
        """
        Internal async method to perform semantic search for a given query.

        Parameters
        ----------
        query : str
            User query describing the column or dataset to search for.

        Returns
        -------
        pd.DataFrame
            A DataFrame containing search results with column IDs and scores.
        """
        embeddings = Embeddings(settings.EMBEDDING_MODEL_NAME, settings.TOKENIZER_MODEL_NAME)
        semantic_search = HybridDenseLateSearch(self.collection_name, embeddings)
        data = await semantic_search.search(string_standardization(query))
        return data

    def search(self, query):
        """
        Perform semantic search over the indexed columns (sync method).

        Parameters
        ----------
        query : str
            The search query describing the column or dataset to find.

        Returns
        -------
        pd.DataFrame
            Search results merged with column details, sorted by score in
            descending order. Returns an empty DataFrame if no results found.

        Example
        -------
        >>> results = ss.search("user email columns")
        >>> results.head()
        """
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
