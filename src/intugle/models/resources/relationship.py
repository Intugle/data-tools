from enum import Enum
from typing import Optional

from intugle.common.resources.base import BaseResource
from intugle.common.schema import NodeType, SchemaBase
from intugle.libs.smart_query_generator.models.models import LinkModel


class RelationshipTable(SchemaBase):
    table: str
    column: str


class RelationshipProfilingMetrics(SchemaBase):
    intersect_count: Optional[int] = None
    intersect_ratio_from_col: Optional[float] = None
    intersect_ratio_to_col: Optional[float] = None
    accuracy: Optional[float] = None


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
        source_field_id = f"{self.source.table}.{self.source.column}"
        target_field_id = f"{self.target.table}.{self.target.column}"
        link: LinkModel = LinkModel(
            id=self.name,
            source_field_id=source_field_id,
            source_asset_id=self.source.table,
            target_field_id=target_field_id,
            target_asset_id=self.target.table,
        )
        return link
