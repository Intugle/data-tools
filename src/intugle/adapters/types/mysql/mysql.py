import time

from typing import TYPE_CHECKING, Any, Optional

import pandas as pd

from intugle.adapters.adapter import Adapter
from intugle.adapters.factory import AdapterFactory
from intugle.adapters.models import ColumnProfile, DataSetData, ProfilingOutput
from intugle.adapters.types.mysql.models import MySQLConfig, MySQLConnectionConfig
from intugle.adapters.utils import convert_to_native
from intugle.core import settings
from intugle.core.utilities.processing import string_standardization

if TYPE_CHECKING:
    from intugle.analysis.models import DataSet

try:
    import pymysql

    MYSQL_CONNECTOR_AVAILABLE = True
except Exception:
    MYSQL_CONNECTOR_AVAILABLE = False

try:
    from sqlglot import transpile

    SQLGLOT_AVAILABLE = True
except Exception:
    SQLGLOT_AVAILABLE = False


MYSQL_AVAILABLE = MYSQL_CONNECTOR_AVAILABLE and SQLGLOT_AVAILABLE


class MySQLAdapter(Adapter):
    _instance = None
    _initialized = False

    @property
    def database(self) -> Optional[str]:
        return self._database

    @database.setter
    def database(self, value: str):
        self._database = value

    @property
    def schema(self) -> Optional[str]:
        """MySQL treats schema and database as synonymous."""
        return self._database

    @property
    def source_name(self) -> str:
        return self._source_name

    @source_name.setter
    def source_name(self, value: str):
        self._source_name = value

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        if not MYSQL_AVAILABLE:
            raise ImportError("MySQL dependencies are not installed. Please run 'pip install intugle[mysql]'.")

        self.connection: Optional[pymysql.connections.Connection] = None
        self._database: Optional[str] = None
        self._source_name: str = settings.PROFILES.get("mysql", {}).get("name", "my_mysql_source")

        self.connect()
        self._initialized = True

    def connect(self):
        connection_parameters_dict = settings.PROFILES.get("mysql", {})
        if not connection_parameters_dict:
            raise ValueError("Could not create MySQL connection. No 'mysql' section found in profiles.yml.")

        params = MySQLConnectionConfig.model_validate(connection_parameters_dict)
        self._database = params.database

        self.connection = pymysql.connect(
            user=params.user,
            password=params.password,
            host=params.host,
            port=params.port,
            database=params.database,
        )

    def _get_connection(self):
        """Ensures the connection is active and returns it."""
        if self.connection is None:
            self.connect()
        else:
            self.connection.ping(reconnect=True)
        return self.connection

    @staticmethod
    def _quote_id(identifier: str) -> str:
        """Safely quotes a MySQL identifier (table or column name)."""
        # Basic protection: escape backticks to prevent breaking out of quotes
        return f"`{identifier.replace('`', '``')}`"

    def _get_fqn(self, identifier: str) -> str:
        if "." in identifier:
            parts = identifier.split(".")
            return ".".join(self._quote_id(p) for p in parts)
        return f"{self._quote_id(self.database)}.{self._quote_id(identifier)}"

    @staticmethod
    def check_data(data: Any) -> MySQLConfig:
        try:
            data = MySQLConfig.model_validate(data)
        except Exception:
            raise TypeError("Input must be a MySQL config.")
        return data

    def _execute_sql(self, query: str, *args) -> list[Any]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, args or None)
            rows = cursor.fetchall()
            return rows
        finally:
            cursor.close()

    def _get_pandas_df(self, query: str, *args) -> pd.DataFrame:
        conn = self._get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        try:
            cursor.execute(query, args or None)
            rows = cursor.fetchall()
            if not rows:
                return pd.DataFrame()
            return pd.DataFrame(rows)
        finally:
            cursor.close()

    def profile(self, data: MySQLConfig, table_name: str) -> ProfilingOutput:
        data = self.check_data(data)
        fqn = self._get_fqn(data.identifier)

        # Count query - fqn is already safely quoted by _get_fqn
        total_count = self._execute_sql(f"SELECT COUNT(*) FROM {fqn}")[0][0]

        query = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        """
        # Use self.database instead of self._schema
        rows = self._execute_sql(query, self.database, data.identifier)
        columns = [row[0] for row in rows]
        dtypes = {row[0]: row[1] for row in rows}

        return ProfilingOutput(
            count=total_count,
            columns=columns,
            dtypes=dtypes,
        )

    def column_profile(
        self,
        data: MySQLConfig,
        table_name: str,
        column_name: str,
        total_count: int,
        sample_limit: int = 10,
        dtype_sample_limit: int = 10000,
    ) -> Optional[ColumnProfile]:
        data = self.check_data(data)
        fqn = self._get_fqn(data.identifier)
        start_ts = time.time()

        quoted_col = self._quote_id(column_name)

        # Null and distinct counts using CASE WHEN because MySQL doesn't support FILTER
        query = f"""
        SELECT
            SUM(CASE WHEN {quoted_col} IS NULL THEN 1 ELSE 0 END) as null_count,
            COUNT(DISTINCT {quoted_col}) as distinct_count
        FROM {fqn}
        """
        result = self._execute_sql(query)[0]
        null_count = int(result[0]) if result[0] is not None else 0
        distinct_count = int(result[1])
        not_null_count = total_count - null_count

        # Sampling
        # Use parameters for LIMIT
        sample_query = f"SELECT DISTINCT CAST({quoted_col} AS CHAR) FROM {fqn} WHERE {quoted_col} IS NOT NULL LIMIT %s"
        distinct_values_result = self._execute_sql(sample_query, dtype_sample_limit)
        distinct_values = [row[0] for row in distinct_values_result]

        if distinct_count > 0:
            distinct_sample_size = min(distinct_count, dtype_sample_limit)
            # avoid numpy; use python sampling when possible
            import random

            sample_data = random.sample(distinct_values, min(len(distinct_values), distinct_sample_size))
        else:
            sample_data = []

        dtype_sample = None
        if distinct_count >= dtype_sample_limit:
            dtype_sample = sample_data
        elif distinct_count > 0 and not_null_count > 0:
            remaining_sample_size = max(0, dtype_sample_limit - distinct_count)
            # ORDER BY RAND() is inefficient but kept for simplicity as per plan
            additional_samples_query = (
                f"SELECT CAST({quoted_col} AS CHAR) FROM {fqn} WHERE {quoted_col} IS NOT NULL ORDER BY RAND() LIMIT %s"
            )
            additional_samples_result = self._execute_sql(additional_samples_query, remaining_sample_size)
            additional_samples = [row[0] for row in additional_samples_result]
            dtype_sample = list(distinct_values) + additional_samples
        else:
            dtype_sample = []

        native_sample_data = convert_to_native(sample_data)
        native_dtype_sample = convert_to_native(dtype_sample)
        business_name = string_standardization(column_name)

        return ColumnProfile(
            column_name=column_name,
            table_name=table_name,
            business_name=business_name,
            null_count=null_count,
            count=total_count,
            distinct_count=distinct_count,
            uniqueness=distinct_count / total_count if total_count > 0 else 0.0,
            completeness=not_null_count / total_count if total_count > 0 else 0.0,
            sample_data=native_sample_data[:sample_limit],
            dtype_sample=native_dtype_sample,
            ts=time.time() - start_ts,
        )

    def load(self, data: MySQLConfig, table_name: str):
        self.check_data(data)
        # No-op: assume table exists in MySQL

    def execute(self, query: str):
        return self._execute_sql(query)

    def to_df(self, data: MySQLConfig, table_name: str) -> pd.DataFrame:
        data = self.check_data(data)
        fqn = self._get_fqn(data.identifier)
        return self._get_pandas_df(f"SELECT * FROM {fqn}")

    def to_df_from_query(self, query: str) -> pd.DataFrame:
        return self._get_pandas_df(query)

    def create_table_from_query(self, table_name: str, query: str, materialize: str = "view", **kwargs) -> str:
        fqn = self._get_fqn(table_name)
        transpiled_sql = transpile(query, write="mysql")[0]
        if materialize == "table":
            self._execute_sql(f"DROP TABLE IF EXISTS {fqn}")
            self._execute_sql(f"CREATE TABLE {fqn} AS {transpiled_sql}")
        else:
            # MySQL does not have materialized views in the same way; create/replace view
            self._execute_sql(f"DROP VIEW IF EXISTS {fqn}")
            self._execute_sql(f"CREATE OR REPLACE VIEW {fqn} AS {transpiled_sql}")
        return transpiled_sql

    def create_new_config_from_etl(self, etl_name: str) -> "DataSetData":
        return MySQLConfig(identifier=etl_name)

    def intersect_count(self, table1: "DataSet", column1_name: str, table2: "DataSet", column2_name: str) -> int:
        table1_adapter = self.check_data(table1.data)
        table2_adapter = self.check_data(table2.data)

        fqn1 = self._get_fqn(table1_adapter.identifier)
        fqn2 = self._get_fqn(table2_adapter.identifier)

        col1 = self._quote_id(column1_name)
        col2 = self._quote_id(column2_name)

        query = f"""
        SELECT COUNT(*) FROM (
            SELECT DISTINCT {col1} FROM {fqn1} WHERE {col1} IS NOT NULL
            INTERSECT
            SELECT DISTINCT {col2} FROM {fqn2} WHERE {col2} IS NOT NULL
        ) as t
        """
        return self._execute_sql(query)[0][0]

    def get_composite_key_uniqueness(self, table_name: str, columns: list[str], dataset_data: DataSetData) -> int:
        data = self.check_data(dataset_data)
        fqn = self._get_fqn(data.identifier)
        safe_columns = [self._quote_id(col) for col in columns]
        column_list = ", ".join(safe_columns)
        null_cols_filter = " AND ".join(f"{c} IS NOT NULL" for c in safe_columns)

        query = f"""
        SELECT COUNT(*) FROM (
            SELECT DISTINCT {column_list} FROM {fqn}
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
        table1_adapter = self.check_data(table1.data)
        table2_adapter = self.check_data(table2.data)

        fqn1 = self._get_fqn(table1_adapter.identifier)
        fqn2 = self._get_fqn(table2_adapter.identifier)

        safe_columns1 = [self._quote_id(col) for col in columns1]
        safe_columns2 = [self._quote_id(col) for col in columns2]

        distinct_cols1 = ", ".join(safe_columns1)
        null_filter1 = " AND ".join(f"{c} IS NOT NULL" for c in safe_columns1)
        subquery1 = f"(SELECT DISTINCT {distinct_cols1} FROM {fqn1} WHERE {null_filter1}) AS t1"

        distinct_cols2 = ", ".join(safe_columns2)
        null_filter2 = " AND ".join(f"{c} IS NOT NULL" for c in safe_columns2)
        subquery2 = f"(SELECT DISTINCT {distinct_cols2} FROM {fqn2} WHERE {null_filter2}) AS t2"

        join_conditions = " AND ".join([f"t1.{c1} = t2.{c2}" for c1, c2 in zip(safe_columns1, safe_columns2)])

        query = f"""
        SELECT COUNT(*)
        FROM {subquery1}
        INNER JOIN {subquery2} ON {join_conditions}
        """
        return self._execute_sql(query)[0][0]

    def get_details(self, data: MySQLConfig):
        data = self.check_data(data)
        return data.model_dump()


def can_handle_mysql(df: Any) -> bool:
    try:
        MySQLConfig.model_validate(df)
        return True
    except Exception:
        return False


def register(factory: AdapterFactory):
    if MYSQL_AVAILABLE:
        factory.register("mysql", can_handle_mysql, MySQLAdapter, MySQLConfig)
