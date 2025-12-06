import re
import time

from typing import TYPE_CHECKING, Any, Optional

import numpy as np
import pandas as pd

from intugle.adapters.adapter import Adapter
from intugle.adapters.common.relationships import clean_name
from intugle.adapters.factory import AdapterFactory
from intugle.adapters.models import ColumnProfile, DataSetData, ProfilingOutput
from intugle.adapters.types.databricks.models import (
    DatabricksConfig,
    DatabricksNotebookConfig,
    DatabricksSQLConnectorConfig,
)
from intugle.adapters.utils import convert_to_native
from intugle.core import settings
from intugle.core.utilities.processing import string_standardization

if TYPE_CHECKING:
    from intugle.analysis.models import DataSet
    from intugle.models.manifest import Manifest

try:
    from pyspark.sql import SparkSession
    PYSPARK_AVAILABLE = True
except ImportError:
    PYSPARK_AVAILABLE = False

try:
    from databricks import sql
    DATABRICKS_SQL_AVAILABLE = True
except ImportError:
    DATABRICKS_SQL_AVAILABLE = False

try:
    from sqlglot import transpile
    SQLGLOT_AVAILABLE = True
except ImportError:
    SQLGLOT_AVAILABLE = False


DATABRICKS_AVAILABLE = PYSPARK_AVAILABLE and DATABRICKS_SQL_AVAILABLE and SQLGLOT_AVAILABLE


def clean_tag(name: str) -> str:
    """Cleans a string to be a valid Databricks tag name."""
    return re.sub(r'[^a-zA-Z0-9_ ]', '_', name)


