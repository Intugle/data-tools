from typing import Literal

from pydantic import Field

from intugle.common.schema import SchemaBase


class SQLServerConnectionConfig(SchemaBase):
    user: str
    password: str
    host: str
    port: int = 1433
    database: str
    schema_: str = Field("dbo", alias="schema")
    encrypt: bool = True


class SQLServerConfig(SchemaBase):
    identifier: str
    type: Literal["sqlserver"] = "sqlserver"