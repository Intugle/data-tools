from typing import Literal

from intugle.common.schema import SchemaBase


class PostgresConnectionConfig(SchemaBase):
    user: str
    password: str
    host: str
    port: int = 5432
    database: str
    schema: str


class PostgresConfig(SchemaBase):
    identifier: str
    type: Literal["postgres"] = "postgres"
