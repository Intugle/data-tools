import time

from typing import TYPE_CHECKING, Any, Optional

import numpy as np
import pandas as pd

from intugle.adapters.adapter import Adapter
from intugle.adapters.factory import AdapterFactory
from intugle.adapters.models import ColumnProfile, DataSetData, ProfilingOutput
from intugle.adapters.types.sqlserver.models import (
    SQLServerConfig,
    SQLServerConnectionConfig,
)
from intugle.adapters.utils import convert_to_native
from intugle.core import settings
from intugle.core.utilities.processing import string_standardization

if TYPE_CHECKING:
    from intugle.analysis.models import DataSet

try:
    import mssql_python

    MSSQL_PYTHON_AVAILABLE = True
except ImportError:
    MSSQL_PYTHON_AVAILABLE = False

try:
    from sqlglot import transpile

    SQLGLOT_AVAILABLE = True
except ImportError:
    SQLGLOT_AVAILABLE = False


SQLSERVER_AVAILABLE = MSSQL_PYTHON_AVAILABLE and SQLGLOT_AVAILABLE


class SQLServerAdapter(Adapter):
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
        return self._schema

    @schema.setter
    def schema(self, value: str):
        self._schema = value

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

        if not SQLSERVER_AVAILABLE:
            raise ImportError(
                "SQL Server dependencies are not installed. Please run 'pip install \"intugle[sqlserver]\"'."
            )

        self.connection: Optional["mssql_python.Connection"] = None
        self._database: Optional[str] = None
        self._schema: Optional[str] = None
        self._source_name: str = settings.PROFILES.get("sqlserver", {}).get(
            "name", "my_sqlserver_source"
        )

        self.connect()
        self._initialized = True

    def connect(self):
        connection_parameters_dict = settings.PROFILES.get("sqlserver", {})
        if not connection_parameters_dict:
            raise ValueError(
                "Could not create SQL Server connection. No 'sqlserver' section found in profiles.yml."
            )

        params = SQLServerConnectionConfig.model_validate(connection_parameters_dict)
        self._database = params.database
        self._schema = params.schema_

        conn_str = (
            f"SERVER={params.host},{params.port};"
            f"DATABASE={params.database};"
            f"UID={params.user};"
            f"PWD={params.password};"
            f"Encrypt={'yes' if params.encrypt else 'no'};"
        )
        self.connection = mssql_python.connect(conn_str)

    def _get_fqn(self, identifier: str) -> str:
        """Gets the fully qualified name for a table identifier."""
        if "." in identifier:
            return identifier
        return f'[{self._schema}].[{identifier}]'

    @staticmethod
    def check_data(data: Any) -> SQLServerConfig:
        try:
            data = SQLServerConfig.model_validate(data)
        except Exception:
            raise TypeError("Input must be a SQLServerConfig.")
        return data

    def _execute_sql(self, query: str, *args) -> list[Any]:
        with self.connection.cursor() as cursor:
            cursor.execute(query, *args)
            try:
                return cursor.fetchall()
            except mssql_python.ProgrammingError:  # No results
                return []

    def _get_pandas_df(self, query: str, *args) -> pd.DataFrame:
        with self.connection.cursor() as cursor:
            cursor.execute(query, *args)
            rows = cursor.fetchall()
            columns = [column[0] for column in cursor.description]
            return pd.DataFrame.from_records(rows, columns=columns)

    def profile(self, data: SQLServerConfig, table_name: str) -> ProfilingOutput:
        data = self.check_data(data)
        fqn = self._get_fqn(data.identifier)

        total_count = self._execute_sql(f"SELECT COUNT(*) FROM {fqn}")[0][0]

        query = """
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
        """
        rows = self._execute_sql(query, self._schema, data.identifier)
        columns = [row.COLUMN_NAME for row in rows]
        dtypes = {row.COLUMN_NAME: row.DATA_TYPE for row in rows}

        return ProfilingOutput(
            count=total_count,
            columns=columns,
            dtypes=dtypes,
        )

    def column_profile(
        self,
        data: SQLServerConfig,
        table_name: str,
        column_name: str,
        total_count: int,
        sample_limit: int = 10,
        dtype_sample_limit: int = 10000,
    ) -> Optional[ColumnProfile]:
        data = self.check_data(data)
        fqn = self._get_fqn(data.identifier)
        start_ts = time.time()

        # Null and distinct counts
        query = f"""
        SELECT
            SUM(CASE WHEN [{column_name}] IS NULL THEN 1 ELSE 0 END) as null_count,
            COUNT(DISTINCT [{column_name}]) as distinct_count
        FROM {fqn}
        """
        result = self._execute_sql(query)[0]
        null_count = result.null_count or 0
        distinct_count = result.distinct_count or 0
        not_null_count = total_count - null_count

        # Sampling
        sample_query = f"""
        SELECT DISTINCT TOP ({dtype_sample_limit}) [{column_name}] FROM {fqn} WHERE [{column_name}] IS NOT NULL
        """
        distinct_values_result = self._execute_sql(sample_query)
        distinct_values = [str(row[0]) for row in distinct_values_result]

        if distinct_count > 0:
            distinct_sample_size = min(distinct_count, dtype_sample_limit)
            sample_data = list(
                np.random.choice(distinct_values, distinct_sample_size, replace=False)
            )
        else:
            sample_data = []

        dtype_sample = None
        if distinct_count >= dtype_sample_limit:
            dtype_sample = sample_data
        elif distinct_count > 0 and not_null_count > 0:
            remaining_sample_size = dtype_sample_limit - distinct_count
            additional_samples_query = f"""
            SELECT TOP {remaining_sample_size} [{column_name}]
            FROM {fqn}
            WHERE [{column_name}] IS NOT NULL
            ORDER BY NEWID()
            """
            additional_samples_result = self._execute_sql(additional_samples_query)
            additional_samples = [str(row[0]) for row in additional_samples_result]
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

    def load(self, data: SQLServerConfig, table_name: str):
        self.check_data(data)
        # No-op, we assume the table already exists in SQL Server.

    def execute(self, query: str):
        return self._execute_sql(query)

    def to_df(self, data: SQLServerConfig, table_name: str) -> pd.DataFrame:
        data = self.check_data(data)
        fqn = self._get_fqn(data.identifier)
        return self._get_pandas_df(f"SELECT * FROM {fqn}")

    def to_df_from_query(self, query: str) -> pd.DataFrame:
        return self._get_pandas_df(query)

    def create_table_from_query(
        self, table_name: str, query: str, materialize: str = "view", **kwargs
    ) -> str:
        fqn = self._get_fqn(table_name)
        transpiled_sql = transpile(query, write="tsql")[0]

        # Drop existing object
        if materialize == "view":
            self._execute_sql(f"IF OBJECT_ID('{fqn}', 'V') IS NOT NULL DROP VIEW {fqn}")
            self._execute_sql(f"CREATE VIEW {fqn} AS {transpiled_sql}")
        else:  # table
            self._execute_sql(f"IF OBJECT_ID('{fqn}', 'U') IS NOT NULL DROP TABLE {fqn}")
            self._execute_sql(f"SELECT * INTO {fqn} FROM ({transpiled_sql}) as tmp")
        
        self.connection.commit()
        return transpiled_sql

    def create_new_config_from_etl(self, etl_name: str) -> "DataSetData":
        return SQLServerConfig(identifier=etl_name)

    def intersect_count(
        self, table1: "DataSet", column1_name: str, table2: "DataSet", column2_name: str
    ) -> int:
        table1_adapter = self.check_data(table1.data)
        table2_adapter = self.check_data(table2.data)

        fqn1 = self._get_fqn(table1_adapter.identifier)
        fqn2 = self._get_fqn(table2_adapter.identifier)

        query = f"""
        SELECT COUNT(DISTINCT t1.[{column1_name}])
        FROM {fqn1} AS t1
        INNER JOIN {fqn2} AS t2 ON t1.[{column1_name}] = t2.[{column2_name}]
        """
        return self._execute_sql(query)[0][0]

    def get_composite_key_uniqueness(self, table_name: str, columns: list[str], dataset_data: DataSetData) -> int:
        data = self.check_data(dataset_data)
        fqn = self._get_fqn(data.identifier)
        safe_columns = [f"[{col}]" for col in columns]
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

        safe_columns1 = [f"[{col}]" for col in columns1]
        safe_columns2 = [f"[{col}]" for col in columns2]

        # Subquery for distinct keys from table 1
        distinct_cols1 = ", ".join(safe_columns1)
        null_filter1 = " AND ".join(f"{c} IS NOT NULL" for c in safe_columns1)
        subquery1 = f"(SELECT DISTINCT {distinct_cols1} FROM {fqn1} WHERE {null_filter1}) AS t1"

        # Subquery for distinct keys from table 2
        distinct_cols2 = ", ".join(safe_columns2)
        null_filter2 = " AND ".join(f"{c} IS NOT NULL" for c in safe_columns2)
        subquery2 = f"(SELECT DISTINCT {distinct_cols2} FROM {fqn2} WHERE {null_filter2}) AS t2"

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

    def get_details(self, data: SQLServerConfig):
        data = self.check_data(data)
        return data.model_dump()


def can_handle_sqlserver(df: Any) -> bool:
    try:
        SQLServerConfig.model_validate(df)
        return True
    except Exception:
        return False


def register(factory: AdapterFactory):
    if SQLSERVER_AVAILABLE:
        factory.register(
            "sqlserver", can_handle_sqlserver, SQLServerAdapter, SQLServerConfig
        )