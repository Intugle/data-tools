from enum import Enum
from typing import List, Optional

from pydantic import field_validator

from intugle.common.resources.base import BaseResource
from intugle.common.schema import NodeType, SchemaBase
from intugle.libs.smart_query_generator.models.models import LinkModel


class RelationshipTable(SchemaBase):
    table: str
    columns: List[str]

    @field_validator("columns", mode="before")
    @classmethod
    def validate_columns(cls, value: str | List[str]) -> List[str]:
        if isinstance(value, str):
            return [value]
        return value


class RelationshipProfilingMetrics(SchemaBase):
    intersect_count: Optional[int] = None
    intersect_ratio_from_col: Optional[float] = None
    intersect_ratio_to_col: Optional[float] = None
    accuracy: Optional[float] = None
    from_uniqueness_ratio: Optional[float] = None
    to_uniqueness_ratio: Optional[float] = None


class RelationshipType(str, Enum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"


class Relationship(BaseResource):
    resource_type: NodeType = NodeType.RELATIONSHIP
    source: RelationshipTable
    target: RelationshipTable
    profiling_metrics: Optional[RelationshipProfilingMetrics] = None
    type: RelationshipType

    @property
    def link(self) -> LinkModel:
        source_field_ids = [f"{self.source.table}.{col}" for col in self.source.columns]
        target_field_ids = [f"{self.target.table}.{col}" for col in self.target.columns]
        link: LinkModel = LinkModel(
            id=self.name,
            source_field_ids=source_field_ids,
            source_asset_id=self.source.table,
            target_field_ids=target_field_ids,
            target_asset_id=self.target.table,
            type=self.type,
        )
        return link
