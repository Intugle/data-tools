from typing import Literal

from pydantic import Field

from intugle.common.schema import SchemaBase


class MySQLConnectionConfig(SchemaBase):
    user: str
    password: str
    host: str
    port: int = 3306
    database: str
    schema_: str = Field(..., alias="schema")


class MySQLConfig(SchemaBase):
    identifier: str
    type: Literal["mysql"] = "mysql"
