
# import asyncio
import asyncio

from intugle.core import settings
from intugle.core.conceptual_search.graph_based_table_search.networkx_initializers import prepare_networkx_graph
from intugle.core.conceptual_search.graph_based_table_search.retreiver import GraphSearch
from intugle.parser.manifest import ManifestLoader

manifest_loader = ManifestLoader(settings.MODELS_DIR)
manifest_loader.load()
manifest = manifest_loader.manifest

prepare_networkx_graph(manifest)

graph = GraphSearch()

while True:
    print("\n\nEnter query: ")
    query = input()
    if query == "q":
        break
    results = asyncio.run(graph.get_shortlisted_tables(query=query))
    print(results.sort_values(by="score", ascending=False))
    # breakpoint()