from typing import Literal

from intugle.common.schema import SchemaBase


class SnowflakeConnectionConfig(SchemaBase):
    account: str
    user: str
    password: str
    role: str
    warehouse: str
    database: str
    schema: str
    type: str


class SnowflakeConfig(SchemaBase):
    identifier: str
    type: Literal["snowflake"] = "snowflake"
