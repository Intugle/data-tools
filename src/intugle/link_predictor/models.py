from typing import List, Optional

from pydantic import BaseModel

from intugle.common.exception import errors
from intugle.models.resources.relationship import (
    Relationship,
    RelationshipProfilingMetrics,
    RelationshipTable,
    RelationshipType,
)


class PredictedLink(BaseModel):
    """
    Represents a single predicted link between two columns from different datasets.
    """

    from_dataset: str
    from_column: str
    to_dataset: str
    to_column: str
    intersect_count: Optional[int] = None
    intersect_ratio_from_col: Optional[float] = None
    intersect_ratio_to_col: Optional[float] = None
    accuracy: Optional[float] = None

    @property
    def relationship(self) -> Relationship:
        source = RelationshipTable(table=self.from_dataset, column=self.from_column)
        target = RelationshipTable(table=self.to_dataset, column=self.to_column)
        profiling_metrics = RelationshipProfilingMetrics(
            intersect_count=self.intersect_count,
            intersect_ratio_from_col=self.intersect_ratio_from_col,
            intersect_ratio_to_col=self.intersect_ratio_to_col,
            accuracy=self.accuracy,
        )
        relationship = Relationship(
            name=f"{self.from_dataset}-{self.to_dataset}",
            description="",
            source=source,
            target=target,
            type=RelationshipType.ONE_TO_MANY,
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
        relationships: list[Relationship] = []
        for link in self.links:
            source = RelationshipTable(table=link.from_dataset, column=link.from_column)
            target = RelationshipTable(table=link.to_dataset, column=link.to_column)
            relationship = Relationship(
                name=f"{link.from_dataset}-{link.to_dataset}",
                description="",
                source=source,
                target=target,
                type=RelationshipType.ONE_TO_MANY,
            )

            relationships.append(relationship)

        return relationships

    def graph(self):
        if len(self.relationships) <= 0:
            raise errors.NotFoundError("No relationships found")

        ...
