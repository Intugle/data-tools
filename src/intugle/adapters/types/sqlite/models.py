from typing import Literal

from intugle.common.schema import SchemaBase


class SqliteConfig(SchemaBase):
    identifier: str
    type: Literal["sqlite"] = "sqlite"
