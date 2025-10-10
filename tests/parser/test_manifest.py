import yaml

from intugle.parser.manifest import ManifestLoader


def test_manifest_loader_is_isolated(tmp_path):
    """
    Tests that the ManifestLoader can correctly parse YAML files from a given
    directory in an isolated environment.
    """
    # 1. Arrange: Create dummy YAML files in a temporary directory.
    
    # Create a dummy source file
    source_data = {
        "sources": [
            {
                "name": "test_db",
                "description": "Test database source",
                "schema": "public",
                "database": "analytics",
                "table": {
                    "name": "users",
                    "description": "Users table",
                    "columns": [{"name": "id", "type": "integer"}],
                },
            }
        ]
    }
    source_file = tmp_path / "sources.yml"
    with open(source_file, "w") as f:
        yaml.dump(source_data, f)

    # Create a dummy relationship file
    relationship_data = {
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
    relationship_file = tmp_path / "relationships.yml"
    with open(relationship_file, "w") as f:
        yaml.dump(relationship_data, f)

    # 2. Act: Initialize the loader with the temporary path and load the files.
    manifest_loader = ManifestLoader(str(tmp_path))
    manifest_loader.load()
    manifest = manifest_loader.manifest

    # 3. Assert: Verify that the content was loaded correctly.
    assert manifest is not None
    
    # Check that the source was loaded
    assert len(manifest.sources) == 1
    assert "users" in manifest.sources
    assert manifest.sources["users"].table.name == "users"
    assert len(manifest.sources["users"].table.columns) == 1
    assert manifest.sources["users"].table.columns[0].name == "id"

    # Check that the relationship was loaded
    assert len(manifest.relationships) == 1
    assert "orders_to_users" in manifest.relationships
    assert manifest.relationships["orders_to_users"].target.table == "users"
