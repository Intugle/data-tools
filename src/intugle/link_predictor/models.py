from typing import List, Optional

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
    """
    Determines the cardinality and direction of a relationship between two datasets.

    Logic:
        - If both sides are unique (>= threshold): Relationship is 1:1.
        - If source is unique and target is not: Relationship is 1:M.
        - If source is not unique and target is unique: Relationship is M:1, but treated as 1:M
          by swapping source and target (Intugle standardizes on 1:M or M:M).
        - If neither is unique: Relationship is M:M.

    Args:
        from_dataset (str): Name of the source dataset.
        from_columns (List[str]): List of source column names.
        to_dataset (str): Name of the target dataset.
        to_columns (List[str]): List of target column names.
        from_uniqueness_ratio (Optional[float]): Uniqueness ratio for source columns (0.0 to 1.0).
        to_uniqueness_ratio (Optional[float]): Uniqueness ratio for target columns (0.0 to 1.0).

    Returns:
        tuple[str, List[str], str, List[str], RelationshipType]: A tuple containing:
            - source_table (str): The final source table name (may be swapped).
            - source_columns (List[str]): The final source columns (may be swapped).
            - target_table (str): The final target table name (may be swapped).
            - target_columns (List[str]): The final target columns (may be swapped).
            - rel_type (RelationshipType): The determined relationship type (1:1, 1:M, or M:M).
    """
    UNIQUENESS_THRESHOLD = 0.8

    from_is_unique = (from_uniqueness_ratio or 0) >= UNIQUENESS_THRESHOLD
    to_is_unique = (to_uniqueness_ratio or 0) >= UNIQUENESS_THRESHOLD

    source_table = from_dataset
    source_columns = from_columns
    target_table = to_dataset
    target_columns = to_columns

    if from_is_unique and to_is_unique:
        rel_type = RelationshipType.ONE_TO_ONE
        # In a 1:1, prefer the table with higher uniqueness as the source (PK)
        if (to_uniqueness_ratio or 0) >= (from_uniqueness_ratio or 0):
            source_table, target_table = target_table, source_table
            source_columns, target_columns = target_columns, source_columns
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
    Constructs the final profiling metrics for a relationship.

    If the `source_table` was swapped (i.e., it matches the `to_dataset` of the original link),
    the metrics (uniqueness ratios, intersect ratios) are also swapped to reflect the new direction.

    Args:
        link (PredictedLink): The original predicted link containing raw metrics.
        source_table (str): The name of the table determined to be the source.

    Returns:
        RelationshipProfilingMetrics: The adjusted profiling metrics for the relationship.
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
    def validate_columns(cls, value: str | List[str]) -> List[str]:
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
