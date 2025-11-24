from typing import Literal, Optional

from pydantic import Field

from intugle.common.schema import SchemaBase


class DatabricksSQLConnectorConfig(SchemaBase):
    host: str
    http_path: str
    token: str
    schema_: str = Field(..., alias="schema")
    catalog: Optional[str] = None


class DatabricksNotebookConfig(SchemaBase):
    schema_: str = Field(..., alias="schema")
    catalog: Optional[str] = None


class DatabricksConfig(SchemaBase):
    identifier: str
    type: Literal["databricks"] = "databricks"
