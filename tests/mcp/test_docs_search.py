import functools

from enum import Enum

import pytest
import pytest_asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = "http://127.0.0.1:8080/semantic_layer/mcp"


class Prompts(str, Enum):
    INTUGLE_VIBE = "intugle-vibe"

    def __repr__(self) -> str:
        return self.value


class Tools(str, Enum):
    SEARCH_INTUGLE_DOCS = "search_intugle_docs"

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
    def __init__(self):
        ...

    @connection_decorator()
    async def search_intugle_docs(self, session: ClientSession = None):
        docs = await session.call_tool(
            name=Tools.SEARCH_INTUGLE_DOCS, arguments={"paths": ["intro.md"]}
        )

        assert isinstance(docs.structuredContent["result"], str)
        assert len(docs.structuredContent["result"]) > 0

    @connection_decorator()
    async def intugle_vibe_prompt(self, session: ClientSession = None):
        prompt = await session.get_prompt(name=Prompts.INTUGLE_VIBE, arguments={"user_query": "What is Intugle?"})

        prompt_text = prompt.messages[0].content.text

        assert isinstance(prompt_text, str)
        assert len(prompt_text) > 0
        assert "About Intugle" in prompt_text
        assert "Available Documentation Paths:" in prompt_text
        assert ".md" in prompt_text
        assert prompt.description


@pytest_asyncio.fixture
async def mcp_server_tools() -> MCPTools:
    return MCPTools()


@pytest.mark.mcp
@pytest.mark.asyncio
async def test_mcp_search_intugle_docs(mcp_server_tools):
    await mcp_server_tools.search_intugle_docs()


@pytest.mark.mcp
@pytest.mark.asyncio
async def test_mcp_intugle_vibe_prompt(mcp_server_tools):
    await mcp_server_tools.intugle_vibe_prompt()
 