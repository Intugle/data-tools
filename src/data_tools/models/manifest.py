from pydantic import Field

from data_tools.common.schema import SchemaBase
from data_tools.models.resources.model import Model
from data_tools.models.resources.relationship import Relationship
from data_tools.models.resources.source import Source


class Manifest(SchemaBase):
    sources: dict[str, Source] = Field(default_factory=dict)
    models: dict[str, Model] = Field(default_factory=dict)
    relationships: dict[str, Relationship] = Field(default_factory=dict)
