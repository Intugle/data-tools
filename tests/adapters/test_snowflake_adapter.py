"""
Snowflake Adapter Tests

Focus on:
1. Contract compliance - Adapter implements required interface
2. Snowflake-specific behavior - Platform quirks and differences
3. Error handling - Proper error messages and handling
"""

from unittest.mock import MagicMock

import pytest

from intugle.adapters.adapter import Adapter
from intugle.adapters.factory import AdapterFactory
from intugle.adapters.types.snowflake.models import SnowflakeConfig
from intugle.adapters.types.snowflake.snowflake import (
    SnowflakeAdapter,
    can_handle_snowflake,
)

# ============================================================================
# Contract Compliance Tests
# ============================================================================


class TestSnowflakeAdapterContract:
    """Verify SnowflakeAdapter implements the Adapter interface correctly."""

    @pytest.fixture
    def mock_adapter(self, mocker):
        """Create a minimally mocked adapter for contract testing."""
        mocker.patch(
            "intugle.adapters.types.snowflake.snowflake.SnowflakeAdapter.connect"
        )
        SnowflakeAdapter._instance = None
        SnowflakeAdapter._initialized = False
        return SnowflakeAdapter()

    def test_implements_required_methods(self, mock_adapter):
        """Verify adapter has all required methods from Adapter interface."""
        required_methods = [
            'profile',
            'column_profile',
            'to_df',
            'to_df_from_query',
            'load',
            'execute',
            'intersect_count',
            'create_table_from_query',
            'create_new_config_from_etl',
            'check_data',
            'get_details',
        ]
        required_properties = [
            'source_name',
            'database',
            'schema'
        ]

        for method in required_methods:
            assert hasattr(mock_adapter, method), f"Missing method: {method}"
            assert callable(getattr(mock_adapter, method)), f"{method} is not callable"

        for propery in required_properties:
            assert hasattr(mock_adapter, propery), f"Missing property: {propery}"

    def test_inherits_from_adapter(self, mock_adapter):
        """Verify SnowflakeAdapter inherits from Adapter base class."""
        assert isinstance(mock_adapter, Adapter)

    def test_singleton_pattern(self, mocker):
        """Verify adapter follows singleton pattern."""
        mocker.patch(
            "intugle.adapters.types.snowflake.snowflake.SnowflakeAdapter.connect"
        )

        SnowflakeAdapter._instance = None
        SnowflakeAdapter._initialized = False

        adapter1 = SnowflakeAdapter()
        adapter2 = SnowflakeAdapter()

        assert adapter1 is adapter2, "SnowflakeAdapter should be a singleton"

    def test_registered_in_factory(self):
        """Verify adapter can be registered and detected by factory."""
        AdapterFactory.register("snowflake", can_handle_snowflake, SnowflakeAdapter, SnowflakeConfig)

        config = SnowflakeConfig(identifier="test_table")

        # Verify the config is recognized as Snowflake
        assert can_handle_snowflake(config)


# ============================================================================
# Snowflake-Specific Behavior Tests
# ============================================================================

