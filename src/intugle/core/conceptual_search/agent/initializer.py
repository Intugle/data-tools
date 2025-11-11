from typing import List

from langchain_core.runnables import RunnableSerializable
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent

from intugle.core import settings
from intugle.core.conceptual_search.agent.prompts import (
    data_product_builder_prompt,
    data_product_planner_prompt,
)
from intugle.core.conceptual_search.agent.tools.web_tools import web_search


def data_product_planner_agent(llm, tools: List[StructuredTool]) -> RunnableSerializable:
    agent = create_react_agent(
        llm, tools + ([web_search] if settings.TAVILY_API_KEY else []), prompt=data_product_planner_prompt
    )

    return agent


def data_product_builder_agent(llm, tools: List[StructuredTool]) -> RunnableSerializable:
    agent = create_react_agent(llm, tools=tools, prompt=data_product_builder_prompt)
    return agent
