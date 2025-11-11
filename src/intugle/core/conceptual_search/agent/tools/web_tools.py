import logging

from langchain.schema import Document
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import tool

from intugle.core import settings

log = logging.getLogger(__name__)

web_search_tool = TavilySearchResults(k=3, tavily_api_key=settings.TAVILY_API_KEY) if settings.TAVILY_API_KEY else None


@tool
def web_search(question: str) -> str:
    """
    Google search to get more ideas on dimensions and measures used in the data product

    Args:
        question (str): The question to web search for

    Returns:
        web_results (str): results of the web search
    """
    # Web search
    log.info(f"Input statement: '{question}'")
    try:
        if not web_search_tool:
            log.error("TAVILY_API_KEY is not set. Web search tool is unavailable.")
            return Document(page_content="Web search tool is unavailable because TAVILY_API_KEY is not set.")
        docs = web_search_tool.invoke({"query": question})
        web_results = "\n".join([d["content"] for d in docs])
        log.info(f"Web search results:\n{web_results}")  # Print the search results
        web_results = Document(page_content=web_results)
        return web_results
    except Exception as e:
        log.error(f"Error during web search: {e}")
        return Document(page_content=f"Error during web search: {e}")
