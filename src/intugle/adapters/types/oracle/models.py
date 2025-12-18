from typing import Literal, Optional

from pydantic import Field

from intugle.common.schema import SchemaBase


class OracleConnectionConfig(SchemaBase):
    user: str
    password: str
    host: str
    port: int = 1521
    service_name: Optional[str] = None
    sid: Optional[str] = None
    schema_: Optional[str] = Field(None, alias="schema")

    def model_post_init(self, __context):
        if not self.service_name and not self.sid:
            raise ValueError("Either 'service_name' or 'sid' must be provided.")


class OracleConfig(SchemaBase):
    identifier: str
    type: Literal["oracle"] = "oracle"
