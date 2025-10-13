"""
Databricks Adapter Tests

Focus on:
1. Contract compliance - Adapter implements required interface
2. Databricks-specific behavior - Platform quirks and differences
3. Error handling - Proper error messages and handling
"""

from unittest.mock import MagicMock

import pytest

from intugle.adapters.adapter import Adapter
from intugle.adapters.factory import AdapterFactory
from intugle.adapters.types.databricks.databricks import (
    DatabricksAdapter,
    can_handle_databricks,
)
from intugle.adapters.types.databricks.models import DatabricksConfig

# ============================================================================
# Contract Compliance Tests
# ============================================================================


class TestDatabricksAdapterContract:
    """Verify DatabricksAdapter implements the Adapter interface correctly."""

    @pytest.fixture
    def mock_adapter(self, mocker):
        """Create a minimally mocked adapter for contract testing."""
        mocker.patch(
            "intugle.adapters.types.databricks.databricks.DatabricksAdapter.connect"
        )
        DatabricksAdapter._instance = None
        DatabricksAdapter._initialized = False
        return DatabricksAdapter()

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

        for method in required_methods:
            assert hasattr(mock_adapter, method), f"Missing method: {method}"
            assert callable(getattr(mock_adapter, method)), f"{method} is not callable"

    def test_inherits_from_adapter(self, mock_adapter):
        """Verify DatabricksAdapter inherits from Adapter base class."""
        assert isinstance(mock_adapter, Adapter)

    def test_singleton_pattern(self, mocker):
        """Verify adapter follows singleton pattern."""
        mocker.patch(
            "intugle.adapters.types.databricks.databricks.DatabricksAdapter.connect"
        )

        DatabricksAdapter._instance = None
        DatabricksAdapter._initialized = False

        adapter1 = DatabricksAdapter()
        adapter2 = DatabricksAdapter()

        assert adapter1 is adapter2, "DatabricksAdapter should be a singleton"

    def test_registered_in_factory(self):
        """Verify adapter can be registered and detected by factory."""
        AdapterFactory.register("databricks", can_handle_databricks, DatabricksAdapter)

        config = DatabricksConfig(identifier="test_table")

        # Verify the config is recognized as Databricks
        assert can_handle_databricks(config)


# ============================================================================
# Databricks-Specific Behavior Tests
# ============================================================================

class TestDatabricksSpecificBehavior:
    """Test Databricks platform-specific behavior and quirks."""

    @pytest.fixture
    def mock_adapter(self, mocker):
        """Create adapter with mocked connection."""
        def mock_init(self):
            self.spark = None
            self.connection = MagicMock()
            self.catalog = "test_catalog"
            self.schema = "test_schema"
            self._initialized = True

        mocker.patch(
            "intugle.adapters.types.databricks.databricks.DatabricksAdapter.__init__",
            mock_init,
        )

        DatabricksAdapter._instance = None
        DatabricksAdapter._initialized = False
        return DatabricksAdapter()

    def test_catalog_and_schema_properties(self, mock_adapter):
        """Verify adapter stores catalog and schema from connection."""
        assert hasattr(mock_adapter, 'catalog')
        assert hasattr(mock_adapter, 'schema')
        assert mock_adapter.catalog == "test_catalog"
        assert mock_adapter.schema == "test_schema"

    def test_check_data_validates_databricks_config(self):
        """Test that check_data properly validates DatabricksConfig."""
        # Valid config
        valid_config = {"identifier": "MY_TABLE", "type": "databricks"}
        result = DatabricksAdapter.check_data(valid_config)

        assert isinstance(result, DatabricksConfig)
        assert result.identifier == "MY_TABLE"
        assert result.type == "databricks"

    def test_check_data_rejects_invalid_config(self):
        """Test that check_data rejects non-Databricks configs."""
        invalid_configs = [
            {"path": "file.csv", "type": "csv"},  # Missing 'identifier'
            "not a dict",
            123,
            None,
        ]

        for invalid in invalid_configs:
            with pytest.raises(TypeError, match="Input must be a Databricks config"):
                DatabricksAdapter.check_data(invalid)

    def test_create_new_config_from_etl(self, mock_adapter):
        """Test creating config for materialized ETL results."""
        new_config = mock_adapter.create_new_config_from_etl("my_data_product")

        assert isinstance(new_config, DatabricksConfig)
        assert new_config.identifier == mock_adapter._get_fqn("my_data_product")
        assert new_config.type == "databricks"

    def test_get_details_returns_config_dict(self, mock_adapter):
        """Test get_details returns config as dictionary."""
        config = DatabricksConfig(identifier="TEST_TABLE")
        details = mock_adapter.get_details(config)

        assert isinstance(details, dict)
        assert details["identifier"] == "TEST_TABLE"
        assert details["type"] == "databricks"

    def test_get_fqn_creates_fully_qualified_name(self, mock_adapter):
        """Test _get_fqn creates proper fully qualified table names."""
        # With catalog and schema
        fqn = mock_adapter._get_fqn("my_table")
        assert fqn == "`test_catalog`.`test_schema`.`my_table`"

        # Already qualified (contains dots) - should return as-is
        already_qualified = "custom_cat.custom_schema.my_table"
        fqn_already = mock_adapter._get_fqn(already_qualified)
        assert fqn_already == already_qualified

    def test_connection_property_exists(self, mock_adapter):
        """Verify adapter has connection for SQL execution."""
        assert hasattr(mock_adapter, 'connection')
        assert mock_adapter.connection is not None


