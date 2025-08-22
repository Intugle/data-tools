from pydantic import Field

from intugle.common.schema import SchemaBase
from intugle.models.resources.model import Model
from intugle.models.resources.relationship import Relationship
from intugle.models.resources.source import Source


class Manifest(SchemaBase):
    sources: dict[str, Source] = Field(default_factory=dict)
    models: dict[str, Model] = Field(default_factory=dict)
    relationships: dict[str, Relationship] = Field(default_factory=dict)
