import uuid

from typing import List, Optional

from pydantic import Field

from intugle.common.schema import NodeType, SchemaBase


class BaseResource(SchemaBase):
    name: str
    resource_type: NodeType
    description: str
    tags: Optional[List[str]] = None
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))