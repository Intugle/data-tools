import asyncio
import logging
import os
import pickle

from concurrent.futures import ThreadPoolExecutor

import networkx as nx

from intugle.core import settings
from intugle.core.conceptual_search.graph_based_column_search.utils import (
    create_embeddings,
    prepare_chunk_document,
)
from intugle.core.conceptual_search.models import GraphFileName
from intugle.core.conceptual_search.utils import colbert_score_numpy

log = logging.getLogger(__name__)


def build_knowledge_graph(doc):
    """
    Build a knowledge graph from text chunks.

    Args:
        chunks (List[Dict]): List of text chunks with metadata
        model (str): Embedding model name

    Returns:
        Tuple[nx.Graph, List[np.ndarray]]: The knowledge graph and chunk embeddings
    """
    log.info("Building knowledge graph...")

    # Create a graph
    graph = nx.Graph()

    # Create embeddings for all chunks
    log.info("Creating embeddings for chunks...")
    print("*" * 100)
    log.info(f"doc length: {len(doc)}")
    print("*" * 100)
    
    # Run asyncio in a separate thread to avoid "event loop is already running" error in notebooks
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, create_embeddings(doc, recreate=True))
        embeddings = future.result()
    
    # Add nodes to the graph
    print("Adding nodes to the graph...")
    for i, chunk in enumerate(doc):

        # concept_i = chunk.metadata['concepts']
        # Add node with attributes
        graph.add_node(i, source=chunk.metadata['source'])
        # concepts=concept_i,embedding=embeddings[i])
        log.info(f"node {i} added ")
    
    # Connect nodes based on shared concepts
    # embedding_model = PreloadedEmbedding.bge_m3_model
    
    log.info("Creating edges between nodes...")
    weights = []
    for i in range(len(doc)):
        # node_concepts = set(graph.nodes[i]["concepts"])
        concepts_i = doc[i].metadata["concepts"]
        node_concepts = set(concepts_i)

        for j in range(i + 1, len(doc)):
            # Calculate concept overlap
            # other_concepts = set(graph.nodes[j]["concepts"])
            other_concepts = set(doc[j].metadata['concepts'])
            shared_concepts = node_concepts.intersection(other_concepts)

            # If they share concepts, add an edge
            if shared_concepts:

                similarity = colbert_score_numpy(embeddings[i], embeddings[j])

                # Calculate edge weight based on concept overlap and semantic similarity
                concept_score = len(shared_concepts) / min(len(node_concepts), len(other_concepts))

                edge_weight = 0.7 * similarity + 0.3 * concept_score
                
                weights.append(edge_weight)

                # Only add edges with significant relationship
                if edge_weight > 0.95:
                    graph.add_edge(i, j,
                                  weight=edge_weight,
                                  similarity=similarity,
                    )
                # shared_concepts=list(shared_concepts))

    log.info(f"Knowledge graph built with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
    
    return graph, embeddings


def prepare_networkx_graph(manifest, force_recreate=False):

    graph_path = os.path.join(settings.GRAPH_DIR,
                               GraphFileName.FIELD)

    if os.path.exists(graph_path) and not force_recreate:
        print('[!] Column search graph already build ... skipping the step')
        return
    
    docs = prepare_chunk_document(manifest)

    graph, _ = build_knowledge_graph(doc=docs)
    
    os.makedirs(os.path.join(settings.GRAPH_DIR), exist_ok=True)

    # write as pickle
    try:
        with open(graph_path, "wb") as _file:
            pickle.dump(graph, _file, pickle.HIGHEST_PROTOCOL)
    except Exception as ex:
        raise ex
    
    print(f"Graph saved to {graph_path}")
    print(f"Graph created with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")