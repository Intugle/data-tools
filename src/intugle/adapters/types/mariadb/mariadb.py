import random
import time

from typing import TYPE_CHECKING, Any, Optional

import pandas as pd

from intugle.adapters.adapter import Adapter
from intugle.adapters.factory import AdapterFactory
from intugle.adapters.models import ColumnProfile, DataSetData, ProfilingOutput
from intugle.adapters.types.mariadb.models import MariaDBConfig, MariaDBConnectionConfig
from intugle.adapters.utils import convert_to_native
from intugle.core import settings
from intugle.core.utilities.processing import string_standardization

if TYPE_CHECKING:
    from intugle.analysis.models import DataSet

try:
    import mariadb

    MARIADB_CONNECTOR_AVAILABLE = True
except Exception:
    MARIADB_CONNECTOR_AVAILABLE = False

try:
    from sqlglot import transpile

    SQLGLOT_AVAILABLE = True
except Exception:
    SQLGLOT_AVAILABLE = False


MARIADB_AVAILABLE = MARIADB_CONNECTOR_AVAILABLE and SQLGLOT_AVAILABLE


class MariaDBAdapter(Adapter):
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
        """MariaDB treats schema and database as synonymous."""
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

        if not MARIADB_AVAILABLE:
            raise ImportError("MariaDB dependencies are not installed. Please run 'pip install intugle[mariadb]'.")

        self.connection: Optional[mariadb.Connection] = None
        self._database: Optional[str] = None
        self._source_name: str = settings.PROFILES.get("mariadb", {}).get("name", "my_mariadb_source")

        self.connect()
        self._initialized = True

    def connect(self):
        connection_parameters_dict = settings.PROFILES.get("mariadb", {})
        if not connection_parameters_dict:
            raise ValueError("Could not create MariaDB connection. No 'mariadb' section found in profiles.yml.")

        params = MariaDBConnectionConfig.model_validate(connection_parameters_dict)
        self._database = params.database

        self.connection = mariadb.connect(
            user=params.user,
            password=params.password,
            host=params.host,
            port=params.port,
            database=params.database,
            autocommit=True
        )

    def _get_connection(self):
        """Ensures the connection is active and returns it."""
        # Check if connection is closed (None or not connected)
        # Note: mariadb python connector might not have a simple is_connected property like others
        # We'll rely on try-except or simple check. 
        # For this implementation, we assume connection stays alive or we reconnect if needed.
        if self.connection is None:
            self.connect()
        return self.connection

    @staticmethod
    def _quote_id(identifier: str) -> str:
        """Safely quotes a MariaDB identifier (table or column name)."""
        return f"`{identifier.replace('`', '``')}`"

    def _get_fqn(self, identifier: str) -> str:
        if "." in identifier:
            parts = identifier.split(".")
            return ".".join(self._quote_id(p) for p in parts)
        return f"{self._quote_id(self.database)}.{self._quote_id(identifier)}"

    @staticmethod
    def check_data(data: Any) -> MariaDBConfig:
        try:
            data = MariaDBConfig.model_validate(data)
        except Exception:
            raise TypeError("Input must be a MariaDB config.")
        return data

    def _execute_sql(self, query: str, *args) -> list[Any]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # mariadb connector uses ? for placeholders usually, but let's check params
            # Standard python dbapi uses %s or ?. mariadb uses ?.
            # Wait, mariadb connector documentation says parameters are supported
            # pymysql uses %s. mariadb uses ?.
            # We need to ensure args are passed safely.
            # If args is a tuple of 1 element which is a list, it might be weird.
            # *args makes it a tuple.
            
            # Note: The query construction in previous adapters (e.g., MySQL) used %s
            # We must be careful about placeholders.
            # For simplicity, if we see %s in query we might need to change it if mariadb expects ?
            # But sqlglot transpile might handle dialects.
            # Let's assume ? for mariadb as per standard or check docs if possible. 
            # Actually, mariadb-connector-python uses ? usually.
            # But let's check what MySQLAdapter did:
            # MySQLAdapter used %s.
            # Let's try to stick to what the driver expects.
            # If the driver expects ?, and our queries (like in profile) use %s, we might fail.
            # We will use ? for now.
            cursor.execute(query, args or None)
            
            # mariadb cursor might not fetchall() if no result.
            if cursor.description:
                rows = cursor.fetchall()
                return rows
            return []
        finally:
            cursor.close()

    def _get_pandas_df(self, query: str, *args) -> pd.DataFrame:
        conn = self._get_connection()
        # named_tuple=False gives tuples. dictionary=True gives dicts
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, args or None)
            if cursor.description:
                rows = cursor.fetchall()
                if not rows:
                    return pd.DataFrame()
                return pd.DataFrame(rows)
            return pd.DataFrame()
        finally:
            cursor.close()

    def profile(self, data: MariaDBConfig, table_name: str) -> ProfilingOutput:
        data = self.check_data(data)
        fqn = self._get_fqn(data.identifier)

        total_count_res = self._execute_sql(f"SELECT COUNT(*) FROM {fqn}")
        total_count = total_count_res[0][0]

        # Use ? for placeholder
        query = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = ? AND table_name = ?
        """
        rows = self._execute_sql(query, self.database, data.identifier)
        # rows are tuples if not dict cursor
        columns = [row[0] for row in rows]
        dtypes = {row[0]: row[1] for row in rows}

        return ProfilingOutput(
            count=total_count,
            columns=columns,
            dtypes=dtypes,
        )

    def column_profile(
        self,
        data: MariaDBConfig,
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

        # Null and distinct counts
        query = f"""
        SELECT
            SUM(CASE WHEN {quoted_col} IS NULL THEN 1 ELSE 0 END) as null_count,
            COUNT(DISTINCT {quoted_col}) as distinct_count
        FROM {fqn}
        """
        result = self._execute_sql(query)[0]
        # result is like (null_count, distinct_count)
        null_count = int(result[0]) if result[0] is not None else 0
        distinct_count = int(result[1])
        not_null_count = total_count - null_count

        # Sampling
        sample_query = f"SELECT DISTINCT CAST({quoted_col} AS CHAR) FROM {fqn} WHERE {quoted_col} IS NOT NULL LIMIT ?"
        distinct_values_result = self._execute_sql(sample_query, dtype_sample_limit)
        distinct_values = [row[0] for row in distinct_values_result]

        if distinct_count > 0:
            distinct_sample_size = min(distinct_count, dtype_sample_limit)
            sample_data = random.sample(distinct_values, min(len(distinct_values), distinct_sample_size))
        else:
            sample_data = []

        dtype_sample = None
        if distinct_count >= dtype_sample_limit:
            dtype_sample = sample_data
        elif distinct_count > 0 and not_null_count > 0:
            remaining_sample_size = max(0, dtype_sample_limit - distinct_count)
            # ORDER BY RAND()
            additional_samples_query = (
                f"SELECT CAST({quoted_col} AS CHAR) FROM {fqn} WHERE {quoted_col} IS NOT NULL ORDER BY RAND() LIMIT ?"
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

    def load(self, data: MariaDBConfig, table_name: str):
        self.check_data(data)
        pass

    def execute(self, query: str):
        return self._execute_sql(query)

    def to_df(self, data: MariaDBConfig, table_name: str) -> pd.DataFrame:
        data = self.check_data(data)
        fqn = self._get_fqn(data.identifier)
        return self._get_pandas_df(f"SELECT * FROM {fqn}")

    def to_df_from_query(self, query: str) -> pd.DataFrame:
        return self._get_pandas_df(query)

    def create_table_from_query(self, table_name: str, query: str, materialize: str = "view", **kwargs) -> str:
        fqn = self._get_fqn(table_name)
        # Use mysql dialect for transpile as mariadb is very similar and sqlglot might not have explicit mariadb or it aliases mysql
        transpiled_sql = transpile(query, write="mysql")[0]
        if materialize == "table":
            self._execute_sql(f"DROP TABLE IF EXISTS {fqn}")
            self._execute_sql(f"CREATE TABLE {fqn} AS {transpiled_sql}")
        else:
            self._execute_sql(f"DROP VIEW IF EXISTS {fqn}")
            self._execute_sql(f"CREATE OR REPLACE VIEW {fqn} AS {transpiled_sql}")
        return transpiled_sql

    def create_new_config_from_etl(self, etl_name: str) -> "DataSetData":
        return MariaDBConfig(identifier=etl_name)

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

    def get_details(self, data: MariaDBConfig):
        data = self.check_data(data)
        return data.model_dump()


def can_handle_mariadb(df: Any) -> bool:
    try:
        MariaDBConfig.model_validate(df)
        return True
    except Exception:
        return False


def register(factory: AdapterFactory):
    if MARIADB_AVAILABLE:
        factory.register("mariadb", can_handle_mariadb, MariaDBAdapter, MariaDBConfig)
