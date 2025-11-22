from typing import Literal

from intugle.common.schema import SchemaBase


class SqliteConfig(SchemaBase):
    identifier: str
    path: str
    type: Literal["sqlite"] = "sqlite"
