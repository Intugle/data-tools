import time
from typing import TYPE_CHECKING, Any, Optional

import numpy as np
import pandas as pd

from intugle.adapters.adapter import Adapter
from intugle.adapters.factory import AdapterFactory
from intugle.adapters.models import ColumnProfile, DataSetData, ProfilingOutput
from intugle.adapters.types.bigquery.models import BigQueryConfig, BigQueryConnectionConfig
from intugle.adapters.utils import convert_to_native
from intugle.core import settings
from intugle.core.utilities.processing import string_standardization

if TYPE_CHECKING:
    from intugle.analysis.models import DataSet

try:
    from google.cloud import bigquery
    from google.oauth2 import service_account
    from sqlglot import transpile

    BIGQUERY_AVAILABLE = True
except ImportError:
    BIGQUERY_AVAILABLE = False


class BigQueryAdapter(Adapter):
    _instance = None
    _initialized = False

    @property
    def database(self) -> Optional[str]:
        return self._project_id

    @database.setter
    def database(self, value: str):
        self._project_id = value

    @property
    def schema(self) -> Optional[str]:
        return self._dataset_id

    @schema.setter
    def schema(self, value: str):
        self._dataset_id = value

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

        if not BIGQUERY_AVAILABLE:
            raise ImportError(
                "BigQuery dependencies are not installed. Please run 'pip install intugle[bigquery]'."
            )

        self.client: Optional["bigquery.Client"] = None
        self._project_id: Optional[str] = None
        self._dataset_id: Optional[str] = None
        self._location: str = "US"
        self._source_name: str = settings.PROFILES.get("bigquery", {}).get("name", "my_bigquery_source")

        self.connect()
        self._initialized = True

    def connect(self):
        """Establish connection to BigQuery."""
        connection_parameters_dict = settings.PROFILES.get("bigquery", {})
        if not connection_parameters_dict:
            raise ValueError("Could not create BigQuery connection. No 'bigquery' section found in profiles.yml.")

        params = BigQueryConnectionConfig.model_validate(connection_parameters_dict)
        self._project_id = params.project_id
        self._dataset_id = params.dataset_id
        self._location = params.location

        # Initialize BigQuery client with credentials if provided
        if params.credentials_path:
            credentials = service_account.Credentials.from_service_account_file(params.credentials_path)
            self.client = bigquery.Client(project=self._project_id, credentials=credentials, location=self._location)
        else:
            # Use default credentials (Application Default Credentials)
            self.client = bigquery.Client(project=self._project_id, location=self._location)

    def _get_fqn(self, identifier: str) -> str:
        """Gets the fully qualified name for a table identifier."""
        if "." in identifier:
            # Already has project or dataset prefix
            parts = identifier.split(".")
            if len(parts) == 2:
                # dataset.table format
                return f"`{self._project_id}.{identifier}`"
            elif len(parts) == 3:
                # project.dataset.table format
                return f"`{identifier}`"
        return f"`{self._project_id}.{self._dataset_id}.{identifier}`"

    @staticmethod
    def check_data(data: Any) -> BigQueryConfig:
        try:
            data = BigQueryConfig.model_validate(data)
        except Exception:
            raise TypeError("Input must be a BigQuery config.")
        return data

    def _execute_sql(self, query: str) -> list[Any]:
        """Execute a SQL query and return results as a list of rows."""
        job_config = bigquery.QueryJobConfig(default_dataset=f"{self._project_id}.{self._dataset_id}")
        query_job = self.client.query(query, job_config=job_config)
        results = query_job.result()
        return [dict(row) for row in results]

    def _get_pandas_df(self, query: str) -> pd.DataFrame:
        """Execute a SQL query and return results as a pandas DataFrame."""
        job_config = bigquery.QueryJobConfig(default_dataset=f"{self._project_id}.{self._dataset_id}")
        query_job = self.client.query(query, job_config=job_config)
        return query_job.to_dataframe()

    def profile(self, data: BigQueryConfig, table_name: str) -> ProfilingOutput:
        """Profile a BigQuery table."""
        data = self.check_data(data)
        fqn = self._get_fqn(data.identifier)

        # Get total count
        count_query = f"SELECT COUNT(*) as count FROM {fqn}"
        total_count = self._execute_sql(count_query)[0]["count"]

        # Get column information from INFORMATION_SCHEMA
        schema_query = f"""
        SELECT column_name, data_type
        FROM `{self._project_id}.{self._dataset_id}.INFORMATION_SCHEMA.COLUMNS`
        WHERE table_name = @table_name
        ORDER BY ordinal_position
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("table_name", "STRING", data.identifier)]
        )
        query_job = self.client.query(schema_query, job_config=job_config)
        rows = [dict(row) for row in query_job.result()]

        columns = [row["column_name"] for row in rows]
        dtypes = {row["column_name"]: row["data_type"] for row in rows}

        return ProfilingOutput(
            count=total_count,
            columns=columns,
            dtypes=dtypes,
        )

    def column_profile(
        self,
        data: BigQueryConfig,
        table_name: str,
        column_name: str,
        total_count: int,
        sample_limit: int = 10,
        dtype_sample_limit: int = 10000,
    ) -> Optional[ColumnProfile]:
        """Profile a specific column in a BigQuery table."""
        data = self.check_data(data)
        fqn = self._get_fqn(data.identifier)
        start_ts = time.time()

        # Null and distinct counts
        query = f"""
        SELECT
            COUNTIF(`{column_name}` IS NULL) as null_count,
            COUNT(DISTINCT `{column_name}`) as distinct_count
        FROM {fqn}
        """
        result = self._execute_sql(query)[0]
        null_count = result["null_count"]
        distinct_count = result["distinct_count"]
        not_null_count = total_count - null_count

        # Sampling for distinct values
        sample_query = f"""
        SELECT DISTINCT CAST(`{column_name}` AS STRING) as value
        FROM {fqn}
        WHERE `{column_name}` IS NOT NULL
        LIMIT {dtype_sample_limit}
        """
        distinct_values_result = self._execute_sql(sample_query)
        distinct_values = [row["value"] for row in distinct_values_result if row["value"] is not None]

        if distinct_count > 0 and len(distinct_values) > 0:
            distinct_sample_size = min(distinct_count, dtype_sample_limit, len(distinct_values))
            sample_data = list(np.random.choice(distinct_values, distinct_sample_size, replace=False))
        else:
            sample_data = []

        dtype_sample = None
        if distinct_count >= dtype_sample_limit:
            dtype_sample = sample_data
        elif distinct_count > 0 and not_null_count > 0:
            remaining_sample_size = dtype_sample_limit - len(distinct_values)
            if remaining_sample_size > 0:
                additional_samples_query = f"""
                SELECT CAST(`{column_name}` AS STRING) as value
                FROM {fqn}
                WHERE `{column_name}` IS NOT NULL
                ORDER BY RAND()
                LIMIT {remaining_sample_size}
                """
                additional_samples_result = self._execute_sql(additional_samples_query)
                additional_samples = [row["value"] for row in additional_samples_result if row["value"] is not None]
                dtype_sample = list(distinct_values) + additional_samples
            else:
                dtype_sample = list(distinct_values)
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

    def load(self, data: BigQueryConfig, table_name: str):
        """Load data into BigQuery table."""
        data = self.check_data(data)
        # This method is typically used for loading data from other sources
        # Implementation depends on the specific use case
        # raise NotImplementedError("Load method needs to be implemented based on specific requirements.")

    def execute(self, query: str):
        """Execute a SQL query."""
        job_config = bigquery.QueryJobConfig(default_dataset=f"{self._project_id}.{self._dataset_id}")
        query_job = self.client.query(query, job_config=job_config)
        query_job.result()  # Wait for the query to complete
        return query_job

    def to_df(self, data: DataSetData, table_name: str) -> pd.DataFrame:
        """Convert BigQuery table to pandas DataFrame."""
        data = self.check_data(data)
        fqn = self._get_fqn(data.identifier)
        query = f"SELECT * FROM {fqn}"
        return self._get_pandas_df(query)

    def to_df_from_query(self, query: str) -> pd.DataFrame:
        """Execute a query and return results as DataFrame."""
        return self._get_pandas_df(query)

    def create_table_from_query(
        self, table_name: str, query: str, materialize: str = "view", **kwargs
    ) -> str:
        """Create a table or view from a query."""
        fqn = self._get_fqn(table_name)
        transpiled_sql = transpile(query, write="bigquery")[0]

        if materialize == "view":
            create_query = f"CREATE OR REPLACE VIEW {fqn} AS {transpiled_sql}"
        elif materialize == "table":
            create_query = f"CREATE OR REPLACE TABLE {fqn} AS {transpiled_sql}"
        else:
            raise ValueError(f"Invalid materialize option: {materialize}. Use 'table' or 'view'.")

        self.execute(create_query)
        return transpiled_sql

    def create_new_config_from_etl(self, etl_name: str) -> DataSetData:
        """Create a new config for an ETL-generated table."""
        return BigQueryConfig(identifier=etl_name, type="bigquery")

    def intersect_count(
        self, table1: "DataSet", column1_name: str, table2: "DataSet", column2_name: str
    ) -> int:
        """Count intersecting values between two columns."""
        data1 = self.check_data(table1.data)
        data2 = self.check_data(table2.data)
        fqn1 = self._get_fqn(data1.identifier)
        fqn2 = self._get_fqn(data2.identifier)

        query = f"""
        SELECT COUNT(*) as count
        FROM (
            SELECT DISTINCT `{column1_name}` as key
            FROM {fqn1}
            WHERE `{column1_name}` IS NOT NULL
        ) t1
        INNER JOIN (
            SELECT DISTINCT `{column2_name}` as key
            FROM {fqn2}
            WHERE `{column2_name}` IS NOT NULL
        ) t2
        ON t1.key = t2.key
        """
        return self._execute_sql(query)[0]["count"]

    def get_composite_key_uniqueness(
        self, table_name: str, columns: list[str], dataset_data: DataSetData
    ) -> int:
        """Get the number of unique composite key combinations."""
        data = self.check_data(dataset_data)
        fqn = self._get_fqn(data.identifier)

        # Build column list with backticks
        safe_columns = [f"`{col}`" for col in columns]
        columns_str = ", ".join(safe_columns)

        # Build null filter
        null_filter = " AND ".join(f"{col} IS NOT NULL" for col in safe_columns)

        query = f"""
        SELECT COUNT(*) as count
        FROM (
            SELECT DISTINCT {columns_str}
            FROM {fqn}
            WHERE {null_filter}
        )
        """
        return self._execute_sql(query)[0]["count"]

    def intersect_composite_keys_count(
        self,
        table1: "DataSet",
        columns1: list[str],
        table2: "DataSet",
        columns2: list[str],
    ) -> int:
        """Count intersecting composite key combinations between two tables."""
        if len(columns1) != len(columns2):
            raise ValueError("Column lists must have the same length for composite key intersection.")

        data1 = self.check_data(table1.data)
        data2 = self.check_data(table2.data)
        fqn1 = self._get_fqn(data1.identifier)
        fqn2 = self._get_fqn(data2.identifier)

        # Build column lists with backticks
        safe_columns1 = [f"`{col}`" for col in columns1]
        safe_columns2 = [f"`{col}`" for col in columns2]

        # Subquery for distinct keys from table 1
        distinct_cols1 = ", ".join(safe_columns1)
        null_filter1 = " AND ".join(f"{c} IS NOT NULL" for c in safe_columns1)
        subquery1 = f"""(
            SELECT DISTINCT {distinct_cols1}
            FROM {fqn1}
            WHERE {null_filter1}
        ) AS t1"""

        # Subquery for distinct keys from table 2
        distinct_cols2 = ", ".join(safe_columns2)
        null_filter2 = " AND ".join(f"{c} IS NOT NULL" for c in safe_columns2)
        subquery2 = f"""(
            SELECT DISTINCT {distinct_cols2}
            FROM {fqn2}
            WHERE {null_filter2}
        ) AS t2"""

        # Join conditions
        join_conditions = " AND ".join(
            [f"t1.{c1} = t2.{c2}" for c1, c2 in zip(safe_columns1, safe_columns2)]
        )

        query = f"""
        SELECT COUNT(*) as count
        FROM {subquery1}
        INNER JOIN {subquery2} ON {join_conditions}
        """
        return self._execute_sql(query)[0]["count"]

    def get_details(self, data: BigQueryConfig):
        """Get configuration details."""
        data = self.check_data(data)
        return data.model_dump()


def can_handle_bigquery(df: Any) -> bool:
    """Check if the data is a BigQuery config."""
    try:
        BigQueryConfig.model_validate(df)
        return True
    except Exception:
        return False


def register(factory: AdapterFactory):
    """Register the BigQuery adapter with the factory."""
    if BIGQUERY_AVAILABLE:
        factory.register("bigquery", can_handle_bigquery, BigQueryAdapter, BigQueryConfig)
