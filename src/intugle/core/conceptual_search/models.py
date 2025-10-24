from enum import Enum

from pydantic import BaseModel, Field


class Relevance_Classification(BaseModel):
    relevance_score: int = Field(
        description="describes how relevant the column is, the higher the number the more relevant",
        enum=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    )


class QdrantCollectionSuffix(str, Enum):
    TABLE = "_table_shortlisting"
    FIELD = "_field_shortlisting"

    def __repr__(
        self,
    ):
        return str(self.value)


class GraphFileName(str, Enum):
    TABLE = "table_graph.gpickle"
    FIELD = "field_graph.gpickle"

    def __repr__(
        self,
    ):
        return str(self.value)
