from enum import StrEnum
from typing import Optional

from data_tools.common.resources.base import BaseResource
from data_tools.common.schema import NodeType, SchemaBase


class RelationshipTable(SchemaBase):
    table: str
    column: str


class RelationshipProfilingMetrics(SchemaBase): ...


class RelationshipType(StrEnum):
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
