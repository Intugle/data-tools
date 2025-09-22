import time
from typing import Any, Optional, TYPE_CHECKING

import numpy as np
import pandas as pd
import pandas.api.types as ptypes

from intugle.adapters.adapter import Adapter
from intugle.adapters.factory import AdapterFactory
from intugle.adapters.models import (
    ColumnProfile,
    ProfilingOutput,
)
from intugle.adapters.utils import convert_to_native
from intugle.core.utilities.processing import string_standardization

if TYPE_CHECKING:
    from intugle.analysis.models import DataSet


class PandasAdapter(Adapter):
    def profile(self, data: pd.DataFrame, _: str) -> ProfilingOutput:
        """
        Generates a profile of a pandas DataFrame.

        Args:
            df: The input pandas DataFrame.

        Returns:
            A pydantic model containing the profile information:
            - "count": Total number of rows.
            - "columns": List of column names.
            - "dtypes": A dictionary mapping column names to generalized data types.
        """
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Input must be a pandas DataFrame.")

        def __format_dtype_pandas__(dtype: Any) -> str:
            """Maps pandas dtype to a generalized type string."""
            if ptypes.is_integer_dtype(dtype):
                return "integer"
            elif ptypes.is_float_dtype(dtype):
                return "float"
            elif ptypes.is_datetime64_any_dtype(dtype) or isinstance(dtype, pd.PeriodDtype):
                return "date & time"
            elif ptypes.is_string_dtype(dtype) or dtype == "object":
                # Fallback to 'object' for mixed types or older pandas versions
                return "string"
            else:
                return "string"  # Default for other types

        total_count = len(data)
        data.columns = data.columns.astype(str)

        columns = data.columns.tolist()
        dtypes = {col: __format_dtype_pandas__(dtype) for col, dtype in data.dtypes.items()}

        return ProfilingOutput(
            count=total_count,
            columns=columns,
            dtypes=dtypes,
        )

    def column_profile(
        self,
        data: pd.DataFrame,
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
        if column_name not in data.columns:
            print(f"Error: Column '{column_name}' not found in DataFrame.")
            return None

        start_ts = time.time()

        column_series = data[column_name]

        # --- Calculations --- #
        not_null_series = column_series.dropna()
        not_null_count = len(not_null_series)
        null_count = total_count - not_null_count

        distinct_values = not_null_series.unique()
        distinct_count = len(distinct_values)

        # --- Sampling Logic --- #
        # 1. Get a sample of distinct values.
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
    
    def load(self, data: pd.DataFrame, table_name: str):
        ...
        # duckdb.sql(f"CREATE TABLE {table_name} AS SELECT * FROM data")
    
    def execute(self, query: str):
        raise NotImplementedError("Execute is not supported for PandasAdapter yet.")
    
    def to_df(self, data):
        return data

    def intersect_count(self, table1: "DataSet", column1_name: str, table2: "DataSet", column2_name: str) -> int:
        df1 = table1.data
        df2 = table2.data
        
        if not isinstance(df1, pd.DataFrame) or not isinstance(df2, pd.DataFrame):
            raise TypeError("Data for intersect_count must be pandas DataFrames for PandasAdapter.")

        col1_unique = df1[column1_name].dropna().unique()
        col2_unique = df2[column2_name].dropna().unique()

        # Using numpy's intersect1d for performance with large arrays
        intersection = np.intersect1d(col1_unique, col2_unique, assume_unique=True)
        
        return len(intersection)


def can_handle_pandas(data: Any) -> bool:
    return isinstance(data, pd.DataFrame)


def register(factory: AdapterFactory):
    factory.register("pandas", can_handle_pandas, PandasAdapter)
