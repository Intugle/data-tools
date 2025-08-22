from data_tools.common.schema import SchemaBase


class DuckdbConfig(SchemaBase): 
    path: str
    type: str
