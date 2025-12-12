import pandas as pd

from intugle.nosql.parser import NoSQLParser


class TestNoSQLParser:
    def test_parser_init(self):
        """Test that the parser can be initialized."""
        parser = NoSQLParser()
        assert isinstance(parser, NoSQLParser)

    def test_flat_json(self):
        """Test parsing of a list of flat JSON objects."""
        parser = NoSQLParser()
        data = [{"a": 1}, {"a": 2}]
        dfs = parser.parse(data, root_table_name="root")
        
        assert isinstance(dfs, dict)
        assert "root" in dfs
        df = dfs["root"]
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "a" in df.columns
        assert df["a"].tolist() == [1, 2]

    def test_nested_object(self):
        """Test parsing of nested JSON objects (should be flattened)."""
        parser = NoSQLParser()
        data = [{"user": {"name": "Trevor", "age": 30}}]
        dfs = parser.parse(data, root_table_name="root")
        
        df = dfs["root"]
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        # json_normalize flattens by default with dot notation
        assert "user.name" in df.columns
        assert "user.age" in df.columns
        assert df["user.name"].iloc[0] == "Trevor"
        assert df["user.age"].iloc[0] == 30

    def test_mixed_flat_and_nested(self):
        """Test mixed flat and nested structures."""
        parser = NoSQLParser()
        data = [
            {"id": 1, "info": {"status": "active"}},
            {"id": 2, "info": {"status": "inactive"}}
        ]
        dfs = parser.parse(data, root_table_name="root")
        
        df = dfs["root"]
        assert len(df) == 2
        assert "id" in df.columns
        assert "info.status" in df.columns
        assert df["info.status"].tolist() == ["active", "inactive"]

    def test_empty_input(self):
        """Test parsing empty input."""
        parser = NoSQLParser()
        dfs = parser.parse([])
        assert dfs == {}

    # Phase 2 Tests

    def test_single_list_split(self):
        """Input {"id": 1, "items": [{"id": A}]}. Assert two tables exist: root and root_items."""
        parser = NoSQLParser()
        data = [{"id": 1, "items": [{"id": "A"}]}]
        dfs = parser.parse(data, root_table_name="root")

        assert "root" in dfs
        assert "root_items" in dfs
        
        root_df = dfs["root"]
        items_df = dfs["root_items"]
        
        assert len(root_df) == 1
        assert len(items_df) == 1
        assert items_df["id"].iloc[0] == "A"
        # Since 'items' was split out, it should NOT be in root (or should be removed)
        assert "items" not in root_df.columns

    def test_foreign_key_link(self):
        """Assert the row in root_items has a root_id column matching the parent."""
        parser = NoSQLParser()
        data = [{"_id": "parent_1", "items": [{"id": "child_1"}]}]
        dfs = parser.parse(data, root_table_name="root")
        
        items_df = dfs["root_items"]
        assert "root_id" in items_df.columns
        assert items_df["root_id"].iloc[0] == "parent_1"

    def test_deep_nesting(self):
        """Input {"a": [{"b": [{"c": 1}]}]}. Assert 3 tables are created."""
        parser = NoSQLParser()
        data = [{"val": "top", "a": [{"val": "mid", "b": [{"c": 1}]}]}]
        dfs = parser.parse(data, root_table_name="root")
        
        assert "root" in dfs
        assert "root_a" in dfs
        assert "root_a_b" in dfs
        
        assert len(dfs["root"]) == 1
        assert len(dfs["root_a"]) == 1
        assert len(dfs["root_a_b"]) == 1
        
        assert dfs["root_a_b"]["c"].iloc[0] == 1

    # Phase 5 Tests (Configuration)

    def test_table_renaming(self):
        """Assert output table name matches config."""
        config = {
            "table_renames": {
                "root_items": "order_lines"
            }
        }
        parser = NoSQLParser(config=config)
        data = [{"id": 1, "items": [{"id": "A"}]}]
        dfs = parser.parse(data, root_table_name="root")
        
        assert "root" in dfs
        assert "order_lines" in dfs
        assert "root_items" not in dfs
        assert len(dfs["order_lines"]) == 1

    def test_custom_pk(self):
        """Assert foreign keys use the user-defined PK column."""
        config = {
            "pk_overrides": {
                "root": "email"
            }
        }
        parser = NoSQLParser(config=config)
        data = [{"email": "user@example.com", "items": [{"item_id": 1}]}]
        dfs = parser.parse(data, root_table_name="root")
        
        items_df = dfs["root_items"]
        assert "root_id" in items_df.columns
        assert items_df["root_id"].iloc[0] == "user@example.com"
