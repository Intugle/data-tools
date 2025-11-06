from typing import Literal, Optional

from intugle.common.schema import SchemaBase


class SQLServerConnectionConfig(SchemaBase):
    user: str
    password: str
    host: str
    port: int = 1433
    database: str
    schema: str = "dbo"
    encrypt: bool = True


class SQLServerConfig(SchemaBase):
    identifier: str
    type: Literal["sqlserver"] = "sqlserver"