from typing import List, Optional, Union

from pydantic import BaseModel, field_validator

from intugle.common.exception import errors
from intugle.models.resources.relationship import (
    Relationship,
    RelationshipProfilingMetrics,
    RelationshipTable,
    RelationshipType,
)


class PredictedLink(BaseModel):
    """
    Represents a single predicted link between columns from different datasets.
    Can represent both simple (single-column) and composite (multi-column) links.
    """

    from_dataset: str
    from_columns: List[str]
    to_dataset: str
    to_columns: List[str]
    intersect_count: Optional[int] = None
    intersect_ratio_from_col: Optional[float] = None
    intersect_ratio_to_col: Optional[float] = None
    accuracy: Optional[float] = None

    @field_validator("from_columns", "to_columns", mode="before")
    @classmethod
    def validate_columns(cls, value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, str):
            return [value]
        return value

    @property
    def relationship(self) -> Relationship:
        source = RelationshipTable(table=self.from_dataset, columns=self.from_columns)
        target = RelationshipTable(table=self.to_dataset, columns=self.to_columns)
        profiling_metrics = RelationshipProfilingMetrics(
            intersect_count=self.intersect_count,
            intersect_ratio_from_col=self.intersect_ratio_from_col,
            intersect_ratio_to_col=self.intersect_ratio_to_col,
            accuracy=self.accuracy,
        )
        # Generate a more descriptive name for composite keys
        from_cols_str = "_".join(self.from_columns)
        to_cols_str = "_".join(self.to_columns)
        relationship_name = f"{self.from_dataset}_{from_cols_str}_{self.to_dataset}_{to_cols_str}"

        relationship = Relationship(
            name=relationship_name,
            description="",
            source=source,
            target=target,
            type=RelationshipType.ONE_TO_MANY, # This might need to be determined more dynamically in the future
            profiling_metrics=profiling_metrics,
        )
        return relationship


class LinkPredictionResult(BaseModel):
    """
    The final output of the link prediction process, containing all discovered links.
    """

    links: List[PredictedLink]

    @property
    def relationships(self) -> list[Relationship]:
        return [link.relationship for link in self.links]

    def graph(self):
        if not self.relationships:
            raise errors.NotFoundError("No relationships found")
        ...
