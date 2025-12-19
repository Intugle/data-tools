"""Tests for the TextToSemanticProcessor."""

from unittest.mock import MagicMock

from intugle.text_processor.models import Entity, RDFGraph, Relationship
from intugle.text_processor.processor import TextToSemanticProcessor


class TestTextToSemanticProcessor:
    def test_processor_initialization(self):
        processor = TextToSemanticProcessor()
        assert processor.model == "gpt-4o-mini"
        assert processor.output_format == "rdf_star"

    def test_processor_custom_config(self):
        processor = TextToSemanticProcessor(
            model="gpt-4",
            output_format="rdf",
            namespace="http://custom.org/",
        )
        assert processor.model == "gpt-4"
        assert processor.output_format == "rdf"
        assert processor.rdf_builder.namespace == "http://custom.org/"

    def test_processor_with_mock_extractor(self):
        # Create mock extractor
        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = (
            [Entity(id="Invoice_123", text="Invoice 123", label="DOCUMENT")],
            [Relationship(subject_id="Invoice_123", predicate="hasAmount", object_id="5400")],
        )

        processor = TextToSemanticProcessor(extractor=mock_extractor)
        
        result = processor.parse("Invoice 123 for $5,400")
        
        mock_extractor.extract.assert_called_once()
        assert isinstance(result, RDFGraph)
        assert len(result.entities) == 1
        assert len(result.relationships) == 1

    def test_export_turtle(self):
        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = (
            [Entity(id="Test", text="Test", label="TEST")],
            [],
        )

        processor = TextToSemanticProcessor(extractor=mock_extractor)
        graph = processor.parse("Test text")
        
        turtle = processor.export_turtle(graph)
        assert "@prefix" in turtle
        assert "Test" in turtle

    def test_export_json_ld(self):
        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = (
            [Entity(id="Test", text="Test", label="TEST")],
            [],
        )

        processor = TextToSemanticProcessor(extractor=mock_extractor)
        graph = processor.parse("Test text")
        
        json_ld = processor.export_json_ld(graph)
        assert "@context" in json_ld
        assert "@graph" in json_ld

    def test_metadata_in_graph(self):
        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = ([], [])

        processor = TextToSemanticProcessor(
            model="test-model",
            output_format="rdf_star",
            extractor=mock_extractor,
        )
        
        graph = processor.parse("Test", metadata={"source": "test.txt"})
        
        assert graph.metadata["model"] == "test-model"
        assert graph.metadata["output_format"] == "rdf_star"
        assert graph.metadata["source"] == "test.txt"
