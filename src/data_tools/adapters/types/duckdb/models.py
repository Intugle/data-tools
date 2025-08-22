from intugle.common.schema import SchemaBase


class DuckdbConfig(SchemaBase): 
    path: str
    type: str
