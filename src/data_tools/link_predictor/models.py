from typing import List

from pydantic import BaseModel


class PredictedLink(BaseModel):
    """
    Represents a single predicted link between two columns from different datasets.
    """
    from_dataset: str
    from_column: str
    to_dataset: str
    to_column: str


class LinkPredictionResult(BaseModel):
    """
    The final output of the link prediction process, containing all discovered links.
    """
    links: List[PredictedLink]
