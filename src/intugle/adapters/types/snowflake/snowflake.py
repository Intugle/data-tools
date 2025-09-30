from typing import Any, Optional

from intugle.adapters.adapter import Adapter
from intugle.adapters.factory import AdapterFactory
from intugle.adapters.models import (
    ColumnProfile,
    ProfilingOutput,
)
from intugle.adapters.types.snowflake.models import SnowflakeConfig, SnowflakeConnectionConfig
from intugle.core import settings

from snowflake.snowpark import Session
import snowflake.snowpark.functions as F

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

        # Null count
        null_count = table.filter(F.col(column_name).is_null()).count()

        # Distinct count
        distinct_count = table.select(column_name).distinct().count()

        # Sample data
        sample_data = table.select(column_name).limit(sample_limit).to_pandas()[column_name].tolist()

        return ColumnProfile(
            column_name=column_name,
            table_name=table_name,
            null_count=null_count,
            count=total_count,
            distinct_count=distinct_count,
            uniqueness=distinct_count / total_count if total_count > 0 else 0.0,
            completeness=(total_count - null_count) / total_count if total_count > 0 else 0.0,
            sample_data=sample_data,
        )

    def load(self, data: SnowflakeConfig, table_name: str):
        self.check_data(data)
    
    def execute(self, query: str):
        return self.session.sql(query).collect()
    
    def to_df(self, data: SnowflakeConfig, table_name: str):
        data = self.check_data(data)
        return self.session.table(data.identifier).to_pandas()

    def intersect_count(self, table1: "DataSet", column1_name: str, table2: "DataSet", column2_name: str) -> int:
        table1_df = self.session.table(table1.data.identifier)
        table2_df = self.session.table(table2.data.identifier)

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
