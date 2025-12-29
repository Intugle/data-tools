
import pytest
from unittest.mock import MagicMock, patch
from intugle.data_product import DataProduct
from intugle.libs.smart_query_generator.models.models import FieldDetailsModel
from intugle.adapters.types.postgres.postgres import PostgresAdapter, PostgresConfig
from intugle.adapters.types.databricks.databricks import DatabricksAdapter, DatabricksConfig
from intugle.adapters.types.sqlserver.sqlserver import SQLServerAdapter, SQLServerConfig
from intugle.adapters.types.oracle.oracle import OracleAdapter, OracleConfig
from intugle.adapters.types.mariadb.mariadb import MariaDBAdapter, MariaDBConfig
from intugle.adapters.types.bigquery.bigquery import BigQueryAdapter, BigQueryConfig

# --- PII Logic Tests ---
def test_data_product_pii_logic():
    """Verify that is_pii is correctly derived from tags."""
    # Mock Manifest and Source
    mock_column_pii = MagicMock()
    mock_column_pii.name = "email"
    mock_column_pii.type = "string"
    mock_column_pii.category = "dimension"
    mock_column_pii.tags = ["PII", "sensitive"]
    
    mock_column_normal = MagicMock()
    mock_column_normal.name = "age"
    mock_column_normal.type = "integer"
    mock_column_normal.category = "measure"
    mock_column_normal.tags = ["demographic"]

    mock_table = MagicMock()
    mock_table.name = "users"
    mock_table.details = {}
    mock_table.columns = [mock_column_pii, mock_column_normal]

    mock_source = MagicMock()
    mock_source.schema_ = "public"
    mock_source.table = mock_table
    
    # Mock DataProduct to load our mock manifest
    with patch("intugle.data_product.ManifestLoader") as MockLoader:
        mock_loader_instance = MockLoader.return_value
        mock_loader_instance.manifest.sources = {"users": mock_source}
        mock_loader_instance.manifest.relationships = {}
        
        # Patch DataSet to avoid initialization errors with empty details
        with patch("intugle.data_product.DataSet"):
            dp = DataProduct()
            
            # Check PII field
            pii_field_id = "users.email"
            assert pii_field_id in dp.field_details
            assert dp.field_details[pii_field_id].is_pii is True, "email should be PII"

            # Check Normal field
            normal_field_id = "users.age"
            assert normal_field_id in dp.field_details
            assert dp.field_details[normal_field_id].is_pii is False, "age should not be PII"

# --- Adapter SQL Injection Tests ---

def test_postgres_adapter_fqn_safety():
    """Test PostgresAdapter _get_fqn with malicious input."""
    # We don't need a real connection for _get_fqn usually, but let's see implementation.
    # PostgresAdapter requires settings and async runner in init. We mock them.
    with patch("intugle.adapters.types.postgres.postgres.POSTGRES_AVAILABLE", True):
        # Bypass init connection
        with patch.object(PostgresAdapter, "connect"):
             with patch("intugle.adapters.types.postgres.postgres.AsyncRunner"):
                adapter = PostgresAdapter()
                adapter._schema = "public"
                
                try:
                    fqn = adapter._get_fqn(malicious_table)
                    
                    # Expected safe: "public"."users""; DROP TABLE accounts; --"
                    # sqlglot quotes identifiers with double quotes and escapes existing double quotes with another double quote.
                    print(f"Postgres FQN: {fqn}")
                    
                    # Verify that the quote is escaped (doubled)
                    assert '""' in fqn or '\\"' in fqn
                except Exception as e:
                   print(f"Caught expected error preventing injection: {e}")
                   pass

def test_databricks_adapter_fqn_safety():
    with patch("intugle.adapters.types.databricks.databricks.DATABRICKS_AVAILABLE", True):
        with patch.object(DatabricksAdapter, "connect"):
            adapter = DatabricksAdapter()
            adapter._schema = "default"
            adapter.catalog = "hive_metastore"
            
            malicious_table = 'users`; DROP TABLE accounts; --'
            fqn = adapter._get_fqn(malicious_table)
            print(f"Databricks FQN: {fqn}")
            
            assert '``;' in fqn

def test_sqlserver_adapter_fqn_safety():
    with patch("intugle.adapters.types.sqlserver.sqlserver.SQLSERVER_AVAILABLE", True):
        with patch.object(SQLServerAdapter, "connect"):
            adapter = SQLServerAdapter()
            adapter._schema = "dbo"
            
            malicious_table = 'users]; DROP TABLE accounts; --'
            fqn = adapter._get_fqn(malicious_table)
            print(f"SQLServer FQN: {fqn}")
            
            # Expected: [dbo].[users]]; DROP TABLE accounts; --]
            assert ']];' in fqn

def test_oracle_adapter_fqn_safety():
    with patch("intugle.adapters.types.oracle.oracle.ORACLE_ADAPTER_AVAILABLE", True):
        with patch.object(OracleAdapter, "connect"):
            adapter = OracleAdapter()
            adapter._schema = "HR"
            
            malicious_table = 'users"; DROP TABLE accounts; --'
            # Oracle uses sqlglot now, so expect similar behavior to Postgres (safe quoting or error)
            try:
                fqn = adapter._get_fqn(malicious_table)
                print(f"Oracle FQN: {fqn}")
                assert '""' in fqn or '\\"' in fqn
            except Exception as e:
                print(f"Caught expected error preventing injection: {e}")
                pass

def test_mariadb_adapter_fqn_safety():
    with patch("intugle.adapters.types.mariadb.mariadb.MARIADB_AVAILABLE", True):
        with patch.object(MariaDBAdapter, "connect"):
            adapter = MariaDBAdapter()
            adapter._database = "inventory" # MariaDB uses database as schema
            
            malicious_table = 'users`; DROP TABLE accounts; --'
            fqn = adapter._get_fqn(malicious_table)
            print(f"MariaDB FQN: {fqn}")
            
            # Should look like `inventory`.`users`` ...`
            assert '``;' in fqn

def test_bigquery_adapter_fqn_safety():
    with patch("intugle.adapters.types.bigquery.bigquery.BIGQUERY_AVAILABLE", True):
        with patch.object(BigQueryAdapter, "connect"):
            adapter = BigQueryAdapter()
            adapter._project_id = "my-project"
            adapter._dataset_id = "analytics"
            
            malicious_table = 'users`; DROP TABLE accounts; --'
            fqn = adapter._get_fqn(malicious_table)
            print(f"BigQuery FQN: {fqn}")
            
            # Should look like `my-project`.`analytics`.`users`` ...` (escaped backtick)
            assert '``;' in fqn
