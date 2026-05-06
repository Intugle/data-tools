from types import SimpleNamespace
from unittest.mock import MagicMock

from intugle.adapters.types.bigquery.bigquery import BigQueryAdapter
from intugle.adapters.types.databricks.databricks import DatabricksAdapter
from intugle.adapters.types.postgres.postgres import PostgresAdapter
from intugle.adapters.types.sqlserver import sqlserver as sqlserver_module
from intugle.adapters.types.sqlserver.sqlserver import SQLServerAdapter
from intugle.data_product import DataProduct


def test_bigquery_get_fqn_escapes_compound_identifier():
    adapter = BigQueryAdapter.__new__(BigQueryAdapter)
    adapter._project_id = "test-project"
    adapter._dataset_id = "analytics"

    fqn = adapter._get_fqn("users`; DROP TABLE accounts; --")

    assert fqn == "`test-project.analytics.users``; DROP TABLE accounts; --`"


def test_databricks_get_fqn_quotes_each_identifier_segment():
    adapter = DatabricksAdapter.__new__(DatabricksAdapter)
    adapter.catalog = "main"
    adapter._schema = "analytics"

    fqn = adapter._get_fqn("sales.orders`; DROP TABLE users; --")

    assert fqn == "`sales`.`orders``; DROP TABLE users; --`"


def test_postgres_column_profile_escapes_column_identifier():
    adapter = PostgresAdapter.__new__(PostgresAdapter)
    adapter._schema = "public"

    captured_queries: list[str] = []

    def fake_execute(query: str, *args):
        captured_queries.append(query)
        if "COUNT(*) FILTER" in query:
            return [{"null_count": 0, "distinct_count": 1}]
        return [("sample@example.com",)]

    adapter._execute_sql = fake_execute

    adapter.column_profile(
        data={"identifier": 'users"; DROP TABLE accounts; --', "type": "postgres"},
        table_name="users",
        column_name='email"; SELECT pg_sleep(1); --',
        total_count=1,
        sample_limit=1,
        dtype_sample_limit=1,
    )

    assert captured_queries
    assert '"email""; SELECT pg_sleep(1); --"' in captured_queries[0]
    assert 'DROP TABLE accounts; --"' in captured_queries[0]


def test_sqlserver_create_table_from_query_escapes_object_id_literal(monkeypatch):
    monkeypatch.setattr(sqlserver_module, "transpile", lambda query, write: [query], raising=False)

    adapter = SQLServerAdapter.__new__(SQLServerAdapter)
    adapter._schema = "dbo"
    adapter.connection = MagicMock()

    executed_queries: list[str] = []
    adapter._execute_sql = lambda query, *args: executed_queries.append(query) or []

    adapter.create_table_from_query("orders'name", "SELECT 1", materialize="view")

    assert "OBJECT_ID('[dbo].[orders''name]', 'V')" in executed_queries[0]
    assert "CREATE VIEW [dbo].[orders'name] AS SELECT 1" == executed_queries[1]


def test_data_product_marks_pii_and_escapes_sql_code():
    source = SimpleNamespace(
        schema_="public",
        schema="public",
        table=SimpleNamespace(
            name='users"; DROP TABLE accounts; --',
            details={"type": "postgres"},
            columns=[
                SimpleNamespace(
                    name='email"; SELECT 1; --',
                    type="string",
                    category="dimension",
                    tags=["PII", "customer"],
                )
            ],
        ),
    )

    dp = DataProduct.__new__(DataProduct)
    dp.manifest = SimpleNamespace(sources={"users": source}, relationships={})

    field_details = dp.get_all_field_details()
    field_detail = next(iter(field_details.values()))

    assert field_detail.is_pii is True
    assert (
        field_detail.sql_code
        == '"users""; DROP TABLE accounts; --"."email""; SELECT 1; --"'
    )
