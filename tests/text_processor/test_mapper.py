"""Tests for the SemanticMapper."""

from unittest.mock import MagicMock

from intugle.text_processor.mapper import MappingResult, SemanticMapper
from intugle.text_processor.models import Entity, RDFGraph


class TestSemanticMapper:
    def test_mapper_initialization(self):
        mapper = SemanticMapper()
        assert mapper.match_threshold == 0.85
        assert mapper.use_embeddings is False

    def test_mapper_custom_threshold(self):
        mapper = SemanticMapper(match_threshold=0.7)
        assert mapper.match_threshold == 0.7

    def test_string_similarity(self):
        mapper = SemanticMapper()
        
        # Exact match
        assert mapper._string_similarity("invoice", "invoice") == 1.0
        
        # Case insensitive
        assert mapper._string_similarity("Invoice", "invoice") == 1.0
        
        # Underscore vs space
        assert mapper._string_similarity("invoice_id", "invoice id") == 1.0
        
        # Partial match
        similarity = mapper._string_similarity("invoice", "invoices")
        assert 0.8 < similarity < 1.0

    def test_map_to_semantic_model_no_match(self):
        mapper = SemanticMapper(match_threshold=0.9)
        
        entity = Entity(id="random_entity", text="Random Thing", label="OTHER")
        graph = RDFGraph(entities=[entity])
        
        # Mock semantic model with no matching columns
        mock_model = MagicMock()
        mock_dataset = MagicMock()
        mock_column = MagicMock()
        mock_column.name = "unrelated_column"
        mock_dataset.source.table.columns = [mock_column]
        mock_model.datasets = {"table1": mock_dataset}
        
        results = mapper.map_to_semantic_model(graph, mock_model)
        
        assert len(results) == 1
        assert results[0].is_new is True
        assert results[0].matched_table is None

    def test_map_to_semantic_model_with_match(self):
        mapper = SemanticMapper(match_threshold=0.8)
        
        entity = Entity(id="customer_id", text="Customer ID", label="IDENTIFIER")
        graph = RDFGraph(entities=[entity])
        
        # Mock semantic model with matching column
        mock_model = MagicMock()
        mock_dataset = MagicMock()
        mock_column = MagicMock()
        mock_column.name = "customer_id"
        mock_dataset.source.table.columns = [mock_column]
        mock_model.datasets = {"customers": mock_dataset}
        
        results = mapper.map_to_semantic_model(graph, mock_model)
        
        assert len(results) == 1
        assert results[0].is_new is False
        assert results[0].matched_table == "customers"
        assert results[0].matched_column == "customer_id"
        assert results[0].confidence >= 0.8

    def test_suggest_new_nodes(self):
        mapper = SemanticMapper()
        
        entity = Entity(id="new_concept", text="New Concept", label="CONCEPT")
        result = MappingResult(entity=entity, is_new=True)
        
        suggestions = mapper.suggest_new_nodes([result])
        
        assert len(suggestions) == 1
        assert suggestions[0]["suggested_name"] == "new_concept"
        assert suggestions[0]["entity_type"] == "CONCEPT"

    def test_suggest_new_nodes_filters_matched(self):
        mapper = SemanticMapper()
        
        matched_entity = Entity(id="matched", text="Matched", label="TEST")
        new_entity = Entity(id="new", text="New", label="TEST")
        
        results = [
            MappingResult(entity=matched_entity, matched_table="t1", matched_column="c1", is_new=False),
            MappingResult(entity=new_entity, is_new=True),
        ]
        
        suggestions = mapper.suggest_new_nodes(results)
        
        # Only the new entity should be suggested
        assert len(suggestions) == 1
        assert suggestions[0]["suggested_name"] == "new"


class TestMappingResult:
    def test_to_dict(self):
        entity = Entity(id="test_id", text="Test", label="TEST")
        result = MappingResult(
            entity=entity,
            matched_table="table1",
            matched_column="col1",
            confidence=0.9,
            is_new=False,
        )
        
        d = result.to_dict()
        
        assert d["entity_id"] == "test_id"
        assert d["matched_table"] == "table1"
        assert d["confidence"] == 0.9
        assert d["is_new"] is False
