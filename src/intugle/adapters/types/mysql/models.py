from typing import Literal

from intugle.common.schema import SchemaBase


class MySQLConnectionConfig(SchemaBase):
    user: str
    password: str
    host: str
    port: int = 3306
    database: str


class MySQLConfig(SchemaBase):
    identifier: str
    type: Literal["mysql"] = "mysql"
