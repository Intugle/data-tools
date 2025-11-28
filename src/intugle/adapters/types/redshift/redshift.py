import redshift_connector
from typing import Any, Optional, Iterable

from intugle.adapters.adapter import Adapter
from intugle.adapters.models import (
    DataSetData,
    ColumnProfile,
    ProfilingOutput,
)
from intugle.adapters.utils import convert_to_native

from .models import RedshiftConfig, RedshiftDataConfig


class RedshiftAdapter(Adapter):
    """
    Amazon Redshift adapter for Intugle.

    Works similarly to PostgresAdapter but uses redshift_connector.
    """

    config_model = RedshiftConfig
    data_config_model = RedshiftDataConfig

    def __init__(self, config: RedshiftConfig):
        self.config = config
        self.connection = None

    # -------------------------------------------------------
    # CONNECTION
    # -------------------------------------------------------
    def connect(self):
        """
        Establish a connection to Redshift.
        Supports IAM + password authentication.
        """
        if self.connection:
            return self.connection

        if self.config.iam:
            # IAM authentication
            self.connection = redshift_connector.connect(
                iam=True,
                db_user=self.config.user,
                cluster_identifier=self.config.cluster_id,
                region=self.config.region,
                database=self.config.database,
            )
        else:
            # Standard user/password auth
            password = (
                self.config.password.get_secret_value()
                if self.config.password
                else None
            )

            self.connection = redshift_connector.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=password,
                ssl=self.config.ssl,
                timeout=self.config.connect_timeout,
            )

        return self.connection

    def close(self):
        """
        Close the Redshift connection.
        """
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass
        self.connection = None

    # -------------------------------------------------------
    # QUERY EXECUTION
    # -------------------------------------------------------
    def execute(self, query: str, params: Optional[Iterable[Any]] = None):
        """
        Execute SQL and return cursor.
        """
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute(query, params)
        return cursor

    def fetch_dataframe(self, query: str) -> DataSetData:
        """
        Execute a query and return a Pandas DataFrame wrapped in DataSetData.
        """
        cursor = self.execute(query)
        rows = cursor.fetchall()
        cols = [col[0] for col in cursor.description]

        import pandas as pd

        df = pd.DataFrame(rows, columns=cols)
        return DataSetData(native=df)

    # -------------------------------------------------------
    # METADATA
    # -------------------------------------------------------
    def get_tables(self, schema: Optional[str] = None):
        """
        Return list of tables from Redshift.
        """
        schema = schema or "public"

        query = f"""
            SELECT tablename
            FROM pg_catalog.pg_tables
            WHERE schemaname = '{schema}'
            ORDER BY tablename;
        """

        cursor = self.execute(query)
        return [row[0] for row in cursor.fetchall()]

    def get_columns(self, table: str, schema: Optional[str] = None):
        """
        Return column metadata for a table.
        """
        schema = schema or "public"

        query = f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = '{table}'
            AND table_schema = '{schema}'
            ORDER BY ordinal_position;
        """

        cursor = self.execute(query)
        return [
            {"name": row[0], "type": row[1]}
            for row in cursor.fetchall()
        ]

    # -------------------------------------------------------
    # PROFILING
    # -------------------------------------------------------
    def profile_table(self, table: str, schema: Optional[str] = None) -> ProfilingOutput:
        """
        Profile a table's structure using Redshift metadata.
        """
        columns = self.get_columns(table, schema)
        profiles = [
            ColumnProfile(
                name=col["name"],
                type=col["type"],
            )
            for col in columns
        ]
        return ProfilingOutput(columns=profiles)

    # -------------------------------------------------------
    # DATA CREATION
    # -------------------------------------------------------
    def create_table_as(self, new_table: str, query: str, schema: Optional[str] = None):
        """
        Create a new table from a SELECT query (CTAS).
        """
        schema = schema or "public"

        sql = f"""
            CREATE TABLE {schema}.{new_table} AS
            {query}
        """

        self.execute(sql)

    def create_view(self, new_view: str, query: str, schema: Optional[str] = None):
        """
        Create a view from a SELECT query.
        """
        schema = schema or "public"

        sql = f"""
            CREATE OR REPLACE VIEW {schema}.{new_view} AS
            {query}
        """

        self.execute(sql)

    # -------------------------------------------------------
    # CLEANUP
    # -------------------------------------------------------
    def __del__(self):
        self.close()
