import time
from typing import Any, Optional

import numpy as np
import pandas as pd

from intugle.adapters.adapter import Adapter
from intugle.adapters.factory import AdapterFactory
from intugle.adapters.models import (
    ColumnProfile,
    ProfilingOutput,
)
from intugle.adapters.types.snowflake.models import SnowflakeConfig, SnowflakeConnectionConfig
from intugle.adapters.utils import convert_to_native
from intugle.core import settings

from snowflake.snowpark import Session
import snowflake.snowpark.functions as F
from snowflake.snowpark.functions import col

from intugle.core.utilities.processing import string_standardization

class SnowflakeAdapter(Adapter):

    def __init__(self):
        connection_parameters = settings.PROFILES.get("etl", {}).get("outputs", {}).get("dev", {})
        self.connection_parameters = SnowflakeConnectionConfig.model_validate(connection_parameters)
        self.session = self.connect()

    def connect(self):
        return Session.builder.configs(self.connection_parameters.model_dump()).create()

    @staticmethod
    def check_data(data: Any) -> SnowflakeConfig:
        try:
            data = SnowflakeConfig.model_validate(data)
        except Exception:
            raise TypeError("Input must be a snowflake config.")
        return data

    def profile(self, data: SnowflakeConfig, table_name: str) -> ProfilingOutput:
        data = self.check_data(data)
        table = self.session.table(data.identifier)
        total_count = table.count()
        columns = table.columns
        dtypes = {field.name: str(field.datatype) for field in table.schema.fields}
        return ProfilingOutput(
            count=total_count,
            columns=columns,
            dtypes=dtypes,
        )

    def column_profile(
        self,
        data: SnowflakeConfig,
        table_name: str,
        column_name: str,
        total_count: int,
        sample_limit: int = 10,
        dtype_sample_limit: int = 10000,
    ) -> Optional[ColumnProfile]:
        data = self.check_data(data)
        table = self.session.table(data.identifier)

        start_ts = time.time()

        # Null count
        null_count = table.filter(F.col(column_name).is_null()).count()
        not_null_count = total_count - null_count

        # Distinct count
        distinct_count = table.select(column_name).distinct().count()

        string_col = col(column_name).cast("string")

        # Sample data
        distinct_values_df = table.select(string_col).distinct().limit(dtype_sample_limit)
        distinct_values = [row[0] for row in distinct_values_df.collect()]

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
            additional_samples_df = table.select(string_col).sample(n=remaining_sample_size)
            additional_samples = [row[0] for row in additional_samples_df.collect()]

            # Combine the full set of unique values with the additional random samples.
            dtype_sample = list(distinct_values) + additional_samples
        else:
            dtype_sample = []

        # --- Convert numpy types to native Python types for JSON compatibility --- #
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
            completeness=(total_count - null_count) / total_count if total_count > 0 else 0.0,
            sample_data=native_sample_data,
            dtype_sample=native_dtype_sample,
            ts=time.time() - start_ts
        )

    def load(self, data: SnowflakeConfig, table_name: str):
        self.check_data(data)
    
    def execute(self, query: str):
        return self.session.sql(query).collect()
    
    def to_df(self, data: SnowflakeConfig, table_name: str):
        data = self.check_data(data)
        df = self.session.table(data.identifier).to_pandas()
        df.columns = [col.strip('"') for col in df.columns]
        return df

    def to_df_from_query(self, query: str) -> pd.DataFrame:
        return self.session.sql(query).to_pandas()

    def create_table_from_query(self, table_name: str, query: str):
        self.session.sql(f"CREATE OR REPLACE TABLE {table_name} AS {query}").collect()

    def intersect_count(self, table1: "DataSet", column1_name: str, table2: "DataSet", column2_name: str) -> int:
        table1_adapter = self.check_data(table1.data)
        table2_adapter = self.check_data(table2.data)
        
        table1_df = self.session.table(table1_adapter.identifier)
        table2_df = self.session.table(table2_adapter.identifier)

        intersect_df = table1_df.select(column1_name).intersect(table2_df.select(column2_name))
        return intersect_df.count()

    def get_details(self, data: SnowflakeConfig):
        data = self.check_data(data)
        return data.model_dump()

def can_handle_snowflake(df: Any) -> bool:
    try:
        SnowflakeAdapter.check_data(df)
    except Exception:
        return False
    return True


def register(factory: AdapterFactory):
    factory.register("snowflake", can_handle_snowflake, SnowflakeAdapter)
