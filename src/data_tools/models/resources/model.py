from typing import Any, List, Literal, Optional

from pydantic import Field

from data_tools.common.resources.base import BaseResource
from data_tools.common.schema import NodeType, SchemaBase


class ColumnProfilingMetrics(SchemaBase):
    count: Optional[int] = None
    null_count: Optional[int] = None
    distinct_count: Optional[int] = None
    sample_data: Optional[List[Any]] = Field(default_factory=list)


class Column(SchemaBase):
    name: str
    type: Optional[str] = None
    category: Literal["dimension", "measure"] = "dimension"
    description: str
    tags: Optional[List[str]] = Field(default_factory=list)
    profiling_metrics: Optional[ColumnProfilingMetrics] = None


class ModelProfilingMetrics(SchemaBase):
    count: Optional[int] = None


class Model(BaseResource):
    resource_type: NodeType = NodeType.MODEL
    columns: List[Column] = Field(default_factory=list)
    profiling_metrics: Optional[ModelProfilingMetrics] = None

