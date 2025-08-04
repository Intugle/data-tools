
from typing import Any

import pandas as pd
import pandas.api.types as ptypes

from data_tools.dataframes.dataframe import DataFrame
from data_tools.dataframes.factory import DataFrameFactory
from data_tools.dataframes.models import ProfilingOutput


class PandasDF(DataFrame):
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def profile(self) -> ProfilingOutput:
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
        if not isinstance(self.df, pd.DataFrame):
            raise TypeError("Input must be a pandas DataFrame.")

        def __format_dtype_pandas__(dtype: Any) -> str:
            """Maps pandas dtype to a generalized type string."""
            if ptypes.is_integer_dtype(dtype):
                return "integer"
            elif ptypes.is_float_dtype(dtype):
                return "float"
            elif ptypes.is_datetime64_any_dtype(dtype) or ptypes.is_period_dtype(dtype):
                return "date & time"
            elif ptypes.is_string_dtype(dtype) or dtype == "object":
                # Fallback to 'object' for mixed types or older pandas versions
                return "string"
            else:
                return "string"  # Default for other types

        self.count = len(self.df)
        self.columns = self.df.columns.tolist()
        self.dtypes = {
            col: __format_dtype_pandas__(dtype) for col, dtype in self.df.dtypes.items()
        }

        return ProfilingOutput(
            count=self.count,
            columns=self.columns,
            dtypes=self.dtypes,
        )


def can_handle_pandas(df: Any) -> bool:
    return isinstance(df, pd.DataFrame)


def register(factory: DataFrameFactory):
    factory.register("pandas", can_handle_pandas, PandasDF)
