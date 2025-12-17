from unittest.mock import MagicMock

from intugle.parser.table_schema import TableSchema


class MockColumn:
    def __init__(self, name, dtype, description):
        self.name = name
        self.type = dtype
        self.description = description


class MockTable:
    def __init__(self, name, description, columns):
        self.name = name
        self.description = description
        self.columns = columns


class MockTableDetail:
    def __init__(self, table):
        self.table = table


class MockRelationshipEnd:
    def __init__(self, table, columns):
        self.table = table
        self.columns = columns


class MockRelationship:
    def __init__(self, source_table, source_cols, target_table, target_cols):
        self.source = MockRelationshipEnd(source_table, source_cols)
        self.target = MockRelationshipEnd(target_table, target_cols)


def test_generate_table_schema():
    manifest = MagicMock()
    
    cols = [
        MockColumn("id", "INTEGER", "Primary Key"),
        MockColumn("username", "VARCHAR(255)", "User Name")
    ]
    user_table_detail = MockTableDetail(MockTable("users", "Users Table", cols))
    
    manifest.sources.get.return_value = user_table_detail

    rel = MockRelationship("users", ["role_id"], "roles", ["id"])
    manifest.relationships.values.return_value = [rel]

    schema_gen = TableSchema(manifest)

    sql = schema_gen.generate_table_schema("users")

    print("\nGenerated SQL:\n", sql) 
    
    assert "CREATE TABLE users" in sql
    assert "id INTEGER" in sql
    assert "username VARCHAR(255)" in sql
    assert "FOREIGN KEY (role_id) REFERENCES roles(id)" in sql