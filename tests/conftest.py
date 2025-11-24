import os
import subprocess
import time

import pytest
import yaml

from dotenv import load_dotenv

# Load environment variables from .env file before any tests are run.
# This makes variables like `INTUGLE_RUN_LIVE_TESTS` available to pytest.
load_dotenv()

# Set dummy LLM provider for tests to avoid ValueError
os.environ.setdefault("LLM_PROVIDER", "openai:gpt-3.5-turbo")
os.environ.setdefault("OPENAI_API_KEY", "dummy-key-for-tests")

# Define the mock data for the YAML files
SOURCE_DATA = {
    "sources": [
        {
            "name": "test_db",
            "description": "Test database source",
            "schema": "public",
            "database": "analytics",
            "table": {
                "name": "users",
                "description": "Users table",
                "columns": [{"name": "id", "type": "integer"}, {"name": "name", "type": "string"}],
                "details": {"path": "dummy.csv", "type": "csv"},
            },
        }
    ]
}

RELATIONSHIP_DATA = {
    "relationships": [
        {
            "name": "orders_to_users",
            "description": "Link between orders and users",
            "source": {"table": "orders", "column": "user_id"},
            "target": {"table": "users", "column": "id"},
            "type": "many_to_one",
        }
    ]
}


@pytest.fixture(scope="session", autouse=True)
def mcp_server(request, tmp_path_factory):
    """
    A session-scoped fixture that automatically starts and stops the MCP server
    if any tests marked with '@pytest.mark.mcp' are scheduled to run.
    """
    # Check if any of the collected tests have the 'mcp' marker
    is_mcp_test_running = any(item.get_closest_marker("mcp") for item in request.session.items)

    if not is_mcp_test_running:
        # If no MCP tests are in the queue, do nothing.
        yield
        return

    # --- Setup Phase ---
    print("\n--- Setting up MCP test server ---")

    # Create a temporary directory that persists for the whole session
    temp_dir = tmp_path_factory.mktemp("mcp_data")

    # Write mock YAML files
    with open(temp_dir / "sources.yml", "w") as f:
        yaml.dump(SOURCE_DATA, f)
    with open(temp_dir / "relationships.yml", "w") as f:
        yaml.dump(RELATIONSHIP_DATA, f)

    # Set environment variable for the server
    env = os.environ.copy()
    env["INTUGLE_PROJECT_BASE"] = str(temp_dir)

    # Start the server as a background process
    server_process = subprocess.Popen(
        ["uv", "run", "intugle-mcp"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Give the server a moment to start
    time.sleep(3)

    # Yield control to the test session
    yield

    # --- Teardown Phase ---
    print("\n--- Tearing down MCP test server ---")
    server_process.terminate()
