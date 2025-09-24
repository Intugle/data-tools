from enum import Enum

from pydantic import BaseModel, ConfigDict


class SchemaBase(BaseModel):
    """Base model configuration"""

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=True,
        validate_by_name=True
    )
    

class NodeType(str, Enum):
    MODEL = "model"
    RELATIONSHIP = "relationship"
    FEWSHOT = "fewshot"
    ANALYTICS_CATALOGUE = "analytics_catalogue"
    SOURCE = "source"


