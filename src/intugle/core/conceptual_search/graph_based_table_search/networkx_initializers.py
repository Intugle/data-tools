import asyncio
import logging
import os
import pickle

from concurrent.futures import ThreadPoolExecutor

import networkx as nx

from intugle.core import settings
from intugle.core.conceptual_search.graph_based_table_search.utils import (
    create_embeddings,
    prepare_chunk_document,
)
from intugle.core.conceptual_search.models import GraphFileName
from intugle.core.conceptual_search.utils import colbert_score_numpy

log = logging.getLogger(__name__)


def build_knowledge_graph(doc):
    """
    Build a knowledge graph from text chunks.
    """
    log.info("Building knowledge graph for tables...")

    graph = nx.Graph()

    log.info("Creating embeddings for table chunks...")
    # Run asyncio in a separate thread to avoid "event loop is already running" error in notebooks
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, create_embeddings(doc, recreate=True))
        embeddings = future.result()
    
    log.info("Adding nodes to the graph...")
    for i, chunk in enumerate(doc):
        graph.add_node(i, source=chunk.metadata['source'])
        log.info(f"Node {i} added for source: {chunk.metadata['source']}")
    
    log.info("Creating edges between nodes...")
    for i in range(len(doc)):
        concepts_i = doc[i].metadata["concepts"]
        node_concepts = set(concepts_i)

        for j in range(i + 1, len(doc)):
            other_concepts = set(doc[j].metadata['concepts'])
            shared_concepts = node_concepts.intersection(other_concepts)

            if shared_concepts:
                similarity = colbert_score_numpy(embeddings[i], embeddings[j])
                concept_score = len(shared_concepts) / min(len(node_concepts), len(other_concepts))
                edge_weight = 0.7 * similarity + 0.3 * concept_score
                
                if edge_weight > 0.7:
                    graph.add_edge(
                        i, j,
                        weight=edge_weight,
                        similarity=similarity,
                        shared_concepts=list(shared_concepts)
                    )

    log.info(f"Knowledge graph built with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
    return graph, embeddings


def prepare_networkx_graph(manifest, force_recreate=False):

    graph_path = os.path.join(settings.GRAPH_DIR, GraphFileName.TABLE)

    if os.path.exists(graph_path) and not force_recreate:
        print('[!] Table search graph already built... skipping the step')
        return
    
    docs = prepare_chunk_document(manifest)

    graph, _ = build_knowledge_graph(doc=docs)
    
    os.makedirs(settings.GRAPH_DIR, exist_ok=True)

    try:
        with open(graph_path, "wb") as _file:
            pickle.dump(graph, _file, pickle.HIGHEST_PROTOCOL)
    except Exception as ex:
        log.error(f"Failed to save graph: {ex}")
        raise ex
    
    print(f"Graph saved to {graph_path}")
    print(f"Graph created with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