class TestSnowflakeSpecificBehavior:
    """Test Snowflake platform-specific behavior and quirks."""

    @pytest.fixture
    def mock_adapter(self, mocker):
        """Create adapter with mocked session."""
        def mock_init(self):
            self.session = MagicMock()
            self.database = "TEST_DATABASE"
            self.schema = "PUBLIC"
            self._initialized = True

        mocker.patch(
            "intugle.adapters.types.snowflake.snowflake.SnowflakeAdapter.__init__",
            mock_init,
        )

        SnowflakeAdapter._instance = None
        SnowflakeAdapter._initialized = False
        return SnowflakeAdapter()

    def test_database_and_schema_properties(self, mock_adapter):
        """Verify adapter stores database and schema from connection."""
        assert hasattr(mock_adapter, 'database')
        assert hasattr(mock_adapter, 'schema')
        assert mock_adapter.database == "TEST_DATABASE"
        assert mock_adapter.schema == "PUBLIC"

    def test_check_data_validates_snowflake_config(self):
        """Test that check_data properly validates SnowflakeConfig."""
        # Valid config
        valid_config = {"identifier": "MY_TABLE", "type": "snowflake"}
        result = SnowflakeAdapter.check_data(valid_config)

        assert isinstance(result, SnowflakeConfig)
        assert result.identifier == "MY_TABLE"
        assert result.type == "snowflake"

    def test_check_data_rejects_invalid_config(self):
        """Test that check_data rejects non-Snowflake configs."""
        invalid_configs = [
            {"path": "file.csv", "type": "csv"},  # Missing 'identifier'
            "not a dict",
            123,
            None,
        ]

        for invalid in invalid_configs:
            with pytest.raises(TypeError, match="Input must be a snowflake config"):
                SnowflakeAdapter.check_data(invalid)

    def test_create_new_config_from_etl(self, mock_adapter):
        """Test creating config for materialized ETL results."""
        new_config = mock_adapter.create_new_config_from_etl("my_data_product")

        assert isinstance(new_config, SnowflakeConfig)
        assert new_config.identifier == "my_data_product"
        assert new_config.type == "snowflake"

    def test_get_details_returns_config_dict(self, mock_adapter):
        """Test get_details returns config as dictionary."""
        config = SnowflakeConfig(identifier="TEST_TABLE")
        details = mock_adapter.get_details(config)

        assert isinstance(details, dict)
        assert details["identifier"] == "TEST_TABLE"
        assert details["type"] == "snowflake"

    def test_session_sql_method_exists(self, mock_adapter):
        """Verify adapter has session.sql for query execution."""
        assert hasattr(mock_adapter, 'session')
        assert hasattr(mock_adapter.session, 'sql')

    def test_session_table_method_exists(self, mock_adapter):
        """Verify adapter has session.table for table access."""
        assert hasattr(mock_adapter, 'session')
        assert hasattr(mock_adapter.session, 'table')


# ============================================================================
# Type Detection Tests
# ============================================================================

class TestCanHandleSnowflake:
    """Test the can_handle_snowflake function for config detection."""

    def test_handles_snowflake_config_object(self):
        """Test detection of SnowflakeConfig objects."""
        config = SnowflakeConfig(identifier="test_table")
        assert can_handle_snowflake(config) is True

    def test_handles_valid_snowflake_dict(self):
        """Test detection of valid Snowflake config dictionaries."""
        valid_dicts = [
            {"identifier": "table1", "type": "snowflake"},
            {"identifier": "DB.SCHEMA.TABLE", "type": "snowflake"},
        ]

        for config_dict in valid_dicts:
            assert can_handle_snowflake(config_dict) is True

    def test_rejects_non_snowflake_configs(self):
        """Test rejection of non-Snowflake configs."""
        invalid_configs = [
            {"path": "file.csv", "type": "csv"},  # Missing 'identifier' field
            "not a config",
            123,
            None,
            [],
        ]

        for invalid in invalid_configs:
            assert can_handle_snowflake(invalid) is False



# ============================================================================
# Error Handling Tests
# ============================================================================

class TestSnowflakeErrorHandling:
    """Test error handling and informative error messages."""

    def test_import_error_when_snowflake_not_installed(self, mocker):
        """Test that helpful error is raised when Snowflake package missing."""
        # Mock SNOWFLAKE_AVAILABLE as False
        mocker.patch(
            "intugle.adapters.types.snowflake.snowflake.SNOWFLAKE_AVAILABLE",
            False
        )

        SnowflakeAdapter._instance = None
        SnowflakeAdapter._initialized = False

        with pytest.raises(ImportError, match="Snowflake dependencies are not installed"):
            SnowflakeAdapter()

    def test_check_data_type_error_message(self):
        """Test that check_data provides clear error message."""
        with pytest.raises(TypeError) as exc_info:
            SnowflakeAdapter.check_data({"path": "file.csv", "type": "csv"})

        assert "Input must be a snowflake config" in str(exc_info.value)

    def test_connection_error_provides_context(self, mocker):
        """Test that connection errors provide helpful context."""
        # Mock get_active_session to raise exception
        mocker.patch(
            "intugle.adapters.types.snowflake.snowflake.get_active_session",
            side_effect=Exception("No session")
        )

        # Mock settings to have no profiles
        mocker.patch(
            "intugle.adapters.types.snowflake.snowflake.settings.PROFILES",
            {}
        )

        SnowflakeAdapter._instance = None
        SnowflakeAdapter._initialized = False

        with pytest.raises(ValueError, match="Could not create Snowflake session"):
            SnowflakeAdapter()