# ============================================================================
# Type Detection Tests
# ============================================================================

class TestCanHandleDatabricks:
    """Test the can_handle_databricks function for config detection."""

    def test_handles_databricks_config_object(self):
        """Test detection of DatabricksConfig objects."""
        config = DatabricksConfig(identifier="test_table")
        assert can_handle_databricks(config) is True

    def test_handles_valid_databricks_dict(self):
        """Test detection of valid Databricks config dictionaries."""
        valid_dicts = [
            {"identifier": "table1", "type": "databricks"},
            {"identifier": "CATALOG.SCHEMA.TABLE", "type": "databricks"},
        ]

        for config_dict in valid_dicts:
            assert can_handle_databricks(config_dict) is True

    def test_rejects_non_databricks_configs(self):
        """Test rejection of non-Databricks configs."""
        invalid_configs = [
            {"path": "file.csv", "type": "csv"},  # Missing 'identifier' field
            "not a config",
            123,
            None,
            [],
        ]

        for invalid in invalid_configs:
            assert can_handle_databricks(invalid) is False

    def test_type_field_not_strictly_enforced(self):
        """Test that Pydantic validates structure but doesn't enforce type value.

        Note: DatabricksConfig validates that 'identifier' field exists,
        but doesn't strictly validate the 'type' field value.
        This means a config with wrong type but valid structure passes validation.

        This could be a potential bug - consider adding field validation.
        """
        # This passes validation because it has the required 'identifier' field
        config_with_wrong_type = {"identifier": "table", "type": "snowflake"}

        # Pydantic validates successfully (structure is correct)
        result = DatabricksAdapter.check_data(config_with_wrong_type)

        # But the type field is NOT corrected - it keeps the wrong value!
        # This is a potential bug in the validation logic
        assert result.type == "snowflake"  # Wrong type passes through!
        assert result.identifier == "table"


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestDatabricksErrorHandling:
    """Test error handling and informative error messages."""

    def test_import_error_when_databricks_not_installed(self, mocker):
        """Test that helpful error is raised when Databricks package missing."""
        # Mock DATABRICKS_AVAILABLE as False
        mocker.patch(
            "intugle.adapters.types.databricks.databricks.DATABRICKS_AVAILABLE",
            False
        )

        DatabricksAdapter._instance = None
        DatabricksAdapter._initialized = False

        with pytest.raises(ImportError, match="Databricks dependencies are not installed"):
            DatabricksAdapter()

    def test_check_data_type_error_message(self):
        """Test that check_data provides clear error message."""
        with pytest.raises(TypeError) as exc_info:
            DatabricksAdapter.check_data({"path": "file.csv", "type": "csv"})

        assert "Input must be a Databricks config" in str(exc_info.value)

    def test_connection_error_provides_context(self, mocker):
        """Test that connection errors provide helpful context."""
        # Mock getActiveSession to simulate no active Spark session
        mocker.patch(
            "intugle.adapters.types.databricks.databricks.SparkSession.getActiveSession",
            return_value=None,
        )

        # Mock settings to have no profiles
        mocker.patch(
            "intugle.adapters.types.databricks.databricks.settings.PROFILES",
            {}
        )

        DatabricksAdapter._instance = None
        DatabricksAdapter._initialized = False

        with pytest.raises(ValueError, match="Could not create Databricks connection"):
            DatabricksAdapter()


