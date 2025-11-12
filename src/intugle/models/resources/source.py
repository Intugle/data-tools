from typing import List, Optional, Union

from pydantic import Field, field_validator

from intugle.common.resources.base import BaseResource
from intugle.common.schema import NodeType, SchemaBase
from intugle.models.resources.model import Column, ModelProfilingMetrics, PrimaryKey


class SourceTables(SchemaBase):
    name: str
    description: str
    tags: Optional[List[str]] = Field(default_factory=list)
    details: Optional[dict] = None
    columns: List[Column] = Field(default_factory=list)
    profiling_metrics: Optional[ModelProfilingMetrics] = None
    key: Optional[PrimaryKey] = None
    source_last_modified: Optional[float] = None

    @field_validator("key", mode="before")
    @classmethod
    def validate_key(cls, value: Union[str, List[str], dict]) -> Optional[dict]:
        if value is None:
            return None
        if isinstance(value, str):
            return {"columns": [value]}
        if isinstance(value, list):
            return {"columns": value}
        return value


class Source(BaseResource):
    schema: str
    database: str
    resource_type: NodeType = NodeType.SOURCE
    table: SourceTables = Field(default_factory=list)
