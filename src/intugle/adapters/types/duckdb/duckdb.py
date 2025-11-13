import time

from typing import TYPE_CHECKING, Any, Optional

import duckdb
import numpy as np
import pandas as pd

from intugle.adapters.adapter import Adapter
from intugle.adapters.factory import AdapterFactory
from intugle.adapters.models import (
    ColumnProfile,
    DataSetData,
    ProfilingOutput,
)
from intugle.adapters.types.duckdb.models import DuckdbConfig
from intugle.adapters.utils import convert_to_native
from intugle.common.exception import errors
from intugle.core import settings
from intugle.core.utilities.processing import string_standardization

if TYPE_CHECKING:
    from intugle.analysis.models import DataSet


def safe_identifier(name: str) -> str:
    """
    Wraps an SQL identifier in double quotes, allowing almost any character except
    double quotes and semicolons (to prevent SQL injection).
    """
    if '"' in name or ';' in name:
        raise ValueError(f"Invalid SQL identifier: {name}")
    return f'"{name}"'


class DuckdbAdapter(Adapter):
    @property
    def database(self) -> Optional[str]:
        return None

    @property
    def schema(self) -> Optional[str]:
        return None
    
    @property
    def source_name(self) -> str:
        return settings.PROFILES.get("duckdb", {}).get("name", "my_local_source")

    def __init__(self):
        duckdb.install_extension('httpfs')
        duckdb.load_extension('httpfs')

    @staticmethod
    def check_data(data: Any) -> DuckdbConfig:
        try:
            data = DuckdbConfig.model_validate(data)
        except Exception:
            raise TypeError("Input must be a DuckdbConfig instance.")
        return data

    def profile(self, data: DuckdbConfig, table_name: str) -> ProfilingOutput:
        """
        Generates a profile of a file.

        Args:
            df: The input pandas DataFrame.

        Returns:
            A pydantic model containing the profile information:
            - "count": Total number of rows.
            - "columns": List of column names.
            - "dtypes": A dictionary mapping column names to generalized data types.
        """
        data = self.check_data(data)
        table_name_safe = safe_identifier(table_name)

        def __format_dtype__(dtype: Any) -> str:
            type_map = {
                "VARCHAR": "string",
                "DATE": "date & time",
                "BIGINT": "integer",
                "DOUBLE": "float",
                "FLOAT": "float",
            }
            return type_map.get(dtype, "string")

        self.load(data, table_name)

        # Fetch total count
        query = f"SELECT COUNT(*) as count FROM {table_name_safe}"
        total_count = duckdb.execute(query).fetchone()[0]

        # Fetch column names and types
        query = "SELECT column_name, data_type FROM duckdb_columns() WHERE table_name = ?"
        column_data = duckdb.execute(query, [table_name]).fetchall()
        dtypes = {col: __format_dtype__(dtype) for col, dtype in column_data}
        columns = [col for col, _ in column_data]

        return ProfilingOutput(
            count=total_count,
            columns=columns,
            dtypes=dtypes,
        )

    def column_profile(
        self,
        data: DuckdbConfig,
        table_name: str,
        column_name: str,
        total_count: int,
        sample_limit: int = 10,
        dtype_sample_limit: int = 10000,
    ) -> Optional[ColumnProfile]:
        """
        Generates a detailed profile for a single column of a table.

        It calculates null and distinct counts, and generates two types of samples:
        1.  `sample_data`: A sample of unique values.
        2.  `dtype_sample`: A potentially larger sample combining unique values with
            random non-unique values, intended for data type analysis.

        Args:
            df: The input pandas DataFrame.
            column_name: The name of the column to profile.
            sample_limit: The desired number of items for the data samples.

        Returns:
            A dictionary containing the profile for the column, or None if the
            column does not exist.
        """
        data = self.check_data(data)
        table_name_safe = safe_identifier(table_name)
        column_name_safe = safe_identifier(column_name)

        self.load(data, table_name)
        start_ts = time.time()

        # --- Nulls and distinct counts ---
        query = f"""
        SELECT 
            COUNT(DISTINCT {column_name_safe}) AS distinct_count,
            SUM(CASE WHEN {column_name_safe} IS NULL THEN 1 ELSE 0 END) AS null_count
        FROM {table_name_safe}
        """
        distinct_null_data = duckdb.execute(query).fetchone()
        distinct_count, null_count = distinct_null_data
        not_null_count = total_count - null_count

        # --- Sampling ---
        sample_query = f"""
        SELECT DISTINCT CAST({column_name_safe} AS VARCHAR) AS sample_values
        FROM {table_name_safe}
        WHERE {column_name_safe} IS NOT NULL
        LIMIT {dtype_sample_limit}
        """
        data_sample = duckdb.execute(sample_query).fetchall()
        distinct_values = [d[0] for d in data_sample]
        not_null_series = pd.Series(distinct_values)

        if distinct_count > 0:
            distinct_sample_size = min(distinct_count, dtype_sample_limit)
            sample_data = list(np.random.choice(distinct_values, distinct_sample_size, replace=False))
        else:
            sample_data = []

        # dtype_sample
        dtype_sample = []
        if distinct_count >= dtype_sample_limit:
            dtype_sample = sample_data
        elif distinct_count > 0 and not_null_count > 0:
            remaining_sample_size = dtype_sample_limit - distinct_count
            additional_samples = list(not_null_series.sample(n=remaining_sample_size, replace=True))
            dtype_sample = list(distinct_values) + additional_samples

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
            uniqueness=distinct_count / total_count if total_count else 0.0,
            completeness=not_null_count / total_count if total_count else 0.0,
            sample_data=native_sample_data[:sample_limit],
            dtype_sample=native_dtype_sample,
            ts=time.time() - start_ts,
        )

    @staticmethod
    def _get_load_func(data: DuckdbConfig):
        func = {"csv": "read_csv", "parquet": "read_parquet", "xlsx": "read_xlsx"}
        ld_func = func.get(data.type)
        if ld_func is None:
            raise errors.NotFoundError(f"Type: {data.type} not supported")

        if data.type == "xlsx":
            return f"{ld_func}('{data.path}', ignore_errors = true)"
        return f"{ld_func}('{data.path}')"

    def load_view(self, data: DuckdbConfig, table_name: str):
        table_name_safe = safe_identifier(table_name)
        query = f"CREATE OR REPLACE VIEW {table_name_safe} AS {data.path}"
        duckdb.execute(query)

    def load_file(self, data: DuckdbConfig, table_name: str):
        table_name_safe = safe_identifier(table_name)
        ld_func = self._get_load_func(data)
        query = f"CREATE VIEW IF NOT EXISTS {table_name_safe} AS SELECT * FROM {ld_func};"
        duckdb.execute(query)

    def load(self, data: DuckdbConfig, table_name: str):
        data = self.check_data(data)
        if data.type == "query":
            self.load_view(data, table_name)
        elif data.type == "table":
            return
        else:
            self.load_file(data, table_name)

    def execute_df(self, query: str) -> pd.DataFrame:
        return duckdb.sql(query).to_df()

    def to_df(self, _: DuckdbConfig, table_name: str) -> pd.DataFrame:
        table_name_safe = safe_identifier(table_name)
        query = f"SELECT * FROM {table_name_safe}"
        return self.execute_df(query)

    def to_df_from_query(self, query: str) -> pd.DataFrame:
        return duckdb.sql(query).to_df()

    def create_table_from_query(
        self, table_name: str, query: str, materialize: str = "view", **kwargs
    ) -> str:
        table_name_safe = safe_identifier(table_name)
        if materialize == "table":
            duckdb.execute(f"CREATE OR REPLACE TABLE {table_name_safe} AS {query}")
        else:
            duckdb.execute(f"CREATE OR REPLACE VIEW {table_name_safe} AS {query}")
        return query

    def create_new_config_from_etl(self, etl_name: str) -> "DataSetData":
        return DuckdbConfig(path=etl_name, type="table")

    def deploy_semantic_model(self, semantic_model_dict: dict, **kwargs):
        raise NotImplementedError("Deployment is not supported for the DuckdbAdapter.")

    def execute(self, query: str):
        df = self.execute_df(query)
        return df.to_dict(orient="records")

    def intersect_count(self, table1: "DataSet", column1_name: str, table2: "DataSet", column2_name: str) -> int:
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
        return result[0]['intersect_count']

    def get_composite_key_uniqueness(self, table_name: str, columns: list[str], dataset_data: DataSetData) -> int:
        table_name_safe = safe_identifier(table_name)
        columns_safe = [safe_identifier(col) for col in columns]
        column_list = ", ".join(columns_safe)
        null_cols_filter = " AND ".join(f"{c} IS NOT NULL" for c in columns_safe)

        query = f"""
        SELECT COUNT(*) as distinct_count FROM (
            SELECT DISTINCT {column_list} FROM {table_name_safe}
            WHERE {null_cols_filter}
        ) as t
        """
        result = self.execute(query)
        return result[0]['distinct_count']

    def intersect_composite_keys_count(
        self,
        table1: "DataSet",
        columns1: list[str],
        table2: "DataSet",
        columns2: list[str],
    ) -> int:
        table1_name_safe = safe_identifier(table1.name)
        table2_name_safe = safe_identifier(table2.name)

        columns1_safe = [safe_identifier(col) for col in columns1]
        columns2_safe = [safe_identifier(col) for col in columns2]

        # Subquery for distinct keys from table 1
        distinct_cols1 = ", ".join(columns1_safe)
        null_filter1 = " AND ".join(f"{c} IS NOT NULL" for c in columns1_safe)
        subquery1 = f"(SELECT DISTINCT {distinct_cols1} FROM {table1_name_safe} WHERE {null_filter1}) AS t1"

        # Subquery for distinct keys from table 2
        distinct_cols2 = ", ".join(columns2_safe)
        null_filter2 = " AND ".join(f"{c} IS NOT NULL" for c in columns2_safe)
        subquery2 = f"(SELECT DISTINCT {distinct_cols2} FROM {table2_name_safe} WHERE {null_filter2}) AS t2"

        # Join conditions
        join_conditions = " AND ".join(
            [f"t1.{c1} = t2.{c2}" for c1, c2 in zip(columns1_safe, columns2_safe)]
        )

        query = f"""
        SELECT COUNT(*) as intersect_count
        FROM {subquery1}
        JOIN {subquery2}
        ON {join_conditions}
        """
        result = self.execute(query)
        return result[0]['intersect_count']

    def get_details(self, data: DuckdbConfig):
        data = self.check_data(data)
        return data.model_dump()


def can_handle_pandas(df: Any) -> bool:
    try:
        DuckdbAdapter.check_data(df)
        return True
    except Exception:
        return False


def register(factory: AdapterFactory):
    factory.register("duckdb", can_handle_pandas, DuckdbAdapter, DuckdbConfig)
