import logging

from intugle.analysis.models import DataSet
from intugle.link_predictor.predictor import LinkPredictor
import asyncio
import threading

from typing import TYPE_CHECKING, Any, Awaitable, Dict, List, TypeVar

from intugle.analysis.models import DataSet
from intugle.link_predictor.predictor import LinkPredictor
from intugle.semantic_search import SemanticSearch

if TYPE_CHECKING:
    from intugle.link_predictor.models import PredictedLink

log = logging.getLogger(__name__)

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


class KnowledgeBuilder:
    def __init__(self, data_input: Dict[str, Any] | List[DataSet], domain: str = ""):
        self.datasets: Dict[str, DataSet] = {}
        self.links: list[PredictedLink] = []
        self.domain = domain
        self._semantic_search_initialized = False

        if isinstance(data_input, dict):
            self._initialize_from_dict(data_input)
        elif isinstance(data_input, list):
            self._initialize_from_list(data_input)
        else:
            raise TypeError("Input must be a dictionary of named dataframes or a list of DataSet objects.")
        
    def _initialize_from_dict(self, data_dict: Dict[str, Any]):
        """Creates and processes DataSet objects from a dictionary of raw dataframes."""
        for name, df in data_dict.items():
            dataset = DataSet(df, name=name)
            self.datasets[name] = dataset

    def _initialize_from_list(self, data_list: List[DataSet]):
        """Processes a list of existing DataSet objects"""
        for dataset in data_list:
            if not dataset.name:
                raise ValueError("DataSet objects provided in a list must have a 'name' attribute.")
            self.datasets[dataset.name] = dataset

    def build(self, force_recreate: bool = False):
        import os

        from intugle.core import settings

        # run analysis on all datasets
        for dataset in self.datasets.values():
            file_path = os.path.join(settings.PROJECT_BASE, f"{dataset.name}.yml")
            if os.path.exists(file_path) and not force_recreate:
                print(f"Dataset {dataset.name} already processed. Loading from file.")
                dataset.load_from_yaml(file_path)
                continue
            dataset.run(domain=self.domain, save=True)

        # Initialize the predictor
        self.link_predictor = LinkPredictor(list(self.datasets.values()))

        # Run the prediction
        self.link_predictor.predict(save=True)
        self.links: list[PredictedLink] = self.link_predictor.links

        # Initialize semantic search
        try:
            self.initialize_semantic_search()
        except Exception as e:
            log.warning(f"Semantic search initialization failed during build: {e}")

        return self

    def initialize_semantic_search(self):
        """Initialize the semantic search engine."""
        try:
            print("Initializing semantic search...")
            search_client = SemanticSearch()
            _run_async_in_sync(search_client.initialize())
            self._semantic_search_initialized = True
            print("Semantic search initialized.")
        except Exception as e:
            log.warning(f"Could not initialize semantic search: {e}")
            raise e

    def visualize(self):
        return self.link_predictor.show_graph()

    def search(self, query: str):
        """Perform a semantic search on the knowledge base."""
        if not self._semantic_search_initialized:
            self.initialize_semantic_search()

        try:
            search_client = SemanticSearch()
            return _run_async_in_sync(search_client.search(query))
        except Exception as e:
            log.error(f"Could not perform semantic search: {e}")
            raise e
        
