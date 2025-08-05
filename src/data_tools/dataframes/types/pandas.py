
import time

from typing import Any, Optional

import numpy as np
import pandas as pd
import pandas.api.types as ptypes

from data_tools.dataframes.dataframe import DataFrame
from data_tools.dataframes.factory import DataFrameFactory
from data_tools.dataframes.models import AssetColumnProfileResponse, ColumnProfile, ProfilingOutput


class PandasDF(DataFrame):

    def profile(self, df: pd.DataFrame) -> ProfilingOutput:
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
        if not isinstance(df, pd.DataFrame):
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

        total_count = len(df)
        columns = df.columns.tolist()
        dtypes = {
            col: __format_dtype_pandas__(dtype) for col, dtype in df.dtypes.items()
        }

        return ProfilingOutput(
            count=total_count,
            columns=columns,
            dtypes=dtypes,
        )
    
    def column_profile(
        self,
        df: pd.DataFrame, 
        table_name: str,
        column_name: str, 
        sample_limit: int = 200
    ) -> Optional[AssetColumnProfileResponse]:
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
        if column_name not in df.columns:
            print(f"Error: Column '{column_name}' not found in DataFrame.")
            return None

        start_ts = time.time()

        total_count = len(df)
        column_series = df[column_name]

        # --- Calculations --- #
        not_null_series = column_series.dropna()
        not_null_count = len(not_null_series)
        null_count = total_count - not_null_count

        distinct_values = not_null_series.unique()
        distinct_count = len(distinct_values)

        # --- Sampling Logic --- #
        # 1. Get a sample of distinct values.
        if distinct_count > 0:
            distinct_sample_size = min(distinct_count, sample_limit)
            sample_data = list(np.random.choice(distinct_values, distinct_sample_size, replace=False))
        else:
            sample_data = []

        # 2. Create a combined sample for data type analysis.
        dtype_sample = None
        if distinct_count >= sample_limit:
            # If we have enough distinct values, that's the best sample.
            dtype_sample = sample_data
        elif distinct_count > 0 and not_null_count > 0:
            # If distinct values are few, supplement them with random non-distinct values.
            remaining_sample_size = sample_limit - distinct_count

            # Use replace=True in case the number of non-null values is less than the remaining sample size needed.
            additional_samples = list(not_null_series.sample(n=remaining_sample_size, replace=True))

            # Combine the full set of unique values with the additional random samples.
            dtype_sample = list(distinct_values) + additional_samples
        else:
            # No data to sample from.
            dtype_sample = []

        # --- Final Profile --- #
        return AssetColumnProfileResponse(
            name=column_name,
            table_name=table_name,  # Placeholder for table name
            
            profile=ColumnProfile(
                null_count=null_count,
                count=total_count,
                distinct_count=distinct_count,
            ),
            
            sample_data=sample_data,
            dtype_sample=dtype_sample,
            ts=time.time() - start_ts,
        )


def can_handle_pandas(df: Any) -> bool:
    return isinstance(df, pd.DataFrame)


def register(factory: DataFrameFactory):
    factory.register("pandas", can_handle_pandas, PandasDF)
