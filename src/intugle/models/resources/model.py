from typing import Any, List, Literal, Optional

from pydantic import Field, field_validator

from intugle.common.resources.base import BaseResource
from intugle.common.schema import NodeType, SchemaBase


class ColumnProfilingMetrics(SchemaBase):
    count: Optional[int] = None
    null_count: Optional[int] = None
    distinct_count: Optional[int] = None
    sample_data: Optional[List[Any]] = Field(default_factory=list)
    dtype_sample: Optional[List[Any]] = Field(default_factory=list, exclude=True)

    @property
    def uniqueness(self) -> Optional[float]:
        """The ratio of distinct values to total count."""
        if self.count is not None and self.distinct_count is not None and self.count > 0:
            return self.distinct_count / self.count
        return None

    @property
    def completeness(self) -> Optional[float]:
        """The ratio of non-null values to total count."""
        if self.count is not None and self.null_count is not None and self.count > 0:
            return (self.count - self.null_count) / self.count
        return None


class Column(SchemaBase):
    name: str
    type: Optional[str] = None
    category: Literal["dimension", "measure"] = "dimension"
    description: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)
    profiling_metrics: Optional[ColumnProfilingMetrics] = None

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, value: str) -> Literal["dimension", "measure"]:
        if value not in ["dimension", "measure"]:
            return "dimension"
        return value


class ModelProfilingMetrics(SchemaBase):
    count: Optional[int] = None


class Model(BaseResource):
    resource_type: NodeType = NodeType.MODEL
    columns: List[Column] = Field(default_factory=list)
    profiling_metrics: Optional[ModelProfilingMetrics] = None