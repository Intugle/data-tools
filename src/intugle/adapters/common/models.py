from pydantic import BaseModel


class ResolvedRelationship(BaseModel):
    """Represents a relationship with a clearly identified parent (one) and child (many) side."""

    parent_table: str
    parent_column: str
    child_table: str
    child_column: str
