import pytest
from unittest.mock import MagicMock, Mock, patch

from intugle.adapters.types.redshift.redshift import RedshiftAdapter, REDSHIFT_AVAILABLE
from intugle.adapters.types.redshift.models import RedshiftConfig
from intugle.analysis.models import DataSet


@pytest.fixture
def mock_redshift_connection():
    """Mock a Redshift connection."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    return mock_conn, mock_cursor


@pytest.fixture
def mock_settings():
    """Mock settings with Redshift configuration."""
    with patch("intugle.adapters.types.redshift.redshift.settings") as mock_settings:
        mock_settings.PROFILES.get.return_value = {
            "user": "test_user",
            "password": "test_password",
            "host": "test-cluster.redshift.amazonaws.com",
            "port": 5439,
            "database": "test_db",
            "schema": "public",
            "name": "test_redshift_source"
        }
        yield mock_settings


@pytest.mark.skipif(not REDSHIFT_AVAILABLE, reason="Redshift dependencies not installed")
class TestRedshiftAdapter:
    """Unit tests for RedshiftAdapter."""

    def test_redshift_config_validation(self):
        """Test that RedshiftConfig validates correctly."""
        config = RedshiftConfig(identifier="test_table", type="redshift")
        assert config.identifier == "test_table"
        assert config.type == "redshift"

    def test_check_data(self):
        """Test the check_data static method."""
        valid_config = {"identifier": "test_table", "type": "redshift"}
        result = RedshiftAdapter.check_data(valid_config)
        assert isinstance(result, RedshiftConfig)
        assert result.identifier == "test_table"

        with pytest.raises(TypeError):
            RedshiftAdapter.check_data({"invalid": "config"})

    @patch("intugle.adapters.types.redshift.redshift.redshift_connector")
    def test_connect(self, mock_connector, mock_settings):
        """Test the connection initialization."""
        mock_conn = MagicMock()
        mock_connector.connect.return_value = mock_conn
        
        # Reset the singleton
        RedshiftAdapter._instance = None
        RedshiftAdapter._initialized = False
        
        adapter = RedshiftAdapter()
        
        mock_connector.connect.assert_called_once_with(
            user="test_user",
            password="test_password",
            host="test-cluster.redshift.amazonaws.com",
            port=5439,
            database="test_db"
        )
        assert adapter.database == "test_db"
        assert adapter.schema == "public"
        assert adapter.source_name == "test_redshift_source"

    @patch("intugle.adapters.types.redshift.redshift.redshift_connector")
    def test_get_fqn(self, mock_connector, mock_settings):
        """Test fully qualified name generation."""
        # Reset singleton
        RedshiftAdapter._instance = None
        RedshiftAdapter._initialized = False
        
        adapter = RedshiftAdapter()
        
        # Test with simple identifier
        assert adapter._get_fqn("test_table") == '"public"."test_table"'
        
        # Test with already qualified identifier
        assert adapter._get_fqn("schema.test_table") == "schema.test_table"

    @patch("intugle.adapters.types.redshift.redshift.redshift_connector")
    def test_profile(self, mock_connector, mock_settings, mock_redshift_connection):
        """Test the profile method."""
        mock_conn, mock_cursor = mock_redshift_connection
        mock_connector.connect.return_value = mock_conn
        
        # Reset singleton
        RedshiftAdapter._instance = None
        RedshiftAdapter._initialized = False
        
        adapter = RedshiftAdapter()
        adapter.connection = mock_conn
        
        # Mock the count query
        mock_cursor.fetchall.side_effect = [
            [(100,)],  # Total count
            [("col1", "varchar"), ("col2", "integer")]  # Column metadata
        ]
        
        config = RedshiftConfig(identifier="test_table")
        result = adapter.profile(config, "test_table")
        
        assert result.count == 100
        assert "col1" in result.columns
        assert "col2" in result.columns
        assert result.dtypes["col1"] == "varchar"
        assert result.dtypes["col2"] == "integer"

    @patch("intugle.adapters.types.redshift.redshift.redshift_connector")
    def test_create_table_from_query(self, mock_connector, mock_settings, mock_redshift_connection):
        """Test creating a table from a query."""
        mock_conn, mock_cursor = mock_redshift_connection
        mock_connector.connect.return_value = mock_conn
        
        # Reset singleton
        RedshiftAdapter._instance = None
        RedshiftAdapter._initialized = False
        
        adapter = RedshiftAdapter()
        adapter.connection = mock_conn
        
        mock_cursor.fetchall.return_value = []
        
        query = "SELECT * FROM source_table WHERE id > 10"
        adapter.create_table_from_query("new_table", query, materialize="table")
        
        # Verify that DROP and CREATE were called
        assert mock_cursor.execute.call_count >= 2

    @patch("intugle.adapters.types.redshift.redshift.redshift_connector")
    def test_to_df_from_query(self, mock_connector, mock_settings, mock_redshift_connection):
        """Test converting query results to DataFrame."""
        mock_conn, mock_cursor = mock_redshift_connection
        mock_connector.connect.return_value = mock_conn
        
        # Reset singleton
        RedshiftAdapter._instance = None
        RedshiftAdapter._initialized = False
        
        adapter = RedshiftAdapter()
        adapter.connection = mock_conn
        
        # Mock query result
        mock_cursor.description = [("id",), ("name",)]
        mock_cursor.fetchall.return_value = [(1, "Alice"), (2, "Bob")]
        
        df = adapter.to_df_from_query("SELECT * FROM test_table")
        
        assert len(df) == 2
        assert list(df.columns) == ["id", "name"]
        assert df.iloc[0]["name"] == "Alice"

    @patch("intugle.adapters.types.redshift.redshift.redshift_connector")
    def test_create_new_config_from_etl(self, mock_connector, mock_settings):
        """Test creating a new config from ETL name."""
        # Reset singleton
        RedshiftAdapter._instance = None
        RedshiftAdapter._initialized = False
        
        adapter = RedshiftAdapter()
        
        new_config = adapter.create_new_config_from_etl("my_etl_table")
        
        assert isinstance(new_config, RedshiftConfig)
        assert new_config.identifier == "my_etl_table"
        assert new_config.type == "redshift"


def test_can_handle_redshift():
    """Test the can_handle_redshift function."""
    from intugle.adapters.types.redshift.redshift import can_handle_redshift
    
    valid_config = {"identifier": "test_table", "type": "redshift"}
    assert can_handle_redshift(valid_config) is True
    
    invalid_config = {"identifier": "test_table", "type": "postgres"}
    assert can_handle_redshift(invalid_config) is False


@pytest.mark.skipif(not REDSHIFT_AVAILABLE, reason="Redshift dependencies not installed")
def test_adapter_registration():
    """Test that the Redshift adapter can be registered with the factory."""
    from intugle.adapters.factory import AdapterFactory
    from intugle.adapters.types.redshift.redshift import register
    
    factory = AdapterFactory.__new__(AdapterFactory)
    factory.dataframe_funcs = {}
    factory.config_types = []
    
    register(factory)
    
    assert "redshift" in factory.dataframe_funcs
    assert RedshiftConfig in factory.config_types
