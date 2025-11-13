from typing import List, Optional, Annotated, Sequence, Dict, TypedDict

from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class Link(BaseModel):
    table1: Annotated[str, "Verbatim name of table1"]
    column1: Annotated[str, "Verbatim name of column1 in table1"]
    table2: Annotated[str, "Verbatim name of table2"]
    column2: Annotated[str, "Verbatim name of column2"]


class ForeignKeyResponse(BaseModel):
    links: Optional[List[Link]] = Field(
        description="Return list of links, return None if no links found", default=None
    )


class OutputSchema(BaseModel):
    links: Optional[List[Link]]
    intersect_count: Optional[int]
    intersect_ratio_col1: Optional[float]
    intersect_ratio_col2: Optional[float]
    from_uniqueness_ratio: Optional[float] = None
    to_uniqueness_ratio: Optional[float] = None
    table1_name: str
    table2_name: str
    save: bool = False


class ValiditySchema(BaseModel):
    message: str
    valid: bool = True
    extra: dict = {}


class GraphState(TypedDict):
    """The state of the link prediction agent."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    remaining_steps: int
    table1_name: str
    table2_name: str
