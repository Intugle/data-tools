import os

from unittest.mock import MagicMock, patch

import pytest

from intugle.adapters.factory import AdapterFactory
from intugle.adapters.types.mariadb import mariadb as mariadb_module
from intugle.adapters.types.mariadb import models as mariadb_models
from intugle.analysis.models import DataSet
from intugle.core import settings
from intugle.data_product import DataProduct
from intugle.semantic_model import SemanticModel


# Existing unit tests
def test_mariadb_models_validation():
    cfg = {"identifier": "my_table", "type": "mariadb"}
    parsed = mariadb_models.MariaDBConfig.model_validate(cfg)
    assert parsed.identifier == "my_table"
    assert parsed.type == "mariadb"


def test_can_handle_mariadb():
    cfg = {"identifier": "my_table", "type": "mariadb"}
    assert mariadb_module.can_handle_mariadb(cfg) is True


def test_register_no_error():
    factory = AdapterFactory(plugins=[])
    # Mocking availability if not installed in env
    with patch("intugle.adapters.types.mariadb.mariadb.MARIADB_AVAILABLE", True):
        mariadb_module.register(factory)
    # Check if registered
    if mariadb_module.MARIADB_AVAILABLE:
        assert "mariadb" in factory.dataframe_funcs


# Mock tests for Adapter methods (since we might not have live DB)
@pytest.fixture
def mock_mariadb_connection():
    # We patch the module-level 'mariadb' variable in the adapter module
    # Since it might be None if import failed, we just set it to a Mock
    mock_mariadb = MagicMock()
    with patch("intugle.adapters.types.mariadb.mariadb.mariadb", mock_mariadb, create=True):
        mock_conn = MagicMock()
        mock_mariadb.connect.return_value = mock_conn
        yield mock_conn


@patch("intugle.core.settings.settings.PROFILES", {"mariadb": {"user": "u", "password": "p", "host": "h", "database": "db"}})
@patch("intugle.adapters.types.mariadb.mariadb.MARIADB_AVAILABLE", True)
def test_adapter_methods_mocked(mock_mariadb_connection):
    adapter = mariadb_module.MariaDBAdapter()
    
    # Test profile
    mock_cursor = MagicMock()
    mock_mariadb_connection.cursor.return_value = mock_cursor
    
    # Mock return for count
    # Mock return for columns (name, type)
    mock_cursor.fetchall.side_effect = [
        [(100,)],  # Count
        [("col1", "int"), ("col2", "varchar")]  # Columns
    ]
    
    cfg = mariadb_models.MariaDBConfig(identifier="table1")
    profile = adapter.profile(cfg, "table1")
    
    assert profile.count == 100
    assert "col1" in profile.columns


# Integration Tests
RUN_LIVE_TESTS = os.getenv("INTUGLE_RUN_LIVE_TESTS", "false").lower() == "true"


@pytest.fixture(scope="module")
def mariadb_setup():
    if not RUN_LIVE_TESTS:
        yield None
        return

    # Try to import mariadb only if live tests are running
    try:
        import mariadb
    except ImportError:
        pytest.skip("mariadb connector not installed")

    # 1. Get creds from settings
    mariadb_config = settings.PROFILES.get("mariadb")
    if not mariadb_config:
        pytest.skip("No 'mariadb' config found in profiles.yml (settings.PROFILES)")

    # 2. Connect
    try:
        conn = mariadb.connect(
            host=mariadb_config.get("host"),
            port=mariadb_config.get("port"),
            user=mariadb_config.get("user"),
            password=mariadb_config.get("password"),
            database=mariadb_config.get("database"),
            autocommit=True
        )
    except Exception as e:
        pytest.skip(f"Could not connect to MariaDB: {e}")

    cursor = conn.cursor()

    # 3. Create tables
    # Using unique prefixes to avoid collision
    prefix = "intugle_test_maria"
    tables_ddl = {
        f"{prefix}_users": f"""
            CREATE TABLE {prefix}_users (
                id INT PRIMARY KEY,
                name VARCHAR(100),
                email VARCHAR(100)
            )
        """,
        f"{prefix}_orders": f"""
            CREATE TABLE {prefix}_orders (
                order_id INT PRIMARY KEY,
                user_id INT,
                amount DECIMAL(10, 2)
            )
        """
    }

    created_tables = []
    try:
        # Cleanup first
        cursor.execute(f"DROP TABLE IF EXISTS {prefix}_orders")
        cursor.execute(f"DROP TABLE IF EXISTS {prefix}_users")
        cursor.execute(f"DROP VIEW IF EXISTS {prefix}_users_view")

        for name, ddl in tables_ddl.items():
            cursor.execute(ddl)
            created_tables.append(name)
        print("Tables created")

        # 4. Insert data
        cursor.execute(f"INSERT INTO {prefix}_users VALUES (1, 'Alice', 'alice@example.com'), (2, 'Bob', 'bob@example.com')")
        cursor.execute(f"INSERT INTO {prefix}_orders VALUES (101, 1, 50.00), (102, 1, 25.00), (103, 2, 100.00)")
        print("Data inserted")
        yield {
            "tables": created_tables,
            "prefix": prefix,
            "config": mariadb_config
        }

    finally:
        # 5. Cleanup
        try:
            if mariadb_module.MariaDBAdapter._instance and mariadb_module.MariaDBAdapter._instance.connection:
                mariadb_module.MariaDBAdapter._instance.connection.close()
                print("Closed MariaDBAdapter connection")
        except Exception as e:
            print(f"Error closing adapter connection: {e}")

        print("Dropping temporary tables and views")
        cursor.execute(f"DROP VIEW IF EXISTS {prefix}_users_view")
        
        for name in reversed(created_tables):
            cursor.execute(f"DROP TABLE IF EXISTS {name}")
        conn.close()


@pytest.mark.skipif(not RUN_LIVE_TESTS, reason="Live tests not enabled")
def test_mariadb_end_to_end(mariadb_setup, tmp_path):
    """
    End-to-end test for MariaDB adapter.
    """
    
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    
    with patch("intugle.core.settings.settings.MODELS_DIR", str(models_dir)):
        
        datasets = []
        for table in mariadb_setup["tables"]:
            ds_data = mariadb_models.MariaDBConfig(identifier=table, type="mariadb")
            datasets.append(DataSet(data=ds_data, name=table))
        
        sm = SemanticModel(datasets, domain="E-commerce Test")
        sm.build()
        
        assert len(sm.profiling_df) > 0
        users_profile = sm.profiling_df[sm.profiling_df['table_name'] == f"{mariadb_setup['prefix']}_users"]
        assert not users_profile.empty
        assert users_profile.iloc[0]['count'] == 2
        
        dp = DataProduct(models_dir_path=str(models_dir))
        
        view_name = f"{mariadb_setup['prefix']}_users_view"
        etl_model = {
            "name": view_name,
            "fields": [
                {
                    "id": f"{mariadb_setup['prefix']}_users.name",
                    "name": "user_name"
                },
                {
                    "id": f"{mariadb_setup['prefix']}_users.email",
                    "name": "contact_email"
                },
            ]
        }
        
        result_ds = dp.build(etl_model, materialize="view")
        
        df = result_ds.to_df()
        assert len(df) == 2
        assert "contact_email" in df.columns
        assert "Alice" in df["user_name"].values
