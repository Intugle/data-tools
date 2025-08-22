from data_tools.core.settings import settings
from data_tools.mcp.adapter.psql import PsqlPool

# from data_tools.parser.manifest import ManifestLoader


class AdapterService:
    """
    Adapter service for executing queries.
    """

    def __init__(self):
        # self.manifest = ManifestLoader.manifest
        self.psql = PsqlPool(
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            host=settings.POSTGRES_HOST,
            database=settings.POSTGRES_DB,
            port=settings.POSTGRES_PORT,
            schema=settings.POSTGRES_SCHEMA,
        )

    async def execute_query(self, sql_query: str) -> list[dict]:
        """
        Execute a SQL query and return the result.

        Args:
            sql_query (str): The SQL query to execute.

        Returns:
            list[dict]: The result of the query execution.
        """

        data = await self.psql.fetch(sql_query)

        data = [dict(record) for record in data] if data else []

        return data


adapter_service = AdapterService()