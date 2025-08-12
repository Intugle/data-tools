import time

from typing import Any, Optional

import numpy as np
import pandas as pd
import pandas.api.types as ptypes

from data_tools.core.pipeline.business_glossary.bg import BusinessGlossary
from data_tools.core.pipeline.datatype_identification.l2_model import L2Model
from data_tools.core.pipeline.datatype_identification.pipeline import DataTypeIdentificationPipeline
from data_tools.core.pipeline.key_identification.ki import KeyIdentificationLLM
from data_tools.core.utilities.processing import string_standardization
from data_tools.dataframes.dataframe import DataFrame
from data_tools.dataframes.factory import DataFrameFactory
from data_tools.dataframes.models import (
    BusinessGlossaryOutput,
    ColumnGlossary,
    ColumnProfile,
    DataTypeIdentificationL1Output,
    DataTypeIdentificationL2Input,
    DataTypeIdentificationL2Output,
    KeyIdentificationOutput,
    ProfilingOutput,
)

from .utils import convert_to_native


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
        dtypes = {col: __format_dtype_pandas__(dtype) for col, dtype in df.dtypes.items()}

        return ProfilingOutput(
            count=total_count,
            columns=columns,
            dtypes=dtypes,
        )

    def column_profile(
        self, df: pd.DataFrame, table_name: str, column_name: str, sample_limit: int = 200
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
            sample_data=native_sample_data,
            dtype_sample=native_dtype_sample,
            ts=time.time() - start_ts,
        )

    def datatype_identification_l1(
        self,
        df: pd.DataFrame,
        table_name: str,
        column_stats: dict[str, ColumnProfile],
    ) -> list[DataTypeIdentificationL1Output]:
        """
        Performs a Level 1 data type identification based on the column's profile.

        This initial step uses the `dtype_sample` collected during the column
        profiling to infer the most likely data type for the column.
        Args:
            df: The input pandas DataFrame.
            table_name: The name of the table the column belongs to.
            column_name: The name of the column to analyze.
            column_stats: The pre-computed statistics for the column from the
                          `column_profile` method.

        Returns:
            A DataTypeIdentificationL1Output model containing the inferred data type.
        """
        records = []
        for column_name, stats in column_stats.items():
            records.append({"table_name": table_name, "column_name": column_name, "values": stats.dtype_sample})

        l1_df = pd.DataFrame(records)
        di_pipeline = DataTypeIdentificationPipeline()
        l1_result = di_pipeline(sample_values_df=l1_df)
        output = [DataTypeIdentificationL1Output(**row) for row in l1_result.to_dict(orient="records")]

        return output

    def datatype_identification_l2(
        self,
        df: Any,
        table_name: str,
        column_stats: list[DataTypeIdentificationL2Input],
    ) -> list[DataTypeIdentificationL1Output]:
        """
        Performs a Level 2 data type identification based on the column profiling.

        Args:
            df: The input pandas DataFrame.
            table_name: The name of the table the column belongs to.
            column_stats: The list of columns, sample data  (DataTypeIdentificationL2Input).

        Returns:
            A DataTypeIdentificationL2Output model containing the inferred data type l2.
        """
        column_values_df = pd.DataFrame([item.model_dump() for item in column_stats])
        l2_model = L2Model()
        l2_result = l2_model(l1_pred=column_values_df)
        output = [DataTypeIdentificationL2Output(**row) for row in l2_result.to_dict(orient="records")]

        return output

    def key_identification(
        self,
        table_name: str,
        column_stats_df: pd.DataFrame,
    ) -> KeyIdentificationOutput:
        """
        Identifies potential primary keys in the DataFrame based on column profiles.

        Args:
            df: The input pandas DataFrame.
            table_name: The name of the table the column belongs to.
            column_stats_df: The pre-computed statistics for the columns from the
                          `column_profile` method.

        Returns:
            A KeyIdentificationOutput model containing the identified primary key column.
        """
        # Placeholder implementation, actual logic would depend on specific criteria for key identification
        ki_model = KeyIdentificationLLM(profiling_data=column_stats_df)
        ki_result = ki_model()
        output = KeyIdentificationOutput(**ki_result)
        return output

    def generate_business_glossary(
        self,
        table_name: str,
        column_stats: pd.DataFrame,
        domain: Optional[str] = None,
    ) -> BusinessGlossaryOutput:
        """
        Generates business glossary terms and tags for columns in a pandas DataFrame.

        Args:
            df: The input pandas DataFrame.
            table_name: The name of the table the column belongs to.

        Returns:
            A BusinessGlossaryOutput model containing glossary terms and tags for each column.
        """

        bg_model = BusinessGlossary(profiling_data=column_stats)
        table_glossary, glossary_df = bg_model(table_name=table_name, domain=domain)
        columns_glossary = []
        for _, row in glossary_df.iterrows():
            columns_glossary.append(
                ColumnGlossary(
                    column_name=row["column_name"],
                    business_glossary=row.get("business_glossary", ""),
                    business_tags=row.get("business_tags", []),
                )
            )
        return BusinessGlossaryOutput(table_name=table_name, table_glossary=table_glossary, columns=columns_glossary)


def can_handle_pandas(df: Any) -> bool:
    return isinstance(df, pd.DataFrame)


def register(factory: DataFrameFactory):
    factory.register("pandas", can_handle_pandas, PandasDF)
