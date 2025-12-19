from unittest.mock import MagicMock
from intugle.nosql.api import NoSQLToRelationalParser


def test_api_initialization():
    """Test NoSQLToRelationalParser initializes correctly."""
    mock_source = MagicMock()
    orchestrator = NoSQLToRelationalParser(mock_source)

    assert orchestrator.source == mock_source
    assert orchestrator.config == {}
    assert orchestrator._parsed_tables is None


def test_api_initialization_with_config():
    """Test NoSQLToRelationalParser accepts config."""
    mock_source = MagicMock()
    config = {"rename_tables": {"root": "orders"}}
    orchestrator = NoSQLToRelationalParser(mock_source, config=config)

    assert orchestrator.config == config


def test_api_infer_model():
    """Test infer_model calls source and returns schema."""
    mock_source = MagicMock()
    mock_source.get_data.return_value = iter([{"id": 1, "name": "test"}])

    orchestrator = NoSQLToRelationalParser(mock_source)
    model = orchestrator.infer_model()

    assert "id" in model
    assert "name" in model
    mock_source.get_data.assert_called_once()


def test_api_run_flow():
    """Test run() executes parsing pipeline."""
    mock_source = MagicMock()
    mock_source.get_data.return_value = iter([{"id": 1, "val": "a"}])

    orchestrator = NoSQLToRelationalParser(mock_source)
    orchestrator.run()

    assert orchestrator._parsed_tables is not None
    assert "root" in orchestrator._parsed_tables


def test_api_run_with_nested_data():
    """Test run() handles nested arrays correctly."""
    mock_source = MagicMock()
    mock_source.get_data.return_value = iter(
        [{"id": 1, "items": [{"name": "a"}, {"name": "b"}]}]
    )

    orchestrator = NoSQLToRelationalParser(mock_source)
    orchestrator.run()

    assert "root" in orchestrator._parsed_tables
    assert "root_items" in orchestrator._parsed_tables


def test_api_write_delegation():
    """Test write() delegates to target."""
    mock_source = MagicMock()
    mock_source.get_data.return_value = iter([])
    mock_target = MagicMock()

    orchestrator = NoSQLToRelationalParser(mock_source)
    orchestrator.write(mock_target)

    mock_target.write.assert_called_once()


def test_api_write_auto_runs_if_not_run():
    """Test write() auto-runs if run() wasn't called."""
    mock_source = MagicMock()
    mock_source.get_data.return_value = iter([{"id": 1}])
    mock_target = MagicMock()

    orchestrator = NoSQLToRelationalParser(mock_source)
    assert orchestrator._parsed_tables is None

    orchestrator.write(mock_target)

    assert orchestrator._parsed_tables is not None
    mock_target.write.assert_called_once()
