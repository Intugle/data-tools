from typing import Literal

from pydantic import Field

from intugle.common.schema import SchemaBase


class RedshiftConnectionConfig(SchemaBase):
    user: str
    password: str
    host: str
    port: int = 5439  # Default Redshift port
    database: str
    schema_: str = Field(..., alias="schema")


class RedshiftConfig(SchemaBase):
    identifier: str
    type: Literal["redshift"] = "redshift"
