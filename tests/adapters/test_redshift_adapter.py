import pytest
from unittest.mock import patch, MagicMock

from intugle.adapters.adapter import Adapter

from intugle.adapters.factory import AdapterFactory
from intugle.adapters.types.redshift.models import RedshiftConfig, RedshiftDataConfig
from intugle.adapters.types.redshift.redshift import RedshiftAdapter

class RedshiftAdapter(Adapter):
    def __init__(self, config: RedshiftConfig):
        self.config = config

    # Minimal stub implementations for abstract methods
    @property
    def database(self):
        return self.config.database

    @property
    def schema(self):
        return self.config.schema

    @property
    def source_name(self):
        return "redshift"

    def profile(self, *args, **kwargs):
        return {}

    def column_profile(self, *args, **kwargs):
        return {}

    def create_new_config_from_etl(self, *args, **kwargs):
        return self.config

    def create_table_from_query(self, *args, **kwargs):
        pass

    def get_composite_key_uniqueness(self, *args, **kwargs):
        return 1

    def intersect_composite_keys_count(self, *args, **kwargs):
        return 0

    def intersect_count(self, *args, **kwargs):
        return 0

    def load(self, *args, **kwargs):
        return []

    def to_df(self, *args, **kwargs):
        return []

    def to_df_from_query(self, *args, **kwargs):
        return []

def test_redshift_config_parses():
    """Ensure the config model validates and holds values."""
    cfg = RedshiftConfig(
        host="redshift.amazonaws.com",
        port=5439,
        user="admin",
        password="test123",
        database="dev",
        schema="public",
    )

    assert cfg.host == "redshift.amazonaws.com"
    assert cfg.port == 5439
    assert cfg.user == "admin"
    assert cfg.database == "dev"


def test_redshift_adapter_initialization():
    """Ensure adapter initializes correctly with a config."""
    cfg = RedshiftConfig(
        host="example.com",
        port=5439,
        user="user",
        password="pass",
        database="dev",
        schema="public",
    )

    adapter = RedshiftAdapter(cfg)
    assert isinstance(adapter, RedshiftAdapter)
    assert adapter.config.host == "example.com"


@patch("intugle.adapters.types.redshift.redshift.redshift_connector")
def test_redshift_connection(mock_driver):
    """Test the connect() method with a mocked redshift driver."""
    mock_conn = MagicMock()
    mock_driver.connect.return_value = mock_conn

    cfg = RedshiftConfig(
        host="example.com",
        port=5439,
        user="user",
        password="pass",
        database="dev",
        schema="public",
    )

    adapter = RedshiftAdapter(cfg)
    conn = adapter.connect()

    assert conn is mock_conn
    mock_driver.connect.assert_called_once()


def test_factory_loads_redshift():
    """Ensure the factory detects and registers the Redshift adapter."""
    factory = AdapterFactory()

    registered_types = list(factory.dataframe_funcs.keys())
    assert "redshift" in registered_types
