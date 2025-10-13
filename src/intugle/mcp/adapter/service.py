# # from intugle.adapters.factory import AdapterFactory
# from intugle.adapters.types.duckdb.duckdb import DuckdbAdapter
# from intugle.analysis.models import DataSet
# from intugle.mcp.manifest import manifest_loader


# class AdapterService:
#     """
#     Adapter service for executing queries.
#     """

#     # Not good way to do it Need to create extandable and properly couple with adapter
#     def __init__(self, adapter: str = "duckdb"):
#         self.manifest = manifest_loader.manifest
#         self.adapter = DuckdbAdapter()
#         self.load_all()

#     def load_all(self):
#         sources = self.manifest.sources
#         for source in sources.values():
#             table_name = source.table.name
#             details = source.table.details

#             DataSet(data=details, name=table_name)

#     async def execute_query(self, sql_query: str) -> list[dict]:
#         """
#         Execute a SQL query and return the result.

#         Args:
#             sql_query (str): The SQL query to execute.

#         Returns:
#             list[dict]: The result of the query execution.
#         """

#         data = self.adapter.execute(sql_query)

#         data = [dict(record) for record in data] if data else []

#         return data


# adapter_service = AdapterService()
