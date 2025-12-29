from typing import Literal

from intugle.common.schema import SchemaBase


class MariaDBConnectionConfig(SchemaBase):
    user: str
    password: str
    host: str
    port: int = 3306
    database: str


class MariaDBConfig(SchemaBase):
    identifier: str
    type: Literal["mariadb"] = "mariadb"
