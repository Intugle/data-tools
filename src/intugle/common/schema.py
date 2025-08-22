from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class SchemaBase(BaseModel):
    """Base model configuration"""

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=True,
        validate_by_name=True
    )
    

class NodeType(StrEnum):
    MODEL = "model"
    RELATIONSHIP = "relationship"
    FEWSHOT = "fewshot"
    ANALYTICS_CATALOGUE = "analytics_catalogue"
    SOURCE = "source"


