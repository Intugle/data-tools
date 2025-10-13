# from mcp.server.fastmcp import FastMCP

# from intugle.core.settings import settings
# from intugle.mcp.adapter.service import adapter_service

# adapter_mcp = FastMCP(
#     name=settings.MCP_SERVER_NAME,
#     stateless_http=settings.MCP_SERVER_STATELESS_HTTP,
# )


# @adapter_mcp.tool(name="execute_query", description="Return the result of a query execution")
# async def execute_query(sql_query: str) -> list[dict]: 
#     data = adapter_service.execute_query(sql_query)
#     print(data)
#     return data
