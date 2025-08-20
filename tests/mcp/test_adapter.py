import functools

from enum import StrEnum

import pytest
import pytest_asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = "http://127.0.0.1:8080/adapter/mcp"


class Tools(StrEnum):
    GET_TABLES = "get_tables"
    GET_SCHEMA = "get_schema"
    EXECUTE_QUERY = "execute_query"

    def __repr__(self) -> str:
        return self.value


def connection_decorator():
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            async with streamablehttp_client(URL) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return await func(*args, **kwargs, session=session)

        return wrapper

    return decorator


class MCPTools:
    def __init__(self): ...

    @connection_decorator()
    async def execute_query(self, session: ClientSession = None):
        await session.call_tool(
            name=Tools.EXECUTE_QUERY, arguments={"sql_query": "SELECT 1"}
        )
        # assert isinstance(schemas.structuredContent, dict)


@pytest_asyncio.fixture
async def mcp_server_tools() -> MCPTools:
    return MCPTools()


# @pytest.mark.asyncio
# async def test_mcp_execute_query(mcp_server_tools):
#     await mcp_server_tools.execute_query()
