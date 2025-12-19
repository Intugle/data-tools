from unittest.mock import MagicMock, patch
from intugle.nosql.source import MongoSource, NoSQLSource


def test_nosql_source_interface():
    """Test that NoSQLSource raises NotImplementedError."""
    source = NoSQLSource()
    try:
        source.get_data()
        assert False, "Should have raised NotImplementedError"
    except NotImplementedError:
        pass


def test_mongo_source_initialization():
    """Test MongoSource stores initialization parameters correctly."""
    source = MongoSource("mongodb://test", "db", "coll")
    assert source.uri == "mongodb://test"
    assert source.database == "db"
    assert source.collection == "coll"
    assert source.sample_size == 0
    assert source._client is None


def test_mongo_source_initialization_with_sample():
    """Test MongoSource with sample_size parameter."""
    source = MongoSource("mongodb://test", "db", "coll", sample_size=100)
    assert source.sample_size == 100


@patch("intugle.nosql.source.pymongo.MongoClient")
def test_mongo_source_get_data(mock_client):
    """Test MongoSource fetches and yields documents correctly."""
    # Setup mock
    mock_db = MagicMock()
    mock_coll = MagicMock()
    mock_cursor = [{"_id": "1", "data": "test"}]

    mock_client.return_value.__getitem__.return_value = mock_db
    mock_db.__getitem__.return_value = mock_coll
    mock_coll.find.return_value = mock_cursor

    # Run
    source = MongoSource("mongodb://test", "db", "coll")
    data = list(source.get_data())

    # Verify
    assert len(data) == 1
    assert data[0]["data"] == "test"
    mock_coll.find.assert_called_once()


@patch("intugle.nosql.source.pymongo.MongoClient")
def test_mongo_source_converts_objectid_to_string(mock_client):
    """Test that ObjectId is converted to string."""
    from bson import ObjectId

    mock_db = MagicMock()
    mock_coll = MagicMock()
    oid = ObjectId()
    mock_cursor = [{"_id": oid, "name": "test"}]

    mock_client.return_value.__getitem__.return_value = mock_db
    mock_db.__getitem__.return_value = mock_coll
    mock_coll.find.return_value = mock_cursor

    source = MongoSource("mongodb://test", "db", "coll")
    data = list(source.get_data())

    assert isinstance(data[0]["_id"], str)
    assert data[0]["_id"] == str(oid)


@patch("intugle.nosql.source.pymongo.MongoClient")
def test_mongo_source_sample_limit(mock_client):
    """Test that sample_size limits the cursor."""
    mock_db = MagicMock()
    mock_coll = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.__iter__ = MagicMock(return_value=iter([]))

    mock_client.return_value.__getitem__.return_value = mock_db
    mock_db.__getitem__.return_value = mock_coll
    mock_coll.find.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor

    source = MongoSource("mongodb://test", "db", "coll", sample_size=50)
    list(source.get_data())

    mock_cursor.limit.assert_called_once_with(50)
