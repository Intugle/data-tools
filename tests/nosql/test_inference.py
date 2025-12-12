from intugle.nosql.inference import identify_primary_key, infer_schema


class TestSchemaInference:
    def test_basic_types(self):
        data = [{"a": 1, "b": "text", "c": True}]
        schema = infer_schema(data)
        assert schema["a"] == "int"
        assert schema["b"] == "string"
        assert schema["c"] == "bool"

    def test_mixed_types(self):
        """Input mixed int/string. Assert schema result says "string"."""
        data = [{"a": 1}, {"a": "2"}]
        schema = infer_schema(data)
        assert schema["a"] == "string"

    def test_numeric_types(self):
        """Mixed int and float should become float."""
        data = [{"a": 1}, {"a": 2.5}]
        schema = infer_schema(data)
        assert schema["a"] == "float"

    def test_missing_fields(self):
        """Input [{"a": 1}, {"b": 2}]. Assert schema contains both columns a and b."""
        data = [{"a": 1}, {"b": 2}]
        schema = infer_schema(data)
        assert "a" in schema
        assert "b" in schema
        assert schema["a"] == "int"
        assert schema["b"] == "int"

    def test_null_values(self):
        """Nulls should be ignored for type determination."""
        data = [{"a": 1}, {"a": None}]
        schema = infer_schema(data)
        assert schema["a"] == "int"
        
        # All nulls -> string default
        data_null = [{"b": None}]
        schema_null = infer_schema(data_null)
        assert schema_null["b"] == "string"

    def test_pk_identification(self):
        """Test primary key identification."""
        schema = {"_id": "string", "name": "string"}
        pk = identify_primary_key(schema)
        assert pk == "_id"

        schema2 = {"id": "int", "val": "string"}
        pk2 = identify_primary_key(schema2)
        assert pk2 == "id"
        
        schema3 = {"val": "string"}
        pk3 = identify_primary_key(schema3)
        assert pk3 is None
