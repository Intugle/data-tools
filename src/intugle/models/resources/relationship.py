from enum import Enum
from typing import List, Optional, Union

from pydantic import field_validator

from intugle.common.resources.base import BaseResource
from intugle.common.schema import NodeType, SchemaBase
from intugle.libs.smart_query_generator.models.models import LinkModel


class RelationshipTable(SchemaBase):
    table: str
    columns: List[str]

    @field_validator("columns", mode="before")
    @classmethod
    def validate_columns(cls, value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, str):
            return [value]
        return value


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
        # For simplicity in the LinkModel, we'll join composite keys with a separator.
        # This might need a more sophisticated handling depending on the consumer of LinkModel.
        source_column_id = ".".join(self.source.columns)
        target_column_id = ".".join(self.target.columns)

        source_field_id = f"{self.source.table}.{source_column_id}"
        target_field_id = f"{self.target.table}.{target_column_id}"
        link: LinkModel = LinkModel(
            id=self.name,
            source_field_id=source_field_id,
            source_asset_id=self.source.table,
            target_field_id=target_field_id,
            target_asset_id=self.target.table,
        )
        return link
