from typing import Literal, Optional

from intugle.common.schema import SchemaBase


class SqliteConfig(SchemaBase):
    identifier: str
    path: Optional[str] = None
    type: Literal["sqlite"] = "sqlite"
