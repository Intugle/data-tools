import asyncio

from intugle.semantic_search import SemanticSearch


def test_semantic_search_initiaize():
    asyncio.run(SemanticSearch().initiaize())


def test_semantic_search():
    query = "reaction"
    data = asyncio.run(SemanticSearch().search(query))
    data.sort_values(by="score", ascending=False, inplace=True)

    breakpoint()