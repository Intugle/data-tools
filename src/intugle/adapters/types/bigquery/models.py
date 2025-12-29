from typing import Literal, Optional

from pydantic import Field

from intugle.common.schema import SchemaBase


class BigQueryConnectionConfig(SchemaBase):
    project_id: str
    dataset_id: str = Field(..., alias="dataset")
    credentials_path: Optional[str] = None
    location: str = "US"


class BigQueryConfig(SchemaBase):
    identifier: str
    type: Literal["bigquery"] = "bigquery"
