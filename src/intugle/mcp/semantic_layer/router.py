from mcp.server.fastmcp import FastMCP

from intugle.core.settings import settings

# from intugle.mcp.adapter.service import adapter_service
from intugle.mcp.docs_search.service import docs_search_service
from intugle.mcp.semantic_layer.prompt import Prompts
from intugle.mcp.semantic_layer.service import semantic_layer_service

semantic_layer_mcp = FastMCP(
    name=settings.MCP_SERVER_NAME,
    stateless_http=settings.MCP_SERVER_STATELESS_HTTP,
)


@semantic_layer_mcp.tool(
    name="get_tables",
    description="Get list of tables in database along with their technical description",
)
def get_tables() -> list[dict]:
    """
    Module used for fetching all the tables and their technical description for a subscription
    Args:
        subscription_id (str): Subscription to fetch the tables from

    Returns:
        dir: List of tables along with their technical description
    """
    tables = semantic_layer_service.get_tables()
    return tables


@semantic_layer_mcp.tool(
    name="get_schema",
    description="Given database table names, get the schemas of the tables including their relationships",
)
def get_schema(table_names: list[str]) -> dict[str, str]:
    """
    Given database table names fetch the schema along with some sample rows
    Args:
        question (str): The question from the client which is used to do dynamic row short listing
        tables (List[str]): List of tables to fetch the schema
        subscription_id (str): Subscription to fetch the schemas from

    Raises:
        Exception: _description_

    Returns:
        dict[str, str]: List of tables with there schemas along with shortlisted sample rows (dynamic + sample rows)
    """
    schemas = semantic_layer_service.get_schema(table_names)
    return schemas


# @semantic_layer_mcp.prompt(name="explore_data", title="Executor Agent Prompt")
# async def prompt() -> str:
#     print("Using prompt from semantic layer")
#     return Prompts.raw_executor_prompt(settings.SQL_DIALECT, settings.DOMAIN, settings.UNIVERSAL_INSTRUCTIONS)


@semantic_layer_mcp.prompt(
    name="intugle-vibe",
    title="Intugle Vibe Prompt",
    description="A helpful AI assistant for the Intugle library.",
)
async def intugle_vibe_prompt(user_query: str) -> str:
    return await Prompts.intugle_vibe_prompt(user_query)


# @semantic_layer_mcp.prompt(name="create-dp", title="Create Data Product Specification")
# async def create_dp_prompt(user_request: str) -> str:
#     return Prompts.create_dp_prompt(user_request)


# @semantic_layer_mcp.tool(name="execute_query", description="Return the result of a query execution")
# async def execute_query(sql_query: str) -> list[dict]: 
#     data = await adapter_service.execute_query(sql_query)
#     return data


@semantic_layer_mcp.tool(
    name="search_intugle_docs",
    description="Fetches content from the Intugle documentation for a given list of page paths.",
)
async def search_intugle_docs(paths: list[str]) -> str:
    """
    Fetches content from the Intugle documentation.

    Args:
        paths (list[str]): A list of markdown file paths (e.g., ["intro.md", "core-concepts/semantic-model.md"])

    Returns:
        str: The concatenated content of the documentation files.
    """
    return await docs_search_service.search_docs(paths)