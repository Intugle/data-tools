from unittest.mock import MagicMock, patch

import pytest

from intugle.adapters.types.bigquery.bigquery import (
    BIGQUERY_AVAILABLE,
    BigQueryAdapter,
    can_handle_bigquery,
)
from intugle.adapters.types.bigquery.models import BigQueryConfig, BigQueryConnectionConfig


@pytest.fixture
def mock_bigquery_client():
    """Mock BigQuery client."""
    with patch("intugle.adapters.types.bigquery.bigquery.bigquery") as mock_bq:
        mock_client = MagicMock()
        mock_bq.Client.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_settings():
    """Mock settings with BigQuery configuration."""
    with patch("intugle.adapters.types.bigquery.bigquery.settings") as mock_settings:
        mock_settings.PROFILES = {
            "bigquery": {
                "project_id": "test-project",
                "dataset": "test_dataset",
                "name": "test_bigquery_source",
                "location": "US",
            }
        }
        yield mock_settings


@pytest.fixture
def bigquery_config():
    """Create a test BigQuery config."""
    return BigQueryConfig(identifier="test_table", type="bigquery")


@pytest.mark.skipif(not BIGQUERY_AVAILABLE, reason="BigQuery dependencies not installed")
class TestBigQueryAdapterContract:
    """Test that BigQueryAdapter implements the Adapter interface correctly."""

    def test_implements_required_methods(self, mock_settings, mock_bigquery_client):
        """Test that all abstract methods are implemented."""
        adapter = BigQueryAdapter()
        
        # Check all abstract methods exist
        assert hasattr(adapter, "profile")
        assert hasattr(adapter, "column_profile")
        assert hasattr(adapter, "load")
        assert hasattr(adapter, "execute")
        assert hasattr(adapter, "to_df")
        assert hasattr(adapter, "to_df_from_query")
        assert hasattr(adapter, "create_table_from_query")
        assert hasattr(adapter, "create_new_config_from_etl")
        assert hasattr(adapter, "intersect_count")
        assert hasattr(adapter, "get_composite_key_uniqueness")
        assert hasattr(adapter, "intersect_composite_keys_count")
        assert callable(adapter.profile)
        assert callable(adapter.column_profile)

    def test_inherits_from_adapter(self, mock_settings, mock_bigquery_client):
        """Test that BigQueryAdapter inherits from Adapter base class."""
        from intugle.adapters.adapter import Adapter
        
        adapter = BigQueryAdapter()
        assert isinstance(adapter, Adapter)

    def test_singleton_pattern(self, mock_settings, mock_bigquery_client):
        """Test that BigQueryAdapter follows singleton pattern."""
        # Reset singleton
        BigQueryAdapter._instance = None
        BigQueryAdapter._initialized = False
        
        adapter1 = BigQueryAdapter()
        adapter2 = BigQueryAdapter()
        assert adapter1 is adapter2

    def test_registered_in_factory(self):
        """Test that BigQueryAdapter is registered in the adapter factory."""
        from intugle.adapters.factory import AdapterFactory
        
        factory = AdapterFactory()
        assert "bigquery" in factory.dataframe_funcs


@pytest.mark.skipif(not BIGQUERY_AVAILABLE, reason="BigQuery dependencies not installed")
class TestBigQuerySpecificBehavior:
    """Test BigQuery-specific functionality."""

    def test_database_and_schema_properties(self, mock_settings, mock_bigquery_client):
        """Test that database and schema properties work correctly."""
        BigQueryAdapter._instance = None
        BigQueryAdapter._initialized = False
        
        adapter = BigQueryAdapter()
        assert adapter.database == "test-project"
        assert adapter.schema == "test_dataset"
        
        adapter.database = "new-project"
        adapter.schema = "new_dataset"
        assert adapter.database == "new-project"
        assert adapter.schema == "new_dataset"

    def test_check_data_validates_bigquery_config(self, mock_settings, mock_bigquery_client, bigquery_config):
        """Test that check_data validates BigQuery config correctly."""
        BigQueryAdapter._instance = None
        BigQueryAdapter._initialized = False
        
        adapter = BigQueryAdapter()
        validated = adapter.check_data(bigquery_config)
        assert isinstance(validated, BigQueryConfig)
        assert validated.identifier == "test_table"
        assert validated.type == "bigquery"

    def test_check_data_rejects_invalid_config(self, mock_settings, mock_bigquery_client):
        """Test that check_data rejects invalid configs."""
        BigQueryAdapter._instance = None
        BigQueryAdapter._initialized = False
        
        adapter = BigQueryAdapter()
        with pytest.raises(TypeError, match="Input must be a BigQuery config"):
            adapter.check_data({"invalid": "config"})

    def test_create_new_config_from_etl(self, mock_settings, mock_bigquery_client):
        """Test creating a new config from ETL name."""
        BigQueryAdapter._instance = None
        BigQueryAdapter._initialized = False
        
        adapter = BigQueryAdapter()
        config = adapter.create_new_config_from_etl("etl_table")
        assert isinstance(config, BigQueryConfig)
        assert config.identifier == "etl_table"
        assert config.type == "bigquery"

    def test_get_details_returns_config_dict(self, mock_settings, mock_bigquery_client, bigquery_config):
        """Test that get_details returns config as dictionary."""
        BigQueryAdapter._instance = None
        BigQueryAdapter._initialized = False
        
        adapter = BigQueryAdapter()
        details = adapter.get_details(bigquery_config)
        assert isinstance(details, dict)
        assert details["identifier"] == "test_table"
        assert details["type"] == "bigquery"

    def test_get_fqn_creates_fully_qualified_name(self, mock_settings, mock_bigquery_client):
        """Test that _get_fqn creates proper fully qualified names."""
        BigQueryAdapter._instance = None
        BigQueryAdapter._initialized = False
        
        adapter = BigQueryAdapter()
        
        # Simple table name
        fqn = adapter._get_fqn("test_table")
        assert fqn == "`test-project.test_dataset.test_table`"
        
        # Dataset.table format
        fqn = adapter._get_fqn("other_dataset.test_table")
        assert fqn == "`test-project.other_dataset.test_table`"
        
        # Full project.dataset.table format
        fqn = adapter._get_fqn("other-project.other_dataset.test_table")
        assert fqn == "`other-project.other_dataset.test_table`"

    def test_client_property_exists(self, mock_settings, mock_bigquery_client):
        """Test that the BigQuery client is initialized."""
        BigQueryAdapter._instance = None
        BigQueryAdapter._initialized = False
        
        adapter = BigQueryAdapter()
        assert adapter.client is not None


@pytest.mark.skipif(not BIGQUERY_AVAILABLE, reason="BigQuery dependencies not installed")
class TestCanHandleBigQuery:
    """Test the can_handle_bigquery function."""

    def test_handles_bigquery_config_object(self, bigquery_config):
        """Test that it accepts valid BigQuery config objects."""
        assert can_handle_bigquery(bigquery_config) is True

    def test_handles_valid_bigquery_dict(self):
        """Test that it accepts valid BigQuery config dictionaries."""
        config_dict = {"identifier": "test_table", "type": "bigquery"}
        assert can_handle_bigquery(config_dict) is True

    def test_rejects_non_bigquery_configs(self):
        """Test that it rejects non-BigQuery configs."""
        assert can_handle_bigquery({"type": "postgres"}) is False
        assert can_handle_bigquery({"invalid": "config"}) is False
        assert can_handle_bigquery("not a config") is False
        assert can_handle_bigquery(None) is False


@pytest.mark.skipif(not BIGQUERY_AVAILABLE, reason="BigQuery dependencies not installed")
class TestBigQueryErrorHandling:
    """Test error handling in BigQueryAdapter."""

    def test_import_error_when_bigquery_not_installed(self):
        """Test that ImportError is raised when BigQuery is not installed."""
        with patch("intugle.adapters.types.bigquery.bigquery.BIGQUERY_AVAILABLE", False):
            BigQueryAdapter._instance = None
            BigQueryAdapter._initialized = False
            
            with pytest.raises(ImportError, match="BigQuery dependencies are not installed"):
                BigQueryAdapter()

    def test_check_data_type_error_message(self, mock_settings, mock_bigquery_client):
        """Test that check_data provides clear error message."""
        BigQueryAdapter._instance = None
        BigQueryAdapter._initialized = False
        
        adapter = BigQueryAdapter()
        with pytest.raises(TypeError) as exc_info:
            adapter.check_data({"not": "valid"})
        assert "Input must be a BigQuery config" in str(exc_info.value)

    def test_connection_error_provides_context(self, mock_bigquery_client):
        """Test that connection errors provide helpful context."""
        with patch("intugle.adapters.types.bigquery.bigquery.settings") as mock_settings:
            mock_settings.PROFILES = {}
            BigQueryAdapter._instance = None
            BigQueryAdapter._initialized = False
            
            with pytest.raises(ValueError, match="No 'bigquery' section found in profiles.yml"):
                BigQueryAdapter()


@pytest.mark.skipif(not BIGQUERY_AVAILABLE, reason="BigQuery dependencies not installed")
class TestBigQueryConnectionConfig:
    """Test BigQueryConnectionConfig model."""

    def test_valid_config(self):
        """Test that valid config can be created."""
        config = BigQueryConnectionConfig(
            project_id="test-project",
            dataset="test_dataset",
            location="US",
        )
        assert config.project_id == "test-project"
        assert config.dataset_id == "test_dataset"
        assert config.location == "US"

    def test_optional_credentials_path(self):
        """Test that credentials_path is optional."""
        config = BigQueryConnectionConfig(
            project_id="test-project",
            dataset="test_dataset",
        )
        assert config.credentials_path is None

    def test_with_credentials_path(self):
        """Test config with credentials path."""
        config = BigQueryConnectionConfig(
            project_id="test-project",
            dataset="test_dataset",
            credentials_path="/path/to/credentials.json",
        )
        assert config.credentials_path == "/path/to/credentials.json"
