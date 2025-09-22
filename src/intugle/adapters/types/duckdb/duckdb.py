import time

from typing import Any, Optional

import duckdb
import numpy as np
import pandas as pd

from intugle.adapters.adapter import Adapter
from intugle.adapters.factory import AdapterFactory
from intugle.adapters.models import (
    ColumnProfile,
    ProfilingOutput,
)
from intugle.adapters.types.duckdb.models import DuckdbConfig
from intugle.adapters.utils import convert_to_native
from intugle.common.exception import errors
from intugle.core.utilities.processing import string_standardization


class DuckdbAdapter(Adapter):

    def __init__(self):
        duckdb.install_extension('httpfs')
        duckdb.load_extension('httpfs')        

    @staticmethod
    def check_data(data: Any) -> DuckdbConfig:
        try:
            data = DuckdbConfig.model_validate(data)
        except Exception:
            raise TypeError("Input must be a duckdb config.")
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

        def __format_dtype__(dtype: Any) -> str:
            """Maps dtype to a generalized type string."""
            type_map = {
                "VARCHAR": "string",
                "DATE": "date & time",
                "BIGINT": "integer",
                "DOUBLE": "float",
                "FLOAT": "float",
            }
            return type_map.get(dtype, "string")

        self.load(data, table_name)

        # Fetching total count of table
        query = f"""
        SELECT count(*) as count FROM "{table_name}"
        """
        data = duckdb.execute(query).fetchall()

        total_count = data[0][0]

        # Fetching column name and their data types of table
        query = """
        SELECT column_name, data_type
        FROM duckdb_columns()
        WHERE table_name = ?
        """
        data = duckdb.execute(query, [table_name]).fetchall()

        dtypes = {col: __format_dtype__(dtype) for col, dtype in data}
        columns = [col for col, _ in data]

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
        Generates a detailed profile for a single column of a pandas DataFrame.

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

        self.load(data, table_name)

        start_ts = time.time()

        # --- Calculations --- #
        query = f"""
        SELECT 
            COUNT(DISTINCT "{column_name}") AS distinct_count,
            SUM(CASE WHEN "{column_name}" IS NULL THEN 1 ELSE 0 END) AS null_count
        FROM  
            "{table_name}"
        """
        distinct_null_data = duckdb.execute(query).fetchall()

        distinct_count, null_count = distinct_null_data[0]
        not_null_count = total_count - null_count

        # --- Sampling Logic --- #
        # 1. Get a sample of distinct values.
        sample_query = f"""
        SELECT 
            DISTINCT CAST( "{column_name}" AS VARCHAR) AS sample_values 
        FROM 
            "{table_name}"
        WHERE 
            "{column_name}" IS NOT NULL LIMIT {dtype_sample_limit}
        """
        data = duckdb.execute(sample_query).fetchall()
        distinct_values = [d[0] for d in data]

        not_null_series = pd.Series(distinct_values)

        if distinct_count > 0:
            distinct_sample_size = min(distinct_count, dtype_sample_limit)
            sample_data = list(np.random.choice(distinct_values, distinct_sample_size, replace=False))
        else:
            sample_data = []

        # 2. Create a combined sample for data type analysis.
        dtype_sample = None
        if distinct_count >= dtype_sample_limit:
            # If we have enough distinct values, that's the best sample.
            dtype_sample = sample_data
        elif distinct_count > 0 and not_null_count > 0:
            # If distinct values are few, supplement them with random non-distinct values.
            remaining_sample_size = dtype_sample_limit - distinct_count

            # Use replace=True in case the number of non-null values is less than the remaining sample size needed.
            additional_samples = list(not_null_series.sample(n=remaining_sample_size, replace=True))

            # Combine the full set of unique values with the additional random samples.
            dtype_sample = list(distinct_values) + additional_samples
        else:
            dtype_sample = []

        # --- Convert numpy types to native Python types for JSON compatibility --- #
        native_sample_data = convert_to_native(sample_data)
        native_dtype_sample = convert_to_native(dtype_sample)

        business_name = string_standardization(column_name)

        # --- Final Profile --- #
        return ColumnProfile(
            column_name=column_name,
            business_name=business_name,
            table_name=table_name,
            null_count=null_count,
            count=total_count,
            distinct_count=distinct_count,
            uniqueness=distinct_count / total_count if total_count > 0 else 0.0,
            completeness=not_null_count / total_count if total_count > 0 else 0.0,
            sample_data=native_sample_data[:sample_limit],
            dtype_sample=native_dtype_sample,
            ts=time.time() - start_ts,
        )

    @staticmethod
    def _get_load_func(data: DuckdbConfig):
        func = {
            "csv": "read_csv",
            "parquet": "read_parquet",
            "xlsx": "read_xlsx",
        }
        ld_func = func.get(data.type)
        if ld_func is None:
            raise errors.NotFoundError(f"Type: {data.type} not supported")

        if data.type == "xlsx":
            return f"{ld_func}('{data.path}', ignore_errors = true)"  # Replace cells that can't be cast to the corresponding inferred column type with NULL

        return f"{ld_func}('{data.path}')"

    def load_view(self, data: DuckdbConfig, table_name: str):
        query = f"""CREATE OR REPLACE VIEW "{table_name}" AS {data.path}"""
        duckdb.execute(query)

    def load_file(self, data: DuckdbConfig, table_name: str):
        ld_func = self._get_load_func(data)
        query = f"""CREATE VIEW IF NOT EXISTS "{table_name}" AS SELECT * FROM {ld_func};"""

        duckdb.execute(query)

    def load(self, data: DuckdbConfig, table_name: str):
        data = self.check_data(data)
        if data.type == "query":
            self.load_view(data, table_name)
            return
        self.load_file(data, table_name)
    
    def execute_df(self, query):
        df = duckdb.sql(query).to_df()
        return df

    def to_df(self, _: DuckdbConfig, table_name: str):
        query = f'''SELECT * from "{table_name}"'''
        df = self.execute_df(query)
        return df

    def execute(self, query):
        df = self.execute_df(query)
        data = df.to_dict(orient="records")
        return data

    async def aexecute(self, query):
        result = duckdb.sql(query).fetchnumpy()
        df = pd.DataFrame(result)
        data = df.to_dict(orient="records")
        return data

    def intersect_count(self, table1: "DataSet", column1_name: str, table2: "DataSet", column2_name: str) -> int:
        table1_name = table1.name
        table2_name = table2.name
        query = f"""
        SELECT COUNT(*) as intersect_count FROM (
            SELECT DISTINCT "{column1_name}" FROM "{table1_name}" WHERE "{column1_name}" IS NOT NULL
            INTERSECT
            SELECT DISTINCT "{column2_name}" FROM "{table2_name}" WHERE "{column2_name}" IS NOT NULL
        ) as t
        """
        result = self.execute(query)
        return result[0]['intersect_count']

    def get_details(self, data: DuckdbConfig):
        data = self.check_data(data)
        return data.model_dump()


def can_handle_pandas(df: Any) -> bool:
    try:
        df = DuckdbAdapter.check_data(df)
    except Exception:
        return False
    return True


def register(factory: AdapterFactory):
    factory.register("duckdb", can_handle_pandas, DuckdbAdapter)
