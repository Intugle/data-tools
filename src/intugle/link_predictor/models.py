from typing import List, Optional, Union

from pydantic import BaseModel, field_validator

from intugle.common.exception import errors
from intugle.models.resources.relationship import (
    Relationship,
    RelationshipProfilingMetrics,
    RelationshipTable,
    RelationshipType,
)


def _determine_relationship_cardinality(
    from_dataset: str,
    from_columns: List[str],
    to_dataset: str,
    to_columns: List[str],
    from_uniqueness_ratio: Optional[float],
    to_uniqueness_ratio: Optional[float],
) -> tuple[str, List[str], str, List[str], RelationshipType]:
    """Determines relationship type and swaps source/target for M:1 cases."""
    UNIQUENESS_THRESHOLD = 0.8

    from_is_unique = (from_uniqueness_ratio or 0) >= UNIQUENESS_THRESHOLD
    to_is_unique = (to_uniqueness_ratio or 0) >= UNIQUENESS_THRESHOLD

    source_table = from_dataset
    source_columns = from_columns
    target_table = to_dataset
    target_columns = to_columns

    if from_is_unique and to_is_unique:
        rel_type = RelationshipType.ONE_TO_ONE
    elif from_is_unique and not to_is_unique:
        rel_type = RelationshipType.ONE_TO_MANY
    elif not from_is_unique and to_is_unique:
        rel_type = RelationshipType.ONE_TO_MANY  # Treat M:1 as 1:M by swapping
        source_table, target_table = target_table, source_table
        source_columns, target_columns = target_columns, source_columns
    else:  # not from_is_unique and not to_is_unique
        rel_type = RelationshipType.MANY_TO_MANY

    return source_table, source_columns, target_table, target_columns, rel_type


def _get_final_profiling_metrics(
    link: "PredictedLink",
    source_table: str,
) -> RelationshipProfilingMetrics:
    """
    Returns the final profiling metrics, swapping them if the source table
    was changed during cardinality determination (i.e., a M:1 was treated as 1:M).
    """
    # If the final source_table is the original to_dataset, it means a swap happened.
    if source_table == link.to_dataset:
        return RelationshipProfilingMetrics(
            intersect_count=link.intersect_count,
            intersect_ratio_from_col=link.intersect_ratio_to_col,
            intersect_ratio_to_col=link.intersect_ratio_from_col,
            accuracy=link.accuracy,
            from_uniqueness_ratio=link.to_uniqueness_ratio,
            to_uniqueness_ratio=link.from_uniqueness_ratio,
        )
    # Otherwise, no swap occurred, so use the original metrics.
    return RelationshipProfilingMetrics(
        intersect_count=link.intersect_count,
        intersect_ratio_from_col=link.intersect_ratio_from_col,
        intersect_ratio_to_col=link.intersect_ratio_to_col,
        accuracy=link.accuracy,
        from_uniqueness_ratio=link.from_uniqueness_ratio,
        to_uniqueness_ratio=link.to_uniqueness_ratio,
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
    from_uniqueness_ratio: Optional[float] = None
    to_uniqueness_ratio: Optional[float] = None
    accuracy: Optional[float] = None

    @field_validator("from_columns", "to_columns", mode="before")
    @classmethod
    def validate_columns(cls, value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, str):
            return [value]
        return value

    @property
    def relationship(self) -> Relationship:
        source_table, source_columns, target_table, target_columns, rel_type = (
            _determine_relationship_cardinality(
                self.from_dataset,
                self.from_columns,
                self.to_dataset,
                self.to_columns,
                self.from_uniqueness_ratio,
                self.to_uniqueness_ratio,
            )
        )

        source = RelationshipTable(table=source_table, columns=source_columns)
        target = RelationshipTable(table=target_table, columns=target_columns)
        profiling_metrics = _get_final_profiling_metrics(self, source_table)

        # Generate a more descriptive name for composite keys using the final source/target
        source_cols_str = "_".join(source_columns)
        target_cols_str = "_".join(target_columns)
        relationship_name = (
            f"{source_table}_{source_cols_str}_{target_table}_{target_cols_str}"
        )

        relationship = Relationship(
            name=relationship_name,
            description="",
            source=source,
            target=target,
            type=rel_type,
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
