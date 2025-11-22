"""
SQLite Adapter Tests

Tests for the SQLite adapter following the BaseAdapterTests pattern.
"""

import os
import sqlite3
import tempfile

import pytest

from intugle.adapters.types.sqlite.models import SqliteConfig
from intugle.adapters.types.sqlite.sqlite import SqliteAdapter, can_handle_sqlite
from intugle.analysis.models import DataSet
from tests.adapters.base_adapter_tests import BaseAdapterTests


def create_test_database(table_name: str, csv_path: str) -> str:
    """
    Create a temporary SQLite database and load data from a CSV file.
    
    Args:
        table_name: Name of the table to create
        csv_path: Path to the CSV file to load
        
    Returns:
        Path to the created SQLite database file
    """
    import pandas as pd
    
    # Create temporary database file
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Load CSV and create table
    df = pd.read_csv(csv_path)
    conn = sqlite3.connect(db_path)
    df.to_sql(table_name, conn, if_exists='replace', index=False)
    conn.close()
    
    return db_path


def get_healthcare_config(table_name: str) -> SqliteConfig:
    """Helper function to create a SqliteConfig for a healthcare table."""
    csv_path = f"sample_data/healthcare/{table_name}.csv"
    db_path = create_test_database(table_name, csv_path)
    return SqliteConfig(path=db_path, type="sqlite")


class TestSqliteAdapter(BaseAdapterTests):
    """Runs the shared adapter tests for the SqliteAdapter."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test to ensure clean state."""
        SqliteAdapter._instance = None
        SqliteAdapter._initialized = False
        yield
        # Cleanup: close connections and reset
        if SqliteAdapter._instance:
            for conn in SqliteAdapter._instance._connections.values():
                try:
                    conn.close()
                except Exception:
                    pass
            SqliteAdapter._instance._connections.clear()
        SqliteAdapter._instance = None
        SqliteAdapter._initialized = False

    @pytest.fixture
    def adapter_instance(self):
        """Create a fresh SqliteAdapter instance for each test."""
        return SqliteAdapter()

    @pytest.fixture
    def test_data(self):
        """Provides a SqliteConfig pointing to the allergies test table."""
        return get_healthcare_config("allergies")

    @pytest.fixture
    def table1_dataset(self) -> DataSet:
        """Provides the 'patients' dataset for intersection tests."""
        config = get_healthcare_config("patients")
        return DataSet(config, name="patients")

    @pytest.fixture
    def table2_dataset(self) -> DataSet:
        """Provides the 'allergies' dataset for intersection tests."""
        config = get_healthcare_config("allergies")
        return DataSet(config, name="allergies")


# ============================================================================
# SQLite-Specific Behavior Tests
# ============================================================================


class TestSqliteSpecificBehavior:
    """Test SQLite platform-specific behavior and quirks."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        SqliteAdapter._instance = None
        SqliteAdapter._initialized = False
        yield
        if SqliteAdapter._instance:
            for conn in SqliteAdapter._instance._connections.values():
                try:
                    conn.close()
                except Exception:
                    pass
            SqliteAdapter._instance._connections.clear()
        SqliteAdapter._instance = None
        SqliteAdapter._initialized = False

    def test_connection_caching(self):
        """Test that connections are cached and reused."""
        adapter = SqliteAdapter()
        
        # Create a temporary database
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        config = SqliteConfig(path=db_path, type="sqlite")
        
        # First load
        adapter.load(config, "test_table")
        conn1 = adapter.connection
        
        # Second load with same path
        adapter.load(config, "test_table")
        conn2 = adapter.connection
        
        # Should be the same connection object
        assert conn1 is conn2
        
        # Cleanup
        os.unlink(db_path)

    def test_multiple_databases(self):
        """Test that adapter can handle multiple database paths."""
        adapter = SqliteAdapter()
        
        # Create two temporary databases
        fd1, db_path1 = tempfile.mkstemp(suffix='.db')
        fd2, db_path2 = tempfile.mkstemp(suffix='.db')
        os.close(fd1)
        os.close(fd2)
        
        config1 = SqliteConfig(path=db_path1, type="sqlite")
        config2 = SqliteConfig(path=db_path2, type="sqlite")
        
        adapter.load(config1, "table1")
        assert adapter._current_path == db_path1
        
        adapter.load(config2, "table2")
        assert adapter._current_path == db_path2
        assert len(adapter._connections) == 2
        
        # Cleanup
        os.unlink(db_path1)
        os.unlink(db_path2)

    def test_create_view(self):
        """Test that CREATE VIEW works correctly."""
        adapter = SqliteAdapter()
        
        # Create a temporary database with a table
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test_table (id INTEGER, name TEXT)")
        conn.execute("INSERT INTO test_table VALUES (1, 'Alice'), (2, 'Bob')")
        conn.commit()
        conn.close()
        
        config = SqliteConfig(path=db_path, type="sqlite")
        adapter.load(config, "test_table")
        
        # Create a view
        query = "SELECT * FROM test_table WHERE id > 1"
        adapter.create_table_from_query("test_view", query, materialize="view")
        
        # Verify view exists and works
        result = adapter.to_df_from_query("SELECT * FROM test_view")
        assert len(result) == 1
        assert result.iloc[0]['name'] == 'Bob'
        
        # Cleanup
        os.unlink(db_path)

    def test_parameterized_queries(self):
        """Test that parameterized queries work correctly."""
        adapter = SqliteAdapter()
        
        # Create a temporary database
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test_table (id INTEGER, name TEXT)")
        conn.execute("INSERT INTO test_table VALUES (1, 'Alice'), (2, 'Bob')")
        conn.commit()
        conn.close()
        
        config = SqliteConfig(path=db_path, type="sqlite")
        adapter.load(config, "test_table")
        
        # Use parameterized query
        result = adapter._execute_sql("SELECT * FROM test_table WHERE id = ?", 1)
        assert len(result) == 1
        assert result[0][1] == 'Alice'
        
        # Cleanup
        os.unlink(db_path)

    def test_safe_identifier(self):
        """Test that safe_identifier prevents SQL injection."""
        from intugle.adapters.types.sqlite.sqlite import safe_identifier
        
        # Valid identifier
        assert safe_identifier("test_table") == '"test_table"'
        
        # Invalid identifiers should raise ValueError
        with pytest.raises(ValueError):
            safe_identifier('test"; DROP TABLE users; --')
        
        with pytest.raises(ValueError):
            safe_identifier('test; DELETE FROM users')

    def test_can_handle_sqlite(self):
        """Test that can_handle_sqlite correctly identifies SqliteConfig."""
        valid_config = SqliteConfig(path="/tmp/test.db", type="sqlite")
        assert can_handle_sqlite(valid_config) is True
        
        invalid_config = {"path": "/tmp/test.db", "type": "postgres"}
        assert can_handle_sqlite(invalid_config) is False

