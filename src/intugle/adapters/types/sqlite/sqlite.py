import random
import sqlite3
import time

from typing import TYPE_CHECKING, Any, Optional

import pandas as pd

try:
    from sqlglot import transpile
    SQLGLOT_AVAILABLE = True
except ImportError:
    SQLGLOT_AVAILABLE = False

from intugle.adapters.adapter import Adapter
from intugle.adapters.factory import AdapterFactory
from intugle.adapters.models import (
    ColumnProfile,
    DataSetData,
    ProfilingOutput,
)
from intugle.adapters.types.sqlite.models import SqliteConfig
from intugle.adapters.utils import convert_to_native
from intugle.core import settings
from intugle.core.utilities.processing import string_standardization

if TYPE_CHECKING:
    from intugle.analysis.models import DataSet
    from intugle.models.manifest import Manifest


def safe_identifier(name: str) -> str:
    """
    Wraps an SQL identifier in double quotes, escaping existing double quotes.
    """
    return '"' + name.replace('"', '""') + '"'


class SqliteAdapter(Adapter):
    # Singleton pattern - reset _instance in tests if needed
    _instance = None
    _initialized = False

    @property
    def database(self) -> Optional[str]:
        return None

    @property
    def schema(self) -> Optional[str]:
        return None

    @property
    def source_name(self) -> str:
        return settings.PROFILES.get("sqlite", {}).get("name", "my_sqlite_source")

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._connections: dict[str, sqlite3.Connection] = {}
        self._current_path: Optional[str] = None
        self._initialized = True

    def _get_connection(self, data: SqliteConfig) -> sqlite3.Connection:
        """Get or create a connection to the SQLite database."""
        path = settings.PROFILES.get("sqlite", {}).get("path")
        
        if not path:
            raise ValueError(
                "SQLite database path not found. Please provide it in profiles.yml under 'sqlite' -> 'path'."
            )

        if path not in self._connections:
            conn = sqlite3.connect(path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._connections[path] = conn
        self._current_path = path
        return self._connections[path]

    @property
    def connection(self) -> Optional[sqlite3.Connection]:
        """Get the current connection based on the last loaded config."""
        if self._current_path and self._current_path in self._connections:
            return self._connections[self._current_path]
        return None

    @staticmethod
    def check_data(data: Any) -> SqliteConfig:
        try:
            data = SqliteConfig.model_validate(data)
        except Exception:
            raise TypeError("Input must be a SqliteConfig instance.")
        return data

    def _execute_sql(self, query: str, *args) -> list[Any]:
        """Execute a SQL query with parameterized arguments and return results."""
        if self.connection is None:
            raise RuntimeError("Connection not established. Call load() first.")
        with self.connection:
            cursor = self.connection.execute(query, tuple(args))
            return cursor.fetchall()

    def _get_pandas_df(self, query: str, *args) -> pd.DataFrame:
        """Execute a SQL query and return results as a pandas DataFrame."""
        rows = self._execute_sql(query, *args)
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame([dict(row) for row in rows])

    def _format_dtype(self, sqlite_type: str) -> str:
        """Convert SQLite data types to generalized types."""
        type_map = {
            "TEXT": "string",
            "VARCHAR": "string",
            "CHAR": "string",
            "DATE": "date & time",
            "DATETIME": "date & time",
            "TIMESTAMP": "date & time",
            "INTEGER": "integer",
            "INT": "integer",
            "BIGINT": "integer",
            "REAL": "float",
            "FLOAT": "float",
            "DOUBLE": "float",
            "NUMERIC": "float",
            "BLOB": "string",
        }
        return type_map.get(sqlite_type.upper(), "string")

    def profile(self, data: SqliteConfig, table_name: str) -> ProfilingOutput:
        """
        Generates a profile of a SQLite table.

        Args:
            data: The SqliteConfig instance.
            table_name: The name of the table to profile.

        Returns:
            A ProfilingOutput containing:
            - count: Total number of rows.
            - columns: List of column names.
            - dtypes: A dictionary mapping column names to generalized data types.
        """
        data = self.check_data(data)
        self.load(data, table_name)
        table_name_safe = safe_identifier(table_name)

        query = f"SELECT COUNT(*) as count FROM {table_name_safe}"
        total_count = self._execute_sql(query)[0][0]

        query = f"PRAGMA table_info({table_name_safe})"
        column_data = self._execute_sql(query)
        columns = [row[1] for row in column_data]
        dtypes = {row[1]: self._format_dtype(row[2]) for row in column_data}

        return ProfilingOutput(
            count=total_count,
            columns=columns,
            dtypes=dtypes,
        )

    def column_profile(
        self,
        data: SqliteConfig,
        table_name: str,
        column_name: str,
        total_count: int,
        sample_limit: int = 10,
        dtype_sample_limit: int = 10000,
    ) -> ColumnProfile:
        """
        Generates a detailed profile for a single column of a SQLite table.

        Args:
            data: The SqliteConfig instance.
            table_name: The name of the table.
            column_name: The name of the column to profile.
            total_count: The total number of rows in the table.
            sample_limit: The desired number of items for the sample_data.
            dtype_sample_limit: The desired number of items for the dtype_sample.

        Returns:
            A ColumnProfile containing detailed statistics about the column.
        """
        data = self.check_data(data)
        self.load(data, table_name)
        table_name_safe = safe_identifier(table_name)
        column_name_safe = safe_identifier(column_name)
        start_ts = time.time()

        query = f"""
        SELECT 
            COUNT(DISTINCT {column_name_safe}) AS distinct_count,
            COALESCE(SUM(CASE WHEN {column_name_safe} IS NULL THEN 1 ELSE 0 END), 0) AS null_count
        FROM {table_name_safe}
        """
        result = self._execute_sql(query)[0]
        distinct_count = result[0]
        null_count = result[1]
        not_null_count = total_count - null_count

        sample_query = f"""
        SELECT DISTINCT {column_name_safe}
        FROM {table_name_safe}
        WHERE {column_name_safe} IS NOT NULL
        LIMIT ?
        """
        distinct_values_result = self._execute_sql(sample_query, dtype_sample_limit)
        distinct_values = [row[0] for row in distinct_values_result]

        if distinct_count > 0 and len(distinct_values) > 0:
            sample_size = min(sample_limit, len(distinct_values))
            sample_data = random.sample(distinct_values, sample_size)
        else:
            sample_data = []

        dtype_sample = distinct_values[:dtype_sample_limit]

        native_sample_data = convert_to_native(sample_data)
        native_dtype_sample = convert_to_native(dtype_sample)
        business_name = string_standardization(column_name)

        return ColumnProfile(
            column_name=column_name,
            business_name=business_name,
            table_name=table_name,
            null_count=null_count,
            count=total_count,
            distinct_count=distinct_count,
            uniqueness=distinct_count / total_count if total_count > 0 else 0.0,
            completeness=not_null_count / total_count if total_count > 0 else 0.0,
            sample_data=native_sample_data,
            dtype_sample=native_dtype_sample,
            ts=time.time() - start_ts,
        )

    def load(self, data: SqliteConfig, table_name: str):
        """
        Load/connect to the SQLite database. This establishes the connection.
        
        Connections are cached per database path and reused across calls to avoid
        unnecessary connection overhead. The table_name parameter is required by
        the interface but not used by SQLite.

        Args:
            data: The SqliteConfig instance.
            table_name: The name of the table (required by interface, unused).
        """
        data = self.check_data(data)
        self._get_connection(data)

    def execute(self, query: str):
        """Execute a raw SQL query and return results as a list of dictionaries."""
        if self.connection is None:
            raise RuntimeError("Connection not established. Call load() first.")
        rows = self._execute_sql(query)
        return [dict(row) for row in rows]

    def to_df(self, data: SqliteConfig, table_name: str) -> pd.DataFrame:
        """
        Convert a SQLite table into a pandas DataFrame.

        Args:
            data: The SqliteConfig instance.
            table_name: The name of the table.

        Returns:
            A pandas DataFrame containing all rows from the table.
        """
        data = self.check_data(data)
        self.load(data, table_name)
        table_name_safe = safe_identifier(table_name)
        query = f"SELECT * FROM {table_name_safe}"
        return self._get_pandas_df(query)

    def to_df_from_query(self, query: str) -> pd.DataFrame:
        """
        Execute a SQL query and return results as a pandas DataFrame.

        Args:
            query: The SQL query to execute.

        Returns:
            A pandas DataFrame containing the query results.
        """
        if self.connection is None:
            raise RuntimeError("Connection not established. Call load() first.")
        return self._get_pandas_df(query)

    def create_table_from_query(
        self, table_name: str, query: str, materialize: str = "view", **kwargs
    ) -> str:
        """
        Create a new table or view from a SQL query.

        Args:
            table_name: The name of the new table/view.
            query: The SQL query to materialize.
            materialize: Either "table" or "view".

        Returns:
            The SQL query that was executed.
        """
        if self.connection is None:
            raise RuntimeError("Connection not established. Call load() first.")
        
        table_name_safe = safe_identifier(table_name)
        
        # Transpile the query to SQLite dialect if possible
        final_query = query
        if SQLGLOT_AVAILABLE:
            final_query = transpile(query, read=None, write="sqlite")[0]

        if materialize == "table":
            self._execute_sql(f"DROP TABLE IF EXISTS {table_name_safe}")
            self._execute_sql(f"CREATE TABLE {table_name_safe} AS {final_query}")
        else:
            self._execute_sql(f"DROP VIEW IF EXISTS {table_name_safe}")
            self._execute_sql(f"CREATE VIEW {table_name_safe} AS {final_query}")
        
        return final_query

    def create_new_config_from_etl(self, etl_name: str) -> DataSetData:
        """
        Create a new SqliteConfig for a table created via ETL.

        Args:
            etl_name: The name of the table that was created.

        Returns:
            A new SqliteConfig instance.
        """
        if self._current_path is None:
            raise RuntimeError("Connection not established. Cannot create config.")
        return SqliteConfig(identifier=etl_name, type="sqlite")

    def deploy_semantic_model(self, manifest: "Manifest", **kwargs):
        """Deploys a semantic model to the target system."""
        raise NotImplementedError("Deployment is not supported for the SqliteAdapter.")

    def intersect_count(
        self, table1: "DataSet", column1_name: str, table2: "DataSet", column2_name: str
    ) -> int:
        """
        Calculate the intersection count between two columns from different tables.
        Assumes both tables are in the same SQLite database.

        Args:
            table1: The first DataSet.
            column1_name: The column name from the first table.
            table2: The second DataSet.
            column2_name: The column name from the second table.

        Returns:
            The count of distinct values that appear in both columns.
        """
        table1_config = self.check_data(table1.data)
        self.check_data(table2.data)
        
        self.load(table1_config, table1.name)
        
        # Assumption: In the single-profile-path model, all tables accessed 
        # via this adapter instance reside in the same database.
        
        table1_name_safe = safe_identifier(table1.name)
        table2_name_safe = safe_identifier(table2.name)
        column1_safe = safe_identifier(column1_name)
        column2_safe = safe_identifier(column2_name)

        query = f"""
        SELECT COUNT(*) as intersect_count FROM (
            SELECT DISTINCT {column1_safe} FROM {table1_name_safe} WHERE {column1_safe} IS NOT NULL
            INTERSECT
            SELECT DISTINCT {column2_safe} FROM {table2_name_safe} WHERE {column2_safe} IS NOT NULL
        ) as t
        """
        result = self.execute(query)
        return result[0]["intersect_count"]

    def get_composite_key_uniqueness(
        self, table_name: str, columns: list[str], dataset_data: DataSetData
    ) -> int:
        """
        Calculate the count of unique composite keys in a table.

        Args:
            table_name: The name of the table.
            columns: List of column names forming the composite key.
            dataset_data: The dataset configuration.

        Returns:
            The count of unique composite keys.
        """
        data = self.check_data(dataset_data)
        self.load(data, table_name)
        
        table_name_safe = safe_identifier(table_name)
        safe_columns = [safe_identifier(col) for col in columns]
        column_list = ", ".join(safe_columns)
        null_cols_filter = " AND ".join(f"{c} IS NOT NULL" for c in safe_columns)

        query = f"""
        SELECT COUNT(*) FROM (
            SELECT DISTINCT {column_list} FROM {table_name_safe}
            WHERE {null_cols_filter}
        ) as t
        """
        return self._execute_sql(query)[0][0]

    def intersect_composite_keys_count(
        self,
        table1: "DataSet",
        columns1: list[str],
        table2: "DataSet",
        columns2: list[str],
    ) -> int:
        """
        Calculate the intersection count of composite keys between two tables.
        Assumes both tables are in the same SQLite database.

        Args:
            table1: The first DataSet.
            columns1: List of column names from the first table.
            table2: The second DataSet.
            columns2: List of column names from the second table.

        Returns:
            The count of matching composite keys found in both tables.
        """
        table1_config = self.check_data(table1.data)
        self.check_data(table2.data)
        
        self.load(table1_config, table1.name)
        
        fqn1 = safe_identifier(table1.name)
        fqn2 = safe_identifier(table2.name)

        safe_columns1 = [safe_identifier(col) for col in columns1]
        safe_columns2 = [safe_identifier(col) for col in columns2]

        # Subquery for distinct keys from table 1
        distinct_cols1 = ", ".join(safe_columns1)
        null_filter1 = " AND ".join(f"{c} IS NOT NULL" for c in safe_columns1)
        subquery1 = f'(SELECT DISTINCT {distinct_cols1} FROM {fqn1} WHERE {null_filter1}) AS t1'

        # Subquery for distinct keys from table 2
        distinct_cols2 = ", ".join(safe_columns2)
        null_filter2 = " AND ".join(f"{c} IS NOT NULL" for c in safe_columns2)
        subquery2 = f'(SELECT DISTINCT {distinct_cols2} FROM {fqn2} WHERE {null_filter2}) AS t2'

        # Join conditions
        join_conditions = " AND ".join(
            [f"t1.{c1} = t2.{c2}" for c1, c2 in zip(safe_columns1, safe_columns2)]
        )

        query = f"""
        SELECT COUNT(*)
        FROM {subquery1}
        INNER JOIN {subquery2} ON {join_conditions}
        """
        return self._execute_sql(query)[0][0]

    def get_details(self, data: SqliteConfig):
        """
        Return the adapter's configuration details.

        Args:
            data: The SqliteConfig instance

        Returns:
            A dictionary containing the configuration details.
        """
        data = self.check_data(data)
        return data.model_dump()


def can_handle_sqlite(df: Any) -> bool:
    """
    Check if the given data can be handled by the SqliteAdapter.

    Args:
        df: The data to check.

    Returns:
        True if the data is a SqliteConfig, False otherwise.
    """
    try:
        SqliteConfig.model_validate(df)
        return True
    except Exception:
        return False


def register(factory: AdapterFactory):
    """
    Register the SqliteAdapter with the AdapterFactory.

    Args:
        factory: The AdapterFactory instance to register with.
    """
    factory.register("sqlite", can_handle_sqlite, SqliteAdapter, SqliteConfig)
