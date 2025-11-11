# import pickle
import _pickle as pickle
import heapq
import logging
import os
import sys

import pandas as pd

from qdrant_client import models

from intugle.core import settings
from intugle.core.conceptual_search.graph_based_column_search.utils import (
    CONCEPTUAL_SEARCH_COLLECTION_NAME,
)
from intugle.core.conceptual_search.models import GraphFileName
from intugle.core.conceptual_search.utils import clean_query
from intugle.core.llms.embeddings import Embeddings, EmbeddingsType
from intugle.core.vector_store import AsyncQdrantService
from intugle.core.vector_store.qdrant import VectorSearchKwargs

log = logging.getLogger(__name__)


class GraphSearch:
    def __init__(self):
        self.collection_name = CONCEPTUAL_SEARCH_COLLECTION_NAME
        self.graph = self.fetch_graph_from_directory()
        self.embedding_model = Embeddings(
            model_name=settings.EMBEDDING_MODEL_NAME,
            tokenizer_model=settings.TOKENIZER_MODEL_NAME,
        )

    @classmethod
    def fetch_graph_from_directory(cls):
        graph_path = os.path.join(settings.GRAPH_DIR, GraphFileName.FIELD)

        if os.path.exists(graph_path):
            log.info(f"Graph file found at {graph_path}")
            with open(graph_path, "rb") as _file:
                graph = pickle.load(_file)
            return graph
        else:
            log.error(f"Graph file not found at {graph_path}")
            return None

    async def traverse_graph(self, query: str, graph, top_k=2, max_depth=2):
        """
        Traverse the knowledge graph to find relevant information for the query.
        """
        # Vectorize the query using the standard embedding model
        vectors = await self.embedding_model.aencode(
            [query], embeddings_types=[EmbeddingsType.LATE]
        )
        query_vector = vectors[EmbeddingsType.LATE][0]

        vector_name = f"{self.embedding_model.model_name}-{EmbeddingsType.LATE}"

        async with AsyncQdrantService(collection_name=self.collection_name, collection_configurations={}) as qdb:
            log.info(f"Traversing graph for query: {query}")

            search_result = await qdb.search(
                query=query_vector,
                search_using=vector_name,
                includes=["metadata"],
                search_kwargs=dict(
                    VectorSearchKwargs(
                        search_type="similarity",
                        top_k=sys.maxsize,
                        search_params=models.SearchParams(
                            hnsw_ef=sys.maxsize,
                            exact=True,
                        ),
                    ),
                ),
            )

        if not search_result or not search_result.points:
            return [], [], pd.DataFrame()

        points_data = [p.model_dump() for p in search_result.points]
        search_df = pd.DataFrame(points_data)

        if search_df.empty:
            return [], [], pd.DataFrame()

        search_df = pd.concat(
            [search_df.drop("payload", axis=1), pd.json_normalize(search_df["payload"])],
            axis=1,
        )
        search_df = search_df[["score", "source", "row", "content"]]
        search_df["score"] = search_df["score"] / len(query_vector)
        search_df.set_index("row", inplace=True)

        similarities = list(search_df["score"].to_dict().items())
        similarities.sort(key=lambda x: x[1], reverse=True)

        starting_nodes = [node for node, _ in similarities[:top_k]]
        log.info(f"Starting traversal from {len(starting_nodes)} nodes")

        visited = set()
        traversal_path = []
        results = []
        queue = []

        for node in starting_nodes:
            # Find the similarity score for the node
            score = next((s for n, s in similarities if n == node), 0)
            heapq.heappush(queue, (-score, node))

        while queue and len(results) < (top_k * 3):
            _, node = heapq.heappop(queue)
            if node in visited or node not in graph:
                continue

            visited.add(node)
            traversal_path.append(node)
            results.append({"node_id": node, "source": graph.nodes[node]["source"]})

            if len(traversal_path) < max_depth:
                neighbors = [
                    (neighbor, graph[node][neighbor]["weight"])
                    for neighbor in graph.neighbors(node)
                    if neighbor not in visited
                ]
                for neighbor, weight in sorted(neighbors, key=lambda x: x[1], reverse=True):
                    heapq.heappush(queue, (-weight, neighbor))

        log.info(f"Graph traversal found {len(results)} relevant chunks")
        return results, traversal_path, search_df

    async def get_shortlisted_columns(self, query: str):
        """
        Get shortlisted tables based on the query.
        Args:
            subscription_id (str): Subscription ID
            query (str): User query
        Returns:
            List[Dict]: Shortlisted tables with relevant information
        """

        if self.graph is None:
            log.error("Graph not found. Please create the graph first.")
            return []

        log.info("Graph loaded successfully")

        query = clean_query(query)
        
        _, traversal_path, search_result = await self.traverse_graph(
            query,
            self.graph,
            top_k=int(settings.NETWORKX_GRAPH_TOP_K_COLUMN),
            max_depth=int(settings.NETWORKX_GRAPH_MAX_DEPTH_COLUMN),
        )

        shortlisted_columns = search_result.loc[[i for i in traversal_path]]

        return shortlisted_columns
