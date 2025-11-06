from typing import Literal, Optional

from intugle.common.schema import SchemaBase


class DatabricksSQLConnectorConfig(SchemaBase):
    host: str
    http_path: str
    token: str
    schema: str
    catalog: Optional[str] = None


class DatabricksNotebookConfig(SchemaBase):
    schema: str
    catalog: Optional[str] = None


class DatabricksConfig(SchemaBase):
    identifier: str
    type: Literal["databricks"] = "databricks"
