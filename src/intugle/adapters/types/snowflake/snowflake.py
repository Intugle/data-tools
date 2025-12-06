import re
import time

from typing import TYPE_CHECKING, Any, Optional

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from intugle.analysis.models import DataSet
    from intugle.models.manifest import Manifest

from intugle.adapters.adapter import Adapter
from intugle.adapters.factory import AdapterFactory
from intugle.adapters.models import (
    ColumnProfile,
    DataSetData,
    ProfilingOutput,
)
from intugle.adapters.types.snowflake.models import SnowflakeConfig, SnowflakeConnectionConfig
from intugle.adapters.utils import convert_to_native
from intugle.core import settings
from intugle.exporters.snowflake import clean_name, quote_identifier

try:
    import snowflake.snowpark.functions as F

    from snowflake.snowpark import Session
    from snowflake.snowpark.context import get_active_session
    from snowflake.snowpark.functions import col

    SNOWFLAKE_AVAILABLE = True
except ImportError:
    SNOWFLAKE_AVAILABLE = False

from intugle.core.utilities.processing import string_standardization


class SnowflakeAdapter(Adapter):
    _instance = None
    _initialized = False

    @property
    def source_name(self) -> str:
        return self._source_name

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

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        if not SNOWFLAKE_AVAILABLE:
            raise ImportError("Snowflake dependencies are not installed. Please run 'pip install intugle[snowflake]'.")

        self.session: "Session" = None
        self._database: Optional[str] = None
        self._schema: Optional[str] = None
        self._source_name: str = settings.PROFILES.get("snowflake", {}).get("name", "my_snowflake_source")
        self.connect()
        self._initialized = True

    def connect(self):
        try:
            self.session = get_active_session()
            print("Found active Snowpark session. Using it for connection.")
            # Get current DB and schema from the active session, stripping quotes
            self._database = self.session.get_current_database().strip('"')
            self._schema = self.session.get_current_schema().strip('"')
        except Exception:
            print("No active Snowpark session found. Creating a new session from profiles.yml.")
            connection_parameters_dict = settings.PROFILES.get("snowflake", {})
            if not connection_parameters_dict:
                raise ValueError(
                    "Could not create Snowflake session. No active session found and no connection details in profiles.yml."
                )

            connection_parameters = SnowflakeConnectionConfig.model_validate(connection_parameters_dict)
            self.session = Session.builder.configs(connection_parameters.model_dump(by_alias=True)).create()
            self._database = connection_parameters.database
            self._schema = connection_parameters.schema_

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
            sample_data=native_sample_data[:sample_limit],
            dtype_sample=native_dtype_sample,
            ts=time.time() - start_ts,
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

    def create_table_from_query(
        self, table_name: str, query: str, materialize: str = "view", **kwargs
    ) -> str:
        def _clean_column_quotes(sql: str) -> str:
            # This regex finds ""..."" and replaces with "..."
            return re.sub(r'""(.*?)""', r'"\1"', sql)

        query = _clean_column_quotes(query)
        if materialize == "table":
            self.session.sql(
                f"CREATE OR REPLACE TABLE {table_name} AS {query}"
            ).collect()
        else:
            self.session.sql(
                f"CREATE OR REPLACE VIEW {table_name} AS {query}"
            ).collect()
        return query

    def create_new_config_from_etl(self, etl_name: str) -> "DataSetData":
        return SnowflakeConfig(identifier=etl_name)

    def _sync_metadata(self, manifest: "Manifest"):
        """
        Syncs metadata (comments and tags) from the manifest to the physical Snowflake tables.
        """
        print("Syncing metadata to Snowflake tables...")

        database = self._database
        schema = self._schema

        if not database or not schema:
            raise ValueError("Database and schema must be defined in your profiles.yml for deployment.")

        # all_tags = set()

        # # First, collect all unique tags from all sources
        # for source in manifest.sources.values():
        #     for column in source.table.columns:
        #         if column.tags:
        #             all_tags.update(column.tags)

        # Ensure all tags exist in Snowflake
        # for tag_name in all_tags:
        #     self.session.sql(f"CREATE TAG IF NOT EXISTS {tag_name}").collect()

        # Apply comments and tags to tables and columns
        for source in manifest.sources.values():
            # Construct the fully qualified table name using details from profiles.yml
            full_table_name = f"{database}.{schema}.{source.table.name}"

            # Set table comment
            if source.table.description:
                table_comment = source.table.description.replace("'", "''")
                self.session.sql(f"ALTER TABLE {full_table_name} SET COMMENT = '{table_comment}'").collect()

            # Set column comments and tags
            for column in source.table.columns:
                comment = (column.description or "").replace("'", "''")

                # Set column comment
                self.session.sql(
                    f"ALTER TABLE {full_table_name} MODIFY COLUMN {quote_identifier(column.name)} COMMENT '{comment}'"
                ).collect()

                # Set column tags
                # if column.tags:
                #     tag_assignments = ", ".join([f"{tag} = 'true'" for tag in column.tags])
                #     self.session.sql(f"ALTER TABLE {full_table_name} MODIFY COLUMN \"{column.name}\" SET TAG {tag_assignments}").collect()

        print("Metadata sync complete.")

    def deploy_semantic_model(self, manifest: "Manifest", **kwargs):
        """
        Constructs and executes a CREATE SEMANTIC VIEW statement based on the manifest.

        Args:
            manifest (Manifest): The project manifest containing all sources and relationships.
            **kwargs:
                model_name (str, optional): A custom name for the semantic model view.
        """
        # Step 1: Sync metadata to the physical tables first
        self._sync_metadata(manifest)

        # Step 2: Manually build the CREATE SEMANTIC VIEW SQL statement
        model_name = kwargs.get("model_name", "intugle_semantic_view")

        database = self._database
        schema = self._schema

        # -- TABLES clause --
        table_clauses = []
        for source in manifest.sources.values():
            table_alias = clean_name(source.table.name)
            full_table_name = f"{database}.{schema}.{source.table.name}"

            clause = f"{table_alias} AS {full_table_name}"
            if source.table.key:
                clause += ' PRIMARY KEY ("' + '", "'.join(source.table.key.columns) + '")'
            if source.table.description:
                comment = source.table.description.replace("'", "''")
                clause += f" COMMENT = '{comment}'"
            table_clauses.append(clause)

        # -- RELATIONSHIPS clause --
        relationship_clauses = []
        for rel in manifest.relationships.values():

            # The table with the FK is the "referencing" table
            table_alias = rel.target.table
            column = '"' + '", "'.join(rel.target.columns) + '"'
            # The table with the PK is the "referenced" table
            ref_table_alias = rel.source.table
            ref_column = '"' + '", "'.join(rel.source.columns) + '"'

            clause = f"{clean_name(rel.name)} AS {table_alias}({column}) REFERENCES {ref_table_alias}({ref_column})"
            relationship_clauses.append(clause)

        # -- FACTS and DIMENSIONS clauses --
        fact_clauses = []
        dimension_clauses = []
        for source in manifest.sources.values():
            table_alias = clean_name(source.table.name)
            for column in source.table.columns:
                col_alias = clean_name(column.name)
                expr = f"{table_alias}.{col_alias} AS {quote_identifier(column.name)}"
                if column.description:
                    comment = column.description.replace("'", "''")
                    expr += f" COMMENT = '{comment}'"

                if column.category == "measure":
                    fact_clauses.append(expr)
                else:  # Default to dimension
                    dimension_clauses.append(expr)

        # -- Assemble the final SQL statement --
        sql = f"CREATE OR REPLACE SEMANTIC VIEW {model_name}\n"
        sql += f"  TABLES ({', '.join(table_clauses)})\n"
        if relationship_clauses:
            sql += f"  RELATIONSHIPS ({', '.join(relationship_clauses)})\n"
        if fact_clauses:
            sql += f"  FACTS ({', '.join(fact_clauses)})\n"
        if dimension_clauses:
            sql += f"  DIMENSIONS ({', '.join(dimension_clauses)})\n"
        sql += "  COMMENT = 'Semantic view generated by Intugle'"

        print(f"Deploying semantic model view '{model_name}' to Snowflake...")
        self.session.sql(sql).collect()
        print(f"Semantic model view '{model_name}' deployed successfully.")

    def intersect_count(self, table1: "DataSet", column1_name: str, table2: "DataSet", column2_name: str) -> int:
        table1_adapter = self.check_data(table1.data)
        table2_adapter = self.check_data(table2.data)

        table1_df = self.session.table(table1_adapter.identifier)
        table2_df = self.session.table(table2_adapter.identifier)

        intersect_df = table1_df.select(column1_name).intersect(table2_df.select(column2_name))
        return intersect_df.count()

    def get_composite_key_uniqueness(self, table_name: str, columns: list[str], dataset_data: DataSetData) -> int:
        data = self.check_data(dataset_data)
        table = self.session.table(data.identifier)
        
        # Drop rows where any of the key columns have null values and count distinct
        distinct_count = table.dropna(subset=columns).select(columns).distinct().count()
        return distinct_count

    def intersect_composite_keys_count(
        self,
        table1: "DataSet",
        columns1: list[str],
        table2: "DataSet",
        columns2: list[str],
    ) -> int:
        table1_adapter = self.check_data(table1.data)
        table2_adapter = self.check_data(table2.data)

        df1 = self.session.table(table1_adapter.identifier)
        df2 = self.session.table(table2_adapter.identifier)

        # Get unique combinations of composite keys, dropping nulls
        df1_unique_keys = df1.dropna(subset=columns1).select(columns1).distinct()
        df2_unique_keys = df2.dropna(subset=columns2).select(columns2).distinct()

        # Create join condition
        join_expr = df1_unique_keys[columns1[0]] == df2_unique_keys[columns2[0]]
        for i in range(1, len(columns1)):
            join_expr = join_expr & (df1_unique_keys[columns1[i]] == df2_unique_keys[columns2[i]])

        # Perform the join and count the results
        intersect_count = df1_unique_keys.join(df2_unique_keys, join_expr).count()
        return intersect_count

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
    if SNOWFLAKE_AVAILABLE:
        factory.register("snowflake", can_handle_snowflake, SnowflakeAdapter, SnowflakeConfig)
