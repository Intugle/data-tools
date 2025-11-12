from typing import List, Optional, Annotated, Sequence, Dict, TypedDict, Union

from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from langgraph.prebuilt import InjectedState


class Link(BaseModel):
    table1: Annotated[str, "Verbatim name of table1"]
    column1: Annotated[str, "Verbatim name of column1 in table1"]
    table2: Annotated[str, "Verbatim name of table2"]
    column2: Annotated[str, "Verbatim name of column2"]


class ForeignKeyResponse(BaseModel):
    links: Optional[List[Link]] = Field(
        description="Return list of links, return None if no links found", default=None
    )


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    remaining_steps: int = 25
    table1_name: str
    table2_name: str


class OutputSchema(BaseModel):
    links: Optional[List[Link]]
    intersect_count: Optional[int]
    intersect_ratio_col1: Optional[float]
    intersect_ratio_col2: Optional[float]
    table1_name: str
    table2_name: str
    save: bool = False


class ValiditySchema(BaseModel):
    message: str
    valid: bool = True
    extra:dict = {}


class GraphState(TypedDict):
    input_text: str
    potential_link: dict
    error_msg: List[str]
    iteration: int
    link_type: str
    if_error: bool
    intersect_count: Optional[int] = None
    intersect_ratio_from_col: Optional[float] = None
    intersect_ratio_to_col: Optional[float] = None
    accuracy: Optional[float] = None
