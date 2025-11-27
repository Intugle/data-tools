"""
SQLite Adapter Tests

Tests for the SQLite adapter following the BaseAdapterTests pattern.
"""

import os
import sqlite3
import tempfile

from unittest.mock import patch

import pandas as pd
import pytest

from intugle.adapters.types.sqlite.models import SqliteConfig
from intugle.adapters.types.sqlite.sqlite import SqliteAdapter, can_handle_sqlite, safe_identifier
from intugle.analysis.models import DataSet
from intugle.core import settings
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
    # Create temporary database file
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Load CSV and create table
    if not os.path.exists(csv_path):
         # Create dummy data if CSV doesn't exist (portability)
         data = {'id': [1, 2, 3], 'name': ['A', 'B', 'C']}
         if table_name == 'allergies':
             data = {
                 'START': ['2000-01-01', '2000-01-02'], 
                 'STOP': ['2000-01-02', None], 
                 'PATIENT': ['P1', 'P2'], 
                 'ENCOUNTER': ['E1', 'E2'], 
                 'CODE': ['C1', 'C2'], 
                 'DESCRIPTION1': ['Sneezing', 'Coughing'],
                 'REACTION2': ['R1', 'R2'],
                 'DESCRIPTION2': ['D1', 'D2'],
                 'SEVERITY2': ['S1', 'S2']
             }
         elif table_name == 'patients':
             data = {
                 'Id': ['P1', 'P2'], 
                 'BIRTHDATE': ['1980-01-01', '1990-01-01'],
                 'DEATHDATE': [None, None],
                 'SSN': ['123', '456'],
                 'DRIVERS': ['D1', 'D2'],
                 'PASSPORT': ['PP1', 'PP2'],
                 'PREFIX': ['Mr', 'Ms'],
                 'FIRST': ['John', 'Jane'],
                 'LAST': ['Doe', 'Smith'],
                 'SUFFIX': [None, None],
                 'MAIDEN': [None, None],
                 'MARITAL': ['M', 'S'],
                 'RACE': ['White', 'Black'],
                 'ETHNICITY': ['Non-Hispanic', 'Non-Hispanic'],
                 'GENDER': ['M', 'F'],
                 'BIRTHPLACE': ['City', 'Town'],
                 'ADDRESS': ['123 St', '456 Ave'],
                 'CITY': ['City', 'Town'],
                 'STATE': ['CA', 'NY'],
                 'COUNTY': ['C1', 'C2'],
                 'ZIP': ['12345', '67890'],
                 'LAT': [0.0, 1.0],
                 'LON': [0.0, 1.0],
                 'HEALTHCARE_EXPENSES': [100.0, 200.0],
                 'HEALTHCARE_COVERAGE': [50.0, 100.0]
             }
         df = pd.DataFrame(data)
    else:
        df = pd.read_csv(csv_path)
    
    conn = sqlite3.connect(db_path)
    df.to_sql(table_name, conn, if_exists='replace', index=False)
    conn.close()
    
    return db_path


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
            for path, conn in SqliteAdapter._instance._connections.items():
                try:
                    conn.close()
                except Exception:
                    pass
                try:
                     if os.path.exists(path):
                         os.unlink(path)
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
    def db_path(self):
        """Creates a temporary DB and populates it with test data, returning the path."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        # Populate with healthcare data
        # We need ALL tables in one DB now
        conn = sqlite3.connect(path)
        
        # Allergies
        a_csv = "sample_data/healthcare/allergies.csv"
        if os.path.exists(a_csv):
             pd.read_csv(a_csv).to_sql("allergies", conn, index=False)
        else:
             # Dummy allergies
             pd.DataFrame({'PATIENT': ['P1', 'P2'], 'DESCRIPTION1': ['A', 'B']}).to_sql("allergies", conn, index=False)

        # Patients
        p_csv = "sample_data/healthcare/patients.csv"
        if os.path.exists(p_csv):
             pd.read_csv(p_csv).to_sql("patients", conn, index=False)
        else:
             # Dummy patients
             pd.DataFrame({'Id': ['P1', 'P2'], 'FIRST': ['A', 'B']}).to_sql("patients", conn, index=False)

        conn.close()
        yield path
        os.unlink(path)

    @pytest.fixture
    def mock_settings(self, db_path):
        """Mocks settings.PROFILES to point to the temp DB."""
        mock_profiles = {"sqlite": {"path": db_path}}
        with patch.object(settings, 'PROFILES', mock_profiles):
            yield

    @pytest.fixture
    def test_data(self, mock_settings):
        """Provides a SqliteConfig pointing to the allergies test table."""
        # Now we don't pass path in config
        return SqliteConfig(identifier="allergies", type="sqlite")

    @pytest.fixture
    def table1_dataset(self, mock_settings) -> DataSet:
        """Provides the 'patients' dataset."""
        config = SqliteConfig(identifier="patients", type="sqlite")
        return DataSet(config, name="patients")

    @pytest.fixture
    def table2_dataset(self, table1_dataset) -> DataSet:
        """Provides the 'allergies' dataset."""
        config = SqliteConfig(identifier="allergies", type="sqlite")
        return DataSet(config, name="allergies")

    def test_create_new_config_from_etl(self, adapter_instance, mock_settings):
        """
        Tests that the adapter can create a new, valid config for a materialized ETL.
        Overridden for SQLite because we need to ensure the connection is established first.
        """
        # Ensure a connection is established (adapter state is populated)
        test_config = SqliteConfig(identifier="allergies", type="sqlite")
        adapter_instance.load(test_config, "allergies")

        new_table_name = "my_new_data_product"
        new_config = adapter_instance.create_new_config_from_etl(new_table_name)

        assert adapter_instance.source_name is not None
        assert adapter_instance.database is None or isinstance(adapter_instance.database, str)
        assert adapter_instance.schema is None or isinstance(adapter_instance.schema, str)

        # Verify the config type is correct
        assert isinstance(new_config, SqliteConfig)
        # Verify it doesn't have path set (since we removed it)
        assert not hasattr(new_config, 'path') or new_config.path is None


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
            for path, conn in SqliteAdapter._instance._connections.items():
                try:
                    conn.close()
                except Exception:
                    pass
                try:
                    if os.path.exists(path):
                        os.unlink(path)
                except Exception:
                    pass
            SqliteAdapter._instance._connections.clear()
        SqliteAdapter._instance = None
        SqliteAdapter._initialized = False

    def test_connection_caching(self):
        """Test that connections are cached and reused."""
        adapter = SqliteAdapter()
        
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        mock_profiles = {"sqlite": {"path": db_path}}
        
        with patch.object(settings, 'PROFILES', mock_profiles):
            config = SqliteConfig(identifier="test_table", type="sqlite")
            
            # First load
            adapter.load(config, "test_table")
            conn1 = adapter.connection
            
            # Second load
            adapter.load(config, "test_table")
            conn2 = adapter.connection
            
            # Should be the same connection object
            assert conn1 is conn2
        
        os.unlink(db_path)

    def test_create_view(self):
        """Test that CREATE VIEW works correctly."""
        adapter = SqliteAdapter()
        
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test_table (id INTEGER, name TEXT)")
        conn.execute("INSERT INTO test_table VALUES (1, 'Alice'), (2, 'Bob')")
        conn.commit()
        conn.close()
        
        mock_profiles = {"sqlite": {"path": db_path}}
        
        with patch.object(settings, 'PROFILES', mock_profiles):
            config = SqliteConfig(identifier="test_table", type="sqlite")
            adapter.load(config, "test_table")
            
            # Create a view
            query = "SELECT * FROM test_table WHERE id > 1"
            adapter.create_table_from_query("test_view", query, materialize="view")
            
            # Verify view exists and works
            result = adapter.to_df_from_query("SELECT * FROM test_view")
            assert len(result) == 1
            assert result.iloc[0]['name'] == 'Bob'
        
        os.unlink(db_path)

    def test_parameterized_queries(self):
        """Test that parameterized queries work correctly."""
        adapter = SqliteAdapter()
        
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test_table (id INTEGER, name TEXT)")
        conn.execute("INSERT INTO test_table VALUES (1, 'Alice'), (2, 'Bob')")
        conn.commit()
        conn.close()
        
        mock_profiles = {"sqlite": {"path": db_path}}
        
        with patch.object(settings, 'PROFILES', mock_profiles):
            config = SqliteConfig(identifier="test_table", type="sqlite")
            adapter.load(config, "test_table")
            
            # Use parameterized query
            result = adapter._execute_sql("SELECT * FROM test_table WHERE id = ?", 1)
            assert len(result) == 1
            assert result[0][1] == 'Alice'
        
        os.unlink(db_path)

    def test_safe_identifier(self):
        """Test that safe_identifier escapes double quotes correctly."""
        assert safe_identifier("test_table") == '"test_table"'
        assert safe_identifier('test"table') == '"test""table"'
        assert safe_identifier('my "crazy" table') == '"my ""crazy"" table"'

    def test_can_handle_sqlite(self):
        """Test that can_handle_sqlite correctly identifies SqliteConfig."""
        # Note: path is no longer in SqliteConfig
        valid_config = SqliteConfig(identifier="test", type="sqlite")
        assert can_handle_sqlite(valid_config) is True
        
        invalid_config = {"identifier": "test", "type": "postgres"}
        assert can_handle_sqlite(invalid_config) is False

    def test_get_composite_key_uniqueness(self):
        """Test fetching uniqueness count for composite keys."""
        adapter = SqliteAdapter()
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test_composite (col1 TEXT, col2 INTEGER)")
        conn.execute("INSERT INTO test_composite VALUES ('A', 1)")
        conn.execute("INSERT INTO test_composite VALUES ('A', 1)")
        conn.execute("INSERT INTO test_composite VALUES ('B', 2)")
        conn.commit()
        conn.close()
        
        mock_profiles = {"sqlite": {"path": db_path}}
        
        with patch.object(settings, 'PROFILES', mock_profiles):
            config = SqliteConfig(identifier="test_composite", type="sqlite")
            dataset_data = config
            
            count = adapter.get_composite_key_uniqueness(
                table_name="test_composite",
                columns=["col1", "col2"],
                dataset_data=dataset_data
            )
            assert count == 2
        os.unlink(db_path)

    def test_intersect_composite_keys_count(self):
        """Test intersection count for composite keys across tables."""
        adapter = SqliteAdapter()
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE table_a (id TEXT, ver INTEGER)")
        conn.execute("INSERT INTO table_a VALUES ('A', 1), ('B', 2), ('C', 3)")
        
        conn.execute("CREATE TABLE table_b (id TEXT, ver INTEGER)")
        conn.execute("INSERT INTO table_b VALUES ('A', 1), ('B', 99), ('D', 4)")
        conn.commit()
        conn.close()
        
        mock_profiles = {"sqlite": {"path": db_path}}
        
        with patch.object(settings, 'PROFILES', mock_profiles):
            config = SqliteConfig(identifier="table_a", type="sqlite")
            
            ds1 = DataSet(config, name="table_a")
            ds2 = DataSet(config, name="table_b")
            
            count = adapter.intersect_composite_keys_count(
                table1=ds1,
                columns1=["id", "ver"],
                table2=ds2,
                columns2=["id", "ver"]
            )
            assert count == 1
        os.unlink(db_path)

    def test_missing_profile_raises_error(self):
        """Test that adapter raises ValueError if path is missing from profiles."""
        adapter = SqliteAdapter()
        
        # Mock empty profiles
        with patch.object(settings, 'PROFILES', {}):
             config = SqliteConfig(identifier="some_table", type="sqlite")
             
             with pytest.raises(ValueError, match="SQLite database path not found"):
                 adapter.load(config, "some_table")