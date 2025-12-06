from typing import Literal

from intugle.common.schema import SchemaBase


class DuckdbConfig(SchemaBase): 
    path: str
    type: Literal["csv", "parquet", "excel", "table"]
