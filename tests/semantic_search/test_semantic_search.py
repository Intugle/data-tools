import os

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
import yaml

from intugle.models.manifest import Manifest
from intugle.models.resources.model import Column, ColumnProfilingMetrics
from intugle.models.resources.source import Source, SourceTables
from intugle.semantic_search import SemanticSearch

# Pytest marker to skip live tests unless an environment variable is set
requires_live_services = pytest.mark.skipif(
    os.environ.get("INTUGLE_RUN_LIVE_TESTS", "false").lower() != "true",
    reason="Requires INTUGLE_RUN_LIVE_TESTS=true and configured services (Qdrant, Embeddings API)",
)


@pytest.fixture
def mock_manifest() -> Manifest:
    """Creates a simple in-memory Manifest with sample data for indexing."""
    manifest = Manifest()
    manifest.sources = {
        "allergies": Source(
            name="allergies",
            description="Table of patient allergies",
            schema="public",
            database="db",
            table=SourceTables(
                name="allergies",
                description="Records of patient allergic reactions.",
                columns=[
                    Column(
                        name="reaction2",
                        description="Description of the allergic reaction.",
                        profiling_metrics=ColumnProfilingMetrics(
                            count=100, null_count=0, distinct_count=10
                        ),
                    ),
                ],
            ),
        ),
    }
    return manifest


@pytest.fixture
def mock_crud(mocker):
    """Mocks the SemanticSearchCRUD class."""
    mock_instance = MagicMock()
    mock_instance.initialize = AsyncMock()  # Mark the method as async
    mocker.patch(
        "intugle.semantic_search.SemanticSearchCRUD", return_value=mock_instance
    )
    return mock_instance


@pytest.fixture
def mock_search(mocker):
    """Mocks the HybridDenseLateSearch class."""
    mock_instance = MagicMock()
    # Simulate the search result as a DataFrame
    fake_search_result = pd.DataFrame(
        [{"column_id": "allergies.reaction2", "score": 0.95}]
    )
    mock_instance.search = AsyncMock(return_value=fake_search_result)
    mocker.patch(
        "intugle.semantic_search.HybridDenseLateSearch", return_value=mock_instance
    )
    return mock_instance


@pytest.fixture
def mock_embeddings(mocker):
    """Mocks the Embeddings class to avoid real API calls."""
    mock_instance = MagicMock()
    mocker.patch("intugle.semantic_search.Embeddings", return_value=mock_instance)
    return mock_instance


# --- Mocked Tests (Default) ---

def test_semantic_search_initialize_mocked(
    mock_manifest, mock_crud, mock_embeddings
):
    """
    Tests that the initialization process calls the CRUD mock's initialize method.
    """
    # 1. Arrange: Patch the ManifestLoader to return our mock manifest
    with patch("intugle.semantic_search.ManifestLoader") as MockManifestLoader:
        MockManifestLoader.return_value.manifest = mock_manifest

        # 2. Act: Initialize the search client
        search_client = SemanticSearch()
        search_client.initialize()

    # 3. Assert: Verify that the CRUD mock was initialized and its method was called
    mock_crud.initialize.assert_called_once()
    call_args, _ = mock_crud.initialize.call_args
    initialized_df = call_args[0]
    assert isinstance(initialized_df, pd.DataFrame)
    assert "allergies.reaction2" in initialized_df["id"].values


def test_semantic_search_search_mocked(
    mock_manifest, mock_search, mock_embeddings
):
    """
    Tests that the search function correctly processes the mocked results.
    """
    # 1. Arrange: Patch the ManifestLoader
    with patch("intugle.semantic_search.ManifestLoader") as MockManifestLoader:
        MockManifestLoader.return_value.manifest = mock_manifest

        # 2. Act
        search_client = SemanticSearch()
        results_df = search_client.search("reaction")

    # 3. Assert
    mock_search.search.assert_called_once_with("reaction")
    assert isinstance(results_df, pd.DataFrame)
    assert not results_df.empty
    assert "column_id" in results_df.columns
    assert results_df.iloc[0]["column_id"] == "allergies.reaction2"
    assert results_df.iloc[0]["column_name"] == "reaction2"


# --- Live Integration Test (Optional) ---

@pytest.fixture
def live_test_project_dir(tmp_path):
    """
    Creates a temporary directory with a minimal YAML file for the live test,
    ensuring the test doesn't depend on the local project structure.
    """
    project_dir = tmp_path / "live_project"
    project_dir.mkdir()

    # Create a minimal but valid YAML file for the ManifestLoader
    test_yaml_content = {
        "sources": [
            {
                "name": "live_test_db",
                "description": "Live test source",
                "schema": "public",
                "database": "db",
                "table": {
                    "name": "allergies",
                    "description": "Records of patient allergic reactions.",
                    "columns": [
                        {
                            "name": "reaction",
                            "description": "A description of the allergic reaction, such as sneezing or hives.",
                            "profiling_metrics": {"count": 10, "null_count": 0, "distinct_count": 5}
                        }
                    ],
                },
            }
        ]
    }
    with open(project_dir / "allergies.yml", "w") as f:
        yaml.dump(test_yaml_content, f)

    return str(project_dir)


@requires_live_services
def test_live_search_end_to_end(live_test_project_dir):
    """
    Runs an end-to-end test against a real Qdrant server and embedding API.
    This test is skipped unless the `INTUGLE_RUN_LIVE_TESTS` env var is "true".
    """
    # 1. Arrange: Instantiate SemanticSearch with the temporary project directory
    # This will use real clients and APIs because they are not mocked.
    search_client = SemanticSearch(models_dir_path=live_test_project_dir)

    # 2. Act: Run the full initialize and search process
    try:
        search_client.initialize()
        results_df = search_client.search("sneezing")
    except Exception as e:
        pytest.fail(
            f"Live semantic search test failed. Ensure Qdrant is running and "
            f"embedding API credentials are set. Error: {e}"
        )

    # 3. Assert: Check for plausible results
    assert isinstance(results_df, pd.DataFrame)
    assert not results_df.empty
    assert "column_id" in results_df.columns
    assert "score" in results_df.columns
    # The top result should be the 'reaction' column we indexed
    assert results_df.iloc[0]["column_id"] == "allergies.reaction"
