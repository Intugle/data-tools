import asyncio

import pandas as pd

from intugle.semantic_search import SemanticSearch


def test_semantic_search_initialize():
    """
    Tests the initialization of the semantic search.
    """
    search_client = SemanticSearch()
    asyncio.run(search_client.initialize())


def test_semantic_search_search():
    """
    Tests the search functionality of the semantic search.
    """
    # Initialize the semantic search
    search_client = SemanticSearch()

    # Perform a search
    query = "reaction"
    data = asyncio.run(search_client.search(query))

    # Assert that the result is a pandas DataFrame
    assert isinstance(data, pd.DataFrame)

    # Assert that the DataFrame is not empty
    assert not data.empty

    # Assert that the DataFrame has the expected columns
    expected_columns = [
        "column_id",
        "score",
        "relevancy",
        "column_name",
        "column_glossary",
        "column_tags",
        "category",
        "table_name",
        "table_glossary",
        "uniqueness",
        "completeness",
        "count",
        "null_count",
        "distinct_count"
    ]
    assert all(col in data.columns for col in expected_columns)

    # Assert that the scores are sorted in descending order
    data.sort_values(by="score", ascending=False, inplace=True)
    assert data["score"].is_monotonic_decreasing
    # Assert that the top result is the expected one
    assert data.iloc[0]["column_id"] == "allergies.reaction2"
