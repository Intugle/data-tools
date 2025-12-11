import time

from typing import TYPE_CHECKING, Any, Optional

import numpy as np
import pandas as pd

from intugle.adapters.adapter import Adapter
from intugle.adapters.factory import AdapterFactory
from intugle.adapters.models import ColumnProfile, DataSetData, ProfilingOutput
from intugle.adapters.types.oracle.models import OracleConfig, OracleConnectionConfig
from intugle.adapters.utils import convert_to_native
from intugle.core import settings
from intugle.core.utilities.processing import string_standardization

if TYPE_CHECKING:
    from intugle.analysis.models import DataSet

try:
    import oracledb

    ORACLE_AVAILABLE = True
except ImportError:
    ORACLE_AVAILABLE = False

try:
    from sqlglot import transpile

    SQLGLOT_AVAILABLE = True
except ImportError:
    SQLGLOT_AVAILABLE = False

ORACLE_ADAPTER_AVAILABLE = ORACLE_AVAILABLE and SQLGLOT_AVAILABLE


class OracleAdapter(Adapter):
    _instance = None
    _initialized = False

    @property
    def database(self) -> Optional[str]:
        # Oracle doesn't have a 'database' concept like Postgres/MySQL in the same way.
        # It's usually the Service Name or SID. We'll return the service_name if available.
        return self._service_name or self._sid

    @property
    def schema(self) -> Optional[str]:
        return self._schema

    @property
    def source_name(self) -> str:
        return self._source_name

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        if not ORACLE_ADAPTER_AVAILABLE:
            raise ImportError(
                "Oracle dependencies are not installed. Please run 'pip install intugle[oracle]'."
            )

        self.connection: Optional["oracledb.Connection"] = None
        self._service_name: Optional[str] = None
        self._sid: Optional[str] = None
        self._schema: Optional[str] = None
        self._source_name: str = settings.PROFILES.get("oracle", {}).get("name", "my_oracle_source")

        self.connect()
        self._initialized = True

    def connect(self):
        connection_parameters_dict = settings.PROFILES.get("oracle", {})
        if not connection_parameters_dict:
            raise ValueError("Could not create Oracle connection. No 'oracle' section found in profiles.yml.")

        params = OracleConnectionConfig.model_validate(connection_parameters_dict)
        self._service_name = params.service_name
        self._sid = params.sid
        # Default to user if schema is not provided, common in Oracle
        self._schema = params.schema_ if params.schema_ else params.user.upper()

        dsn = None
        if params.service_name:
            dsn = f"{params.host}:{params.port}/{params.service_name}"
        elif params.sid:
            dsn = oracledb.makedsn(params.host, params.port, sid=params.sid)

        self.connection = oracledb.connect(
            user=params.user,
            password=params.password,
            dsn=dsn
        )
        
        # Set current schema if different from user
        if params.schema_:
            with self.connection.cursor() as cursor:
                cursor.execute(f"ALTER SESSION SET CURRENT_SCHEMA = {params.schema_}")

    def _get_fqn(self, identifier: str) -> str:
        if "." in identifier:
            return identifier.upper()  # Oracle identifiers are case-insensitive/upper by default unless quoted
        return f'"{self._schema}"."{identifier}"'

    @staticmethod
    def check_data(data: Any) -> OracleConfig:
        try:
            data = OracleConfig.model_validate(data)
        except Exception:
            raise TypeError("Input must be an Oracle config.")
        return data

    def _execute_sql(self, query: str, params: Optional[list | dict] = None) -> list[Any]:
        # Oracle uses :1, :2 or :name for bind variables.
        # We need to ensure the query format matches what oracledb expects.
        with self.connection.cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if cursor.description:
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                # Convert rows to list of dicts to match other adapters' return format for convenience
                result = []
                for row in rows:
                    result.append(dict(zip(columns, row)))
                return result
            return []

    def _get_pandas_df(self, query: str, params: Optional[list | dict] = None) -> pd.DataFrame:
        # Use simple read_sql
        return pd.read_sql(query, self.connection, params=params)

    def profile(self, data: OracleConfig, table_name: str) -> ProfilingOutput:
        data = self.check_data(data)
        # Assuming identifier is table name
        table_upper = data.identifier.upper()
        
        # Count
        fqn = self._get_fqn(data.identifier)
        count_res = self._execute_sql(f"SELECT COUNT(*) as CNT FROM {fqn}")
        total_count = count_res[0]["CNT"]

        # Columns and Types from Data Dictionary
        # Using ALL_TAB_COLUMNS to see everything accessible
        query = """
        SELECT COLUMN_NAME, DATA_TYPE
        FROM ALL_TAB_COLUMNS
        WHERE OWNER = :owner AND TABLE_NAME = :table_name
        """
        rows = self._execute_sql(query, {"owner": self._schema, "table_name": table_upper})
        
        columns = [row["COLUMN_NAME"] for row in rows]
        dtypes = {row["COLUMN_NAME"]: row["DATA_TYPE"] for row in rows}

        return ProfilingOutput(
            count=total_count,
            columns=columns,
            dtypes=dtypes,
        )

    def column_profile(
        self,
        data: OracleConfig,
        table_name: str,
        column_name: str,
        total_count: int,
        sample_limit: int = 10,
        dtype_sample_limit: int = 10000,
    ) -> Optional[ColumnProfile]:
        data = self.check_data(data)
        fqn = self._get_fqn(data.identifier)
        start_ts = time.time()
        
        # Oracle treats empty strings as NULLs sometimes, but we'll stick to standard SQL
        safe_col = f'"{column_name}"'

        query = f"""
        SELECT
            COUNT(CASE WHEN {safe_col} IS NULL THEN 1 END) as NULL_COUNT,
            COUNT(DISTINCT {safe_col}) as DISTINCT_COUNT
        FROM {fqn}
        """
        result = self._execute_sql(query)[0]
        null_count = result["NULL_COUNT"]
        distinct_count = result["DISTINCT_COUNT"]
        not_null_count = total_count - null_count

        # Sampling
        # SAMPLE() clause in Oracle is approximate. For exact limit, use ROWNUM or FETCH FIRST.
        # Getting distinct non-null values
        sample_query = f"""
        SELECT DISTINCT CAST({safe_col} AS VARCHAR2(4000)) as VAL 
        FROM {fqn} 
        WHERE {safe_col} IS NOT NULL 
        FETCH FIRST {dtype_sample_limit} ROWS ONLY
        """
        distinct_values_result = self._execute_sql(sample_query)
        distinct_values = [row["VAL"] for row in distinct_values_result]

        if distinct_count > 0:
            distinct_sample_size = min(distinct_count, dtype_sample_limit)
            # numpy choice might fail if list is empty
            if distinct_values:
                sample_data = list(np.random.choice(distinct_values, min(len(distinct_values), distinct_sample_size), replace=False))
            else:
                sample_data = []
        else:
            sample_data = []

        dtype_sample = None
        if distinct_count >= dtype_sample_limit:
            dtype_sample = sample_data
        elif distinct_count > 0 and not_null_count > 0:
            remaining_sample_size = dtype_sample_limit - distinct_count
            if remaining_sample_size > 0:
                # Oracle Random Sort -> ORDER BY dbms_random.value
                additional_samples_query = f"""
                SELECT CAST({safe_col} AS VARCHAR2(4000)) as VAL 
                FROM {fqn} 
                WHERE {safe_col} IS NOT NULL 
                ORDER BY dbms_random.value 
                FETCH FIRST {remaining_sample_size} ROWS ONLY
                """
                additional_samples_result = self._execute_sql(additional_samples_query)
                additional_samples = [row["VAL"] for row in additional_samples_result]
                dtype_sample = list(distinct_values) + additional_samples
            else:
                dtype_sample = list(distinct_values)
        else:
            dtype_sample = []

        # Convert to native types
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

    def load(self, data: OracleConfig, table_name: str):
        self.check_data(data)
        # No-op
        pass

    def execute(self, query: str):
        return self._execute_sql(query)

    def to_df(self, data: OracleConfig, table_name: str) -> pd.DataFrame:
        data = self.check_data(data)
        fqn = self._get_fqn(data.identifier)
        return self._get_pandas_df(f"SELECT * FROM {fqn}")

    def to_df_from_query(self, query: str) -> pd.DataFrame:
        return self._get_pandas_df(query)

    def create_table_from_query(
        self, table_name: str, query: str, materialize: str = "view", **kwargs
    ) -> str:
        fqn = self._get_fqn(table_name)
        # Use sqlglot to transpile to Oracle
        transpiled_sql = transpile(query, read=None, write="oracle")[0]
        
        # Clean up existing
        try:
            if materialize == "table":
                try:
                    self._execute_sql(f"DROP TABLE {fqn}")
                except Exception:
                    pass  # Ignore if not exists
                self._execute_sql(f"CREATE TABLE {fqn} AS {transpiled_sql}")
            
            elif materialize == "materialized_view":
                try:
                    self._execute_sql(f"DROP MATERIALIZED VIEW {fqn}")
                except Exception:
                    pass
                self._execute_sql(f"CREATE MATERIALIZED VIEW {fqn} AS {transpiled_sql}")

            else:  # view
                # CREATE OR REPLACE VIEW is supported in Oracle
                self._execute_sql(f"CREATE OR REPLACE VIEW {fqn} AS {transpiled_sql}")
        except Exception as e:
            raise RuntimeError(f"Failed to create {materialize} {fqn}: {e}")

        return transpiled_sql

    def create_new_config_from_etl(self, etl_name: str) -> "DataSetData":
        return OracleConfig(identifier=etl_name)

    def intersect_count(self, table1: "DataSet", column1_name: str, table2: "DataSet", column2_name: str) -> int:
        table1_adapter = self.check_data(table1.data)
        table2_adapter = self.check_data(table2.data)

        fqn1 = self._get_fqn(table1_adapter.identifier)
        fqn2 = self._get_fqn(table2_adapter.identifier)
        
        # Use INTERSECT
        query = f"""
        SELECT COUNT(*) as CNT FROM (
            SELECT DISTINCT "{column1_name}" FROM {fqn1} WHERE "{column1_name}" IS NOT NULL
            INTERSECT
            SELECT DISTINCT "{column2_name}" FROM {fqn2} WHERE "{column2_name}" IS NOT NULL
        )
        """
        return self._execute_sql(query)[0]["CNT"]

    def get_composite_key_uniqueness(self, table_name: str, columns: list[str], dataset_data: DataSetData) -> int:
        data = self.check_data(dataset_data)
        fqn = self._get_fqn(data.identifier)
        safe_columns = [f'"{col}"' for col in columns]
        column_list = ", ".join(safe_columns)
        null_cols_filter = " AND ".join(f"{c} IS NOT NULL" for c in safe_columns)

        query = f"""
        SELECT COUNT(*) as CNT FROM (
            SELECT DISTINCT {column_list} FROM {fqn}
            WHERE {null_cols_filter}
        )
        """
        return self._execute_sql(query)[0]["CNT"]

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

        safe_columns1 = [f'"{col}"' for col in columns1]
        safe_columns2 = [f'"{col}"' for col in columns2]
        
        # Subquery for distinct keys from table 1
        distinct_cols1 = ", ".join(safe_columns1)
        null_filter1 = " AND ".join(f"{c} IS NOT NULL" for c in safe_columns1)
        subquery1 = f'(SELECT DISTINCT {distinct_cols1} FROM {fqn1} WHERE {null_filter1})'

        # Subquery for distinct keys from table 2
        distinct_cols2 = ", ".join(safe_columns2)
        null_filter2 = " AND ".join(f"{c} IS NOT NULL" for c in safe_columns2)
        subquery2 = f'(SELECT DISTINCT {distinct_cols2} FROM {fqn2} WHERE {null_filter2})'

        # Join conditions - confusing in generic SQL without aliasing the subqueries clearly in Oracle
        # Actually standard SQL supports: SELECT COUNT(*) FROM (sub1) t1 INNER JOIN (sub2) t2 ON ...
        
        join_conditions = " AND ".join(
            [f"t1.{c1} = t2.{c2}" for c1, c2 in zip(safe_columns1, safe_columns2)]
        )

        query = f"""
        SELECT COUNT(*) as CNT
        FROM {subquery1} t1
        INNER JOIN {subquery2} t2 ON {join_conditions}
        """
        return self._execute_sql(query)[0]["CNT"]

    def get_details(self, data: OracleConfig):
        data = self.check_data(data)
        return data.model_dump()


def can_handle_oracle(df: Any) -> bool:
    try:
        OracleConfig.model_validate(df)
        return True
    except Exception:
        return False


def register(factory: AdapterFactory):
    if ORACLE_ADAPTER_AVAILABLE:
        factory.register("oracle", can_handle_oracle, OracleAdapter, OracleConfig)
