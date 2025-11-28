from typing import Literal

from pydantic import Field

from intugle.common.schema import SchemaBase


class SnowflakeConnectionConfig(SchemaBase):
    account: str
    user: str
    password: str
    role: str
    warehouse: str
    database: str
    schema_: str = Field(..., alias="schema")
    type: str


class SnowflakeConfig(SchemaBase):
    identifier: str
    type: Literal["snowflake"] = "snowflake"
