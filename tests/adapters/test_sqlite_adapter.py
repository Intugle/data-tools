"""
SQLite Adapter Tests

Tests for the SQLite adapter following the BaseAdapterTests pattern.
"""

import os

import sqlite3

import tempfile

from unittest.mock import patch



import pytest

import pandas as pd



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





def get_healthcare_config(table_name: str) -> SqliteConfig:

    """Helper function to create a SqliteConfig for a healthcare table."""

    # Try to find the CSV, but allow fallback if not present

    csv_path = f"sample_data/healthcare/{table_name}.csv"

    db_path = create_test_database(table_name, csv_path)

    return SqliteConfig(identifier=table_name, path=db_path, type="sqlite")





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

    def test_data(self):

        """Provides a SqliteConfig pointing to the allergies test table."""

        return get_healthcare_config("allergies")



    @pytest.fixture

    def table1_dataset(self) -> DataSet:

        """Provides the 'patients' dataset for intersection tests."""

        # Note: For intersection tests to work in SQLite, tables must be in the SAME database.

        # We need to manually construct a shared DB.

        fd, db_path = tempfile.mkstemp(suffix='.db')

        os.close(fd)

        

        # Load both tables into this DB

        conn = sqlite3.connect(db_path)

        

        # Patients

        p_csv = "sample_data/healthcare/patients.csv"

        if os.path.exists(p_csv):

            pd.read_csv(p_csv).to_sql("patients", conn, index=False)

        else:

             pd.DataFrame({'Id': ['P1', 'P2'], 'name': ['A', 'B']}).to_sql("patients", conn, index=False)



        # Allergies

        a_csv = "sample_data/healthcare/allergies.csv"

        if os.path.exists(a_csv):

            pd.read_csv(a_csv).to_sql("allergies", conn, index=False)

        else:

             pd.DataFrame({'PATIENT': ['P1', 'P3'], 'desc': ['X', 'Y']}).to_sql("allergies", conn, index=False)

        

        conn.close()

        

        config = SqliteConfig(identifier="patients", path=db_path, type="sqlite")

        return DataSet(config, name="patients")



    @pytest.fixture

    def table2_dataset(self, table1_dataset) -> DataSet:

        """Provides the 'allergies' dataset for intersection tests."""

        # Reuse the same config (same DB file) as table1

        return DataSet(table1_dataset.data, name="allergies")



    def test_create_new_config_from_etl(self, adapter_instance):

        """

        Tests that the adapter can create a new, valid config for a materialized ETL.

        Overridden for SQLite because we need to ensure the connection is established first.

        """

        # Ensure a connection is established (adapter state is populated)

        test_config = get_healthcare_config("allergies")

        adapter_instance.load(test_config, "allergies")



        new_table_name = "my_new_data_product"

        new_config = adapter_instance.create_new_config_from_etl(new_table_name)



        assert adapter_instance.source_name is not None

        assert adapter_instance.database is None or isinstance(adapter_instance.database, str)

        assert adapter_instance.schema is None or isinstance(adapter_instance.schema, str)



        # Verify the config type is correct

        assert isinstance(new_config, SqliteConfig)

        assert new_config.path == test_config.path





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

        

        # Create a temporary database

        fd, db_path = tempfile.mkstemp(suffix='.db')

        os.close(fd)

        

        config = SqliteConfig(identifier="test_table", path=db_path, type="sqlite")

        

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

        

        config1 = SqliteConfig(identifier="table1", path=db_path1, type="sqlite")

        config2 = SqliteConfig(identifier="table2", path=db_path2, type="sqlite")

        

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

        

        config = SqliteConfig(identifier="test_table", path=db_path, type="sqlite")

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

        

        config = SqliteConfig(identifier="test_table", path=db_path, type="sqlite")

        adapter.load(config, "test_table")

        

        # Use parameterized query

        result = adapter._execute_sql("SELECT * FROM test_table WHERE id = ?", 1)

        assert len(result) == 1

        assert result[0][1] == 'Alice'

        

        # Cleanup

        os.unlink(db_path)



    def test_safe_identifier(self):

        """Test that safe_identifier escapes double quotes correctly."""

        # Valid identifier (simple)

        assert safe_identifier("test_table") == '"test_table"'

        

        # Identifier with quotes (should be escaped)

        assert safe_identifier('test"table') == '"test""table"'

        

        # Complex case

        assert safe_identifier('my "crazy" table') == '"my ""crazy"" table"'



    def test_can_handle_sqlite(self):

        """Test that can_handle_sqlite correctly identifies SqliteConfig."""

        valid_config = SqliteConfig(identifier="test", path="/tmp/test.db", type="sqlite")

        assert can_handle_sqlite(valid_config) is True

        

        invalid_config = {"path": "/tmp/test.db", "type": "postgres"}

        assert can_handle_sqlite(invalid_config) is False



    def test_get_composite_key_uniqueness(self):

        """Test fetching uniqueness count for composite keys."""

        adapter = SqliteAdapter()

        fd, db_path = tempfile.mkstemp(suffix='.db')

        os.close(fd)

        

        conn = sqlite3.connect(db_path)

        conn.execute("CREATE TABLE test_composite (col1 TEXT, col2 INTEGER)")

        # Insert 3 rows, 2 distinct combinations

        # ('A', 1)

        # ('A', 1) -> duplicate

        # ('B', 2)

        conn.execute("INSERT INTO test_composite VALUES ('A', 1)")

        conn.execute("INSERT INTO test_composite VALUES ('A', 1)")

        conn.execute("INSERT INTO test_composite VALUES ('B', 2)")

        conn.commit()

        conn.close()

        

        config = SqliteConfig(identifier="test_composite", path=db_path, type="sqlite")

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

        # Table A: ('A', 1), ('B', 2), ('C', 3)

        conn.execute("CREATE TABLE table_a (id TEXT, ver INTEGER)")

        conn.execute("INSERT INTO table_a VALUES ('A', 1), ('B', 2), ('C', 3)")

        

        # Table B: ('A', 1), ('B', 99), ('D', 4)

        # Intersection: ('A', 1) -> count should be 1

        conn.execute("CREATE TABLE table_b (id TEXT, ver INTEGER)")

        conn.execute("INSERT INTO table_b VALUES ('A', 1), ('B', 99), ('D', 4)")

        conn.commit()

        conn.close()

        

        config = SqliteConfig(identifier="table_a", path=db_path, type="sqlite")

        

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



    def test_profiles_fallback(self):

        """Test that adapter falls back to settings.PROFILES if path is missing."""

        adapter = SqliteAdapter()

        

        fd, db_path = tempfile.mkstemp(suffix='.db')

        os.close(fd)

        

        # Mock settings.PROFILES

        mock_profiles = {"sqlite": {"path": db_path}}

        

        with patch.object(settings, 'PROFILES', mock_profiles):

             # Config without path

             config = SqliteConfig(identifier="some_table")

             

             # Should succeed by using the mocked profile path

             adapter.load(config, "some_table")

             assert adapter._current_path == db_path

             assert db_path in adapter._connections

        

        os.unlink(db_path)
