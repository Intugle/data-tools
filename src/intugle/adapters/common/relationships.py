import re

from typing import Dict, Optional

from intugle.adapters.common.models import ResolvedRelationship
from intugle.models.resources.relationship import Relationship
from intugle.models.resources.source import Source


def clean_name(name: str) -> str:
    """Cleans a string to be a valid SQL identifier by replacing non-alphanumeric characters with underscores."""
    return re.sub(r'[^a-zA-Z0-9_]', '_', name)


def resolve_relationship_direction(
    rel: Relationship, sources: Dict[str, Source]
) -> Optional[ResolvedRelationship]:
    """
    Determines the direction of a relationship by identifying the primary key.

    Args:
        rel: The relationship object from the manifest.
        sources: A dictionary of all sources from the manifest.

    Returns:
        A ResolvedRelationship object with parent/child identified, or None if it's not a valid FK relationship.
    """
    source_table_info = sources.get(rel.source.table)
    target_table_info = sources.get(rel.target.table)

    if not source_table_info or not target_table_info:
        return None

    # Case 1: The source column is the primary key of the source table.
    # This means the target table is the child (many side).
    if source_table_info.table.key and source_table_info.table.key == rel.source.column:
        return ResolvedRelationship(
            parent_table=rel.source.table,
            parent_column=rel.source.column,
            child_table=rel.target.table,
            child_column=rel.target.column,
        )

    # Case 2: The target column is the primary key of the target table.
    # This means the source table is the child (many side).
    elif target_table_info.table.key and target_table_info.table.key == rel.target.column:
        return ResolvedRelationship(
            parent_table=rel.target.table,
            parent_column=rel.target.column,
            child_table=rel.source.table,
            child_column=rel.source.column,
        )

    # If neither side is a primary key, it's not a valid FK relationship for our purposes.
    return None