class DatabricksAdapter(Adapter):
    _instance = None
    _initialized = False

    @property
    def database(self) -> Optional[str]:
        return self.catalog
    
    @database.setter
    def database(self, value: str):
        self.catalog = value

    @property
    def schema(self) -> Optional[str]:
        return self._schema
    
    @schema.setter
    def schema(self, value: str):
        self._schema = value
    
    @property
    def source_name(self) -> str:
        return self._source_name
    
    @source_name.setter
    def source_name(self, value: str):
        self._source_name = value

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        if not DATABRICKS_AVAILABLE:
            raise ImportError(
                "Databricks dependencies are not installed. Please run 'pip install intugle[databricks]'.."
            )

        self.spark: Optional["SparkSession"] = None
        self.connection: Optional[Any] = None
        self.catalog: Optional[str] = None
        self._schema: Optional[str] = None
        self._source_name: str = settings.PROFILES.get("databricks", {}).get("name", "my_databricks_source")
        self.connect()
        self._initialized = True

    def connect(self):
        connection_parameters_dict = settings.PROFILES.get("databricks", {})
        if not connection_parameters_dict:
            raise ValueError(
                "Could not create Databricks connection. No 'databricks' section found in profiles.yml."
            )

        # Try to get an active Spark session (for notebook environment)
        if PYSPARK_AVAILABLE:
            try:
                self.spark = SparkSession.getActiveSession()
                if self.spark:
                    print("Found active Spark session. Using it for execution.")
                    params = DatabricksNotebookConfig.model_validate(connection_parameters_dict)
                    self.catalog = params.catalog
                    self._schema = params.schema_
                    return
            except (AttributeError, TypeError):
                self.spark = None

        # If no active Spark session, create a SQL connector connection (for external environment)
        if not self.spark:
            if not DATABRICKS_SQL_AVAILABLE:
                raise ImportError(
                    "databricks-sql-connector is not installed. Please run 'pip install intugle[databricks]' to connect from outside a Databricks notebook."
                )
            print("No active Spark session found. Creating a new SQL connector connection.")
            params = DatabricksSQLConnectorConfig.model_validate(connection_parameters_dict)
            self.catalog = params.catalog
            self._schema = params.schema_
            self.connection = sql.connect(
                server_hostname=params.host, http_path=params.http_path, access_token=params.token
            )

    def _get_fqn(self, identifier: str) -> str:
        """Gets the fully qualified name for a table identifier."""
        # An identifier is already fully qualified if it contains a dot.
        if "." in identifier:
            return identifier
        
        # Backticks are used to handle reserved keywords and special characters.
        safe_schema = f"`{self._schema}`"
        safe_identifier = f"`{identifier}`"

        if self.catalog:
            safe_catalog = f"`{self.catalog}`"
            return f"{safe_catalog}.{safe_schema}.{safe_identifier}"
        
        return f"{safe_schema}.{safe_identifier}"

    @staticmethod
    def check_data(data: Any) -> DatabricksConfig:
        try:
            data = DatabricksConfig.model_validate(data)
        except Exception:
            raise TypeError("Input must be a Databricks config.")
        return data

    def _execute_sql(self, query: str) -> list[Any]:
        if self.spark:
            if self.catalog:
                self.spark.sql(f"USE CATALOG `{self.catalog}`")
            if self._schema:
                self.spark.sql(f"USE `{self._schema}`")
            return self.spark.sql(query).collect()
        elif self.connection:
            with self.connection.cursor() as cursor:
                if self.catalog:
                    cursor.execute(f"USE CATALOG `{self.catalog}`")
                if self._schema:
                    cursor.execute(f"USE `{self._schema}`")
                cursor.execute(query)
                try:
                    return cursor.fetchall()
                except Exception:
                    return []
        raise ConnectionError("No active Databricks connection.")

    def _get_pandas_df(self, query: str) -> pd.DataFrame:
        if self.spark:
            if self.catalog:
                self.spark.sql(f"USE CATALOG `{self.catalog}`")
            if self._schema:
                self.spark.sql(f"USE `{self._schema}`")
            return self.spark.sql(query).toPandas()
        elif self.connection:
            with self.connection.cursor() as cursor:
                if self.catalog:
                    cursor.execute(f"USE CATALOG `{self.catalog}`")
                if self._schema:
                    cursor.execute(f"USE `{self._schema}`")
                cursor.execute(query)
                data = cursor.fetchall()
                columns = [column[0] for column in cursor.description]
                return pd.DataFrame(data, columns=columns)
        raise ConnectionError("No active Databricks connection.")

    def profile(self, data: DatabricksConfig, table_name: str) -> ProfilingOutput:
        data = self.check_data(data)
        fqn = self._get_fqn(data.identifier)
        if self.spark:
            table = self.spark.table(fqn)
            total_count = table.count()
            columns = table.columns
            dtypes = {field.name: str(field.dataType) for field in table.schema.fields}
        else:
            rows = self._execute_sql(f"DESCRIBE TABLE {fqn}")
            columns = [row.col_name for row in rows]
            dtypes = {row.col_name: row.data_type for row in rows}
            total_count = self._execute_sql(f"SELECT COUNT(*) FROM {fqn}")[0][0]

        return ProfilingOutput(
            count=total_count,
            columns=columns,
            dtypes=dtypes,
        )

    def column_profile(
        self,
        data: DatabricksConfig,
        table_name: str,
        column_name: str,
        total_count: int,
        sample_limit: int = 10,
        dtype_sample_limit: int = 10000,
    ) -> Optional[ColumnProfile]:
        data = self.check_data(data)
        fqn = self._get_fqn(data.identifier)
        start_ts = time.time()

        # Null and distinct counts
        query = f"""
        SELECT
            COUNT(CASE WHEN `{column_name}` IS NULL THEN 1 END) as null_count,
            COUNT(DISTINCT `{column_name}`) as distinct_count
        FROM {fqn}
        """
        result = self._execute_sql(query)[0]
        null_count = result.null_count
        distinct_count = result.distinct_count
        not_null_count = total_count - null_count

        # Sampling
        sample_query = f"""
        SELECT DISTINCT CAST(`{column_name}` AS STRING) FROM {fqn} WHERE `{column_name}` IS NOT NULL LIMIT {dtype_sample_limit}
        """
        distinct_values_result = self._execute_sql(sample_query)
        distinct_values = [row[0] for row in distinct_values_result]

        if distinct_count > 0:
            distinct_sample_size = min(distinct_count, dtype_sample_limit)
            sample_data = list(np.random.choice(distinct_values, distinct_sample_size, replace=False))
        else:
            sample_data = []

        dtype_sample = None
        if distinct_count >= dtype_sample_limit:
            dtype_sample = sample_data
        elif distinct_count > 0 and not_null_count > 0:
            remaining_sample_size = dtype_sample_limit - distinct_count
            additional_samples_query = f"""
            SELECT CAST(`{column_name}` AS STRING) FROM {fqn} WHERE `{column_name}` IS NOT NULL ORDER BY RAND() LIMIT {remaining_sample_size}
            """
            additional_samples_result = self._execute_sql(additional_samples_query)
            additional_samples = [row[0] for row in additional_samples_result]
            dtype_sample = list(distinct_values) + additional_samples
        else:
            dtype_sample = []

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

    def load(self, data: DatabricksConfig, table_name: str):
        self.check_data(data)
        # No-op, we assume the table already exists in Databricks.

    def execute(self, query: str):
        return self._execute_sql(query)

    def to_df(self, data: DatabricksConfig, table_name: str) -> pd.DataFrame:
        data = self.check_data(data)
        fqn = self._get_fqn(data.identifier)
        return self._get_pandas_df(f"SELECT * FROM {fqn}")

    def to_df_from_query(self, query: str) -> pd.DataFrame:
        return self._get_pandas_df(query)

    def create_table_from_query(
        self, table_name: str, query: str, materialize: str = "view", **kwargs
    ) -> str:
        fqn = self._get_fqn(table_name)
        transpiled_sql = transpile(query, write="databricks")[0]
        if materialize == "table":
            self._execute_sql(
                f"CREATE OR REPLACE TABLE {fqn} AS {transpiled_sql}"
            )
        else:
            self._execute_sql(f"CREATE OR REPLACE VIEW {fqn} AS {transpiled_sql}")
        return transpiled_sql

    def create_new_config_from_etl(self, etl_name: str) -> "DataSetData":
        fqn = self._get_fqn(etl_name)
        return DatabricksConfig(identifier=fqn)

    def deploy_semantic_model(
        self,
        manifest: "Manifest",
        sync_glossary: bool = True,
        sync_tags: bool = False,
        set_primary_keys: bool = True,
        set_foreign_keys: bool = True,
        **kwargs,
    ):
        if sync_glossary or sync_tags:
            self._sync_metadata(manifest, sync_glossary, sync_tags)
        if set_primary_keys:
            self._set_primary_keys(manifest)
        if set_foreign_keys:
            self._set_foreign_keys(manifest)

    def _sync_metadata(self, manifest: "Manifest", sync_glossary: bool, sync_tags: bool):
        """
        Syncs metadata (comments for glossaries, and tags) from the manifest to the physical Databricks tables.
        """
        print("Syncing metadata to Databricks tables...")

        for source in manifest.sources.values():
            fqn = self._get_fqn(source.table.name)

            # Set table comment
            if sync_glossary and source.table.description:
                table_comment = source.table.description.replace("'", "\\'")
                self._execute_sql(f"COMMENT ON TABLE {fqn} IS '{table_comment}'")  # Works for views too

            # Set column comments and tags
            for column in source.table.columns:
                if sync_glossary and column.description:
                    col_comment = column.description.replace("'", "\\'")
                    self._execute_sql(f"COMMENT ON COLUMN {fqn}.`{column.name}` IS '{col_comment}'")

                if sync_tags and column.tags:
                    cleaned_tags = [clean_tag(tag) for tag in column.tags]
                    tag_assignments = ", ".join([f"'{tag}'" for tag in cleaned_tags])

                    # FIXME: Need to differentiate between TABLES and VIEWS for setting tags
                    try:
                        self._execute_sql(f"ALTER TABLE {fqn} ALTER COLUMN `{column.name}` SET TAGS ({tag_assignments})")
                    except Exception:
                        try:
                            self._execute_sql(f"ALTER VIEW {fqn} ALTER COLUMN `{column.name}` SET TAGS ({tag_assignments})")
                        except Exception as e:
                            print(f"Could not set tags '{tag_assignments}' on {fqn}.`{column.name}`: {e}")
                            
        print("Metadata sync complete.")

    def _set_primary_keys(self, manifest: "Manifest"):
        """
        Sets primary key constraints on the tables based on the manifest.
        """
        print("Setting primary key constraints...")
        for source in manifest.sources.values():
            if not source.table.key:
                print(f"Skipping primary key for table '{source.table.name}' due to missing or invalid key.")
                continue

            fqn = self._get_fqn(source.table.name)
            pk_columns = source.table.key.columns
            constraint_name = f"pk_{source.table.name}"
            try:
                for col in pk_columns:
                    # First, ensure the column is not nullable
                    self._execute_sql(f"ALTER TABLE {fqn} ALTER COLUMN `{col}` SET NOT NULL")
                # Then, add the primary key constraint
                self._execute_sql(f"ALTER TABLE {fqn} ADD CONSTRAINT {constraint_name} PRIMARY KEY (`" + "`, `".join(pk_columns) + "`)")
                print(f"Set primary key on {fqn} (`{pk_columns}`)")
            except Exception as e:
                print(f"Could not set primary key for {fqn}: {e}")
        print("Primary key setting complete.")

    def _set_foreign_keys(self, manifest: "Manifest"):
        """
        Sets foreign key constraints between tables based on the manifest relationships.
        """
        print("Setting foreign key constraints...")
        for rel in manifest.relationships.values():
            # resolved = resolve_relationship_direction(rel, manifest.sources)
            # if not resolved:
            #     print(f"Skipping invalid or ambiguous relationship '{rel.name}'.")
            #     continue
            
            try:
                child_fqn = self._get_fqn(rel.target.table)
                parent_fqn = self._get_fqn(rel.source.table)
                constraint_name = f"fk_{rel.name}"
                cleaned_constraint_name = clean_name(constraint_name)

                self._execute_sql(
                    f"ALTER TABLE {child_fqn} ADD CONSTRAINT {cleaned_constraint_name} "
                    f"FOREIGN KEY (`{'`, '.join(rel.target.columns)}`) REFERENCES {parent_fqn} (`{'`, '.join(rel.source.columns)}`)"
                )
            except Exception as e:
                print(f"Could not set foreign key for relationship {rel.name}: {e}")
        print("Foreign key setting complete.")

    def intersect_count(self, table1: "DataSet", column1_name: str, table2: "DataSet", column2_name: str) -> int:
        table1_adapter = self.check_data(table1.data)
        table2_adapter = self.check_data(table2.data)
        
        fqn1 = self._get_fqn(table1_adapter.identifier)
        fqn2 = self._get_fqn(table2_adapter.identifier)

        query = f"""
        SELECT COUNT(*) FROM (
            SELECT DISTINCT `{column1_name}` FROM {fqn1} WHERE `{column1_name}` IS NOT NULL
            INTERSECT
            SELECT DISTINCT `{column2_name}` FROM {fqn2} WHERE `{column2_name}` IS NOT NULL
        )
        """
        return self._execute_sql(query)[0][0]

    def get_composite_key_uniqueness(self, table_name: str, columns: list[str], dataset_data: DataSetData) -> int:
        data = self.check_data(dataset_data)
        fqn = self._get_fqn(data.identifier)
        safe_columns = [f"`{col}`" for col in columns]
        column_list = ", ".join(safe_columns)
        null_cols_filter = " AND ".join(f"{c} IS NOT NULL" for c in safe_columns)

        query = f"""
        SELECT COUNT(*) FROM (
            SELECT DISTINCT {column_list} FROM {fqn}
            WHERE {null_cols_filter}
        )
        """
        return self._execute_sql(query)[0][0]

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

        safe_columns1 = [f"`{col}`" for col in columns1]
        safe_columns2 = [f"`{col}`" for col in columns2]

        # Subquery for distinct keys from table 1
        distinct_cols1 = ", ".join(safe_columns1)
        null_filter1 = " AND ".join(f"{c} IS NOT NULL" for c in safe_columns1)
        subquery1 = f"(SELECT DISTINCT {distinct_cols1} FROM {fqn1} WHERE {null_filter1}) AS t1"

        # Subquery for distinct keys from table 2
        distinct_cols2 = ", ".join(safe_columns2)
        null_filter2 = " AND ".join(f"{c} IS NOT NULL" for c in safe_columns2)
        subquery2 = f"(SELECT DISTINCT {distinct_cols2} FROM {fqn2} WHERE {null_filter2}) AS t2"

        # Join conditions
        join_conditions = " AND ".join(
            [f"t1.{c1} = t2.{c2}" for c1, c2 in zip(safe_columns1, safe_columns2)]
        )

        query = f"""
        SELECT COUNT(*)
        FROM {subquery1}
        INNER JOIN {subquery2} ON {join_conditions}
        """
        return self._execute_sql(query)[0][0]

    def get_details(self, data: DatabricksConfig):
        data = self.check_data(data)
        return data.model_dump()


def can_handle_databricks(df: Any) -> bool:
    try:
        DatabricksConfig.model_validate(df)
        return True
    except Exception:
        return False


def register(factory: AdapterFactory):
    if DATABRICKS_AVAILABLE:
        factory.register("databricks", can_handle_databricks, DatabricksAdapter, DatabricksConfig)