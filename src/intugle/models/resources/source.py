from typing import List, Optional

from pydantic import Field

from intugle.common.resources.base import BaseResource
from intugle.common.schema import NodeType, SchemaBase
from intugle.models.resources.model import Column, ModelProfilingMetrics


class SourceTables(SchemaBase):
    name: str
    description: str
    tags: Optional[List[str]] = Field(default_factory=list)
    details: Optional[dict] = None
    columns: List[Column] = Field(default_factory=list)
    profiling_metrics: Optional[ModelProfilingMetrics] = None
    key: Optional[str] = None
    source_last_modified: Optional[float] = None


class Source(BaseResource):
    schema: str
    database: str
    resource_type: NodeType = NodeType.SOURCE
    table: SourceTables = Field(default_factory=list)
