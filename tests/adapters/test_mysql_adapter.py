import os

from unittest.mock import patch

import pandas as pd
import pytest

from intugle.adapters.factory import AdapterFactory
from intugle.adapters.types.mysql import models as mysql_models
from intugle.adapters.types.mysql import mysql as mysql_module
from intugle.analysis.models import DataSet
from intugle.core import settings
from intugle.data_product import DataProduct
from intugle.semantic_model import SemanticModel


# Existing unit tests
def test_mysql_models_validation():
    cfg = {"identifier": "my_table", "type": "mysql"}
    parsed = mysql_models.MySQLConfig.model_validate(cfg)
    assert parsed.identifier == "my_table"


def test_can_handle_mysql():
    cfg = {"identifier": "my_table", "type": "mysql"}
    assert mysql_module.can_handle_mysql(cfg) is True


def test_register_no_error():
    factory = AdapterFactory(plugins=[])
    mysql_module.register(factory)


# Integration Tests
RUN_LIVE_TESTS = os.getenv("INTUGLE_RUN_LIVE_TESTS", "false").lower() == "true"


@pytest.fixture(scope="module")
def mysql_setup():
    if not RUN_LIVE_TESTS:
        yield None
        return

    # Try to import pymysql only if live tests are running
    try:
        import pymysql
    except ImportError:
        pytest.skip("pymysql not installed")

    # 1. Get creds from settings
    mysql_config = settings.PROFILES.get("mysql")
    if not mysql_config:
        pytest.skip("No 'mysql' config found in profiles.yml (settings.PROFILES)")

    # 2. Connect
    try:
        conn = pymysql.connect(
            host=mysql_config.get("host"),
            port=mysql_config.get("port"),
            user=mysql_config.get("user"),
            password=mysql_config.get("password"),
            database=mysql_config.get("database"),
            autocommit=True
        )
    except Exception as e:
        pytest.skip(f"Could not connect to MySQL: {e}")

    cursor = conn.cursor()

    # 3. Create tables
    # Using unique prefixes to avoid collision
    prefix = "intugle_test"
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
        # Note: Foreign Key omitted to test if Intugle can infer it, 
        # or we can add it. Intugle's link prediction works even without explicit FKs usually.
        # But adding it helps validity.
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
            "config": mysql_config
        }

    finally:
        # 5. Cleanup
        # Close the singleton adapter's connection to release any metadata locks
        # The app's adapter might hold an open transaction (from the last SELECT) which blocks DROPs.
        try:
            if mysql_module.MySQLAdapter._instance and mysql_module.MySQLAdapter._instance.connection:
                mysql_module.MySQLAdapter._instance.connection.close()
                print("Closed MySQLAdapter connection")
        except Exception as e:
            print(f"Error closing adapter connection: {e}")

        # Drop views created during tests
        print("Dropping temporary tables and views")
        cursor.execute(f"DROP VIEW IF EXISTS {prefix}_users_view")
        
        for name in reversed(created_tables):  # Drop orders before users
            cursor.execute(f"DROP TABLE IF EXISTS {name}")
        conn.close()


@pytest.mark.skipif(not RUN_LIVE_TESTS, reason="Live tests not enabled")
def test_mysql_end_to_end(mysql_setup, tmp_path):
    """
    End-to-end test for MySQL adapter:
    1. Define DataSet
    2. Build SemanticModel (Profile, Glossaries, Links)
    3. Semantic Search
    4. Create Data Product
    """
    
    # We patch MODELS_DIR so we don't write to the actual project's models folder
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    
    with patch("intugle.core.settings.settings.MODELS_DIR", str(models_dir)):
        
        # 1. Setup Semantic Model
        datasets = []
        for table in mysql_setup["tables"]:
            # Correctly initializing DataSet with MySQLConfig
            ds_data = mysql_models.MySQLConfig(identifier=table, type="mysql")
            datasets.append(DataSet(data=ds_data, name=table))
        
        # Domain is optional but good for glossary
        sm = SemanticModel(datasets, domain="E-commerce Test")
        
        # 2. Build
        # This runs profiling, key id, glossary, link prediction
        sm.build()
        print("Semantic model built")

        # Verify profiling
        assert len(sm.profiling_df) > 0
        users_profile = sm.profiling_df[sm.profiling_df['table_name'] == f"{mysql_setup['prefix']}_users"]
        assert not users_profile.empty
        assert users_profile.iloc[0]['count'] == 2
        
        # Verify Glossary (check if descriptions were generated/assigned)
        # Note: If no LLM configured, this might be empty strings, but the dataframe should exist.
        assert len(sm.glossary_df) > 0
        
        # 3. Semantic Search
        # This step might fail if Qdrant/Embedding model is not reachable.
        # We wrap it to allow partial pass if only DB is available but not Vector DB.
        try:
            results = sm.search("users who spent money")
            # We don't assert specific results as it depends on embeddings/LLM, 
            # but it should return a DataFrame (empty or not).
            assert isinstance(results, pd.DataFrame)
            print("Semantic search executed successfully.")
        except Exception as e:
            print(f"Skipping Semantic Search assertion due to error (likely missing Qdrant/LLM): {e}")

        # 4. Data Product
        dp = DataProduct(models_dir_path=str(models_dir))
        
        # Create a simple view from one table (to avoid link dependency issues if prediction failed)
        view_name = f"{mysql_setup['prefix']}_users_view"
        etl_model = {
            "name": view_name,
            "fields": [
                {
                    "id": f"{mysql_setup['prefix']}_users.name",
                    "name": "user_name"
                },
                {
                    "id": f"{mysql_setup['prefix']}_users.email",
                    "name": "contact_email"
                },
                {
                    "id": f"{mysql_setup['prefix']}_orders.amount",
                    "name": "amount",
                    "category": "measure",
                    "measure_func": "sum"
                },
            ]
        }
        
        # Build Data Product (creates view in MySQL)
        result_ds = dp.build(etl_model, materialize="view")
        print("Data Product built")
        
        assert result_ds.name == view_name
        
        # Verify data from the view
        df = result_ds.to_df()
        assert len(df) == 2
        assert "contact_email" in df.columns
        assert "Alice" in df["user_name"].values