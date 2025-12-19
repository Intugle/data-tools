"""Tests for the RDF Builder."""

import pytest
from intugle.text_processor.models import Entity, Relationship
from intugle.text_processor.rdf.builder import RDFBuilder


class TestRDFBuilder:
    def test_builder_initialization(self):
        builder = RDFBuilder()
        assert builder.namespace == RDFBuilder.DEFAULT_NAMESPACE
        assert builder.include_entity_triples is True
        assert builder.include_provenance is True

    def test_builder_custom_namespace(self):
        builder = RDFBuilder(namespace="http://custom.org/")
        assert builder.namespace == "http://custom.org/"

    def test_build_empty(self):
        builder = RDFBuilder()
        graph = builder.build(entities=[], relationships=[])
        assert len(graph.triples) == 0
        assert len(graph.entities) == 0

    def test_build_with_entities(self):
        builder = RDFBuilder()
        entities = [
            Entity(id="Invoice_123", text="Invoice 123", label="DOCUMENT"),
            Entity(id="Vendor_A", text="Vendor A", label="ORGANIZATION"),
        ]
        graph = builder.build(entities=entities, relationships=[])
        
        # Each entity should produce type and label triples
        assert len(graph.triples) == 4  # 2 entities x 2 triples each
        assert len(graph.entities) == 2

    def test_build_with_relationships(self):
        builder = RDFBuilder()
        entities = [
            Entity(id="Invoice_123", text="Invoice 123", label="DOCUMENT"),
            Entity(id="Vendor_A", text="Vendor A", label="ORGANIZATION"),
        ]
        relationships = [
            Relationship(
                subject_id="Invoice_123",
                predicate="issuedBy",
                object_id="Vendor_A",
            )
        ]
        graph = builder.build(entities=entities, relationships=relationships)
        
        # 4 entity triples + 1 relationship triple
        assert len(graph.triples) == 5
        assert len(graph.relationships) == 1

    def test_build_with_literal_object(self):
        builder = RDFBuilder()
        entities = [
            Entity(id="Invoice_123", text="Invoice 123", label="DOCUMENT"),
        ]
        relationships = [
            Relationship(
                subject_id="Invoice_123",
                predicate="hasAmount",
                object_id="5400",  # Not an entity ID, should be treated as literal
            )
        ]
        graph = builder.build(entities=entities, relationships=relationships)
        
        # Find the hasAmount triple
        amount_triple = None
        for t in graph.triples:
            if "hasAmount" in t.predicate:
                amount_triple = t
                break
        
        assert amount_triple is not None
        assert amount_triple.object_type == "literal"

    def test_build_without_entity_triples(self):
        builder = RDFBuilder(include_entity_triples=False)
        entities = [
            Entity(id="Invoice_123", text="Invoice 123", label="DOCUMENT"),
        ]
        relationships = [
            Relationship(
                subject_id="Invoice_123",
                predicate="hasAmount",
                object_id="5400",
            )
        ]
        graph = builder.build(entities=entities, relationships=relationships)
        
        # Only the relationship triple, no entity type/label triples
        assert len(graph.triples) == 1

    def test_provenance_metadata(self):
        builder = RDFBuilder(include_provenance=True)
        entities = [
            Entity(id="Test", text="Test", label="TEST", confidence=0.95),
        ]
        graph = builder.build(entities=entities, relationships=[])
        
        # Check that confidence is in metadata
        assert graph.triples[0].metadata.get("confidence") == 0.95

    def test_no_provenance_metadata(self):
        builder = RDFBuilder(include_provenance=False)
        entities = [
            Entity(id="Test", text="Test", label="TEST", confidence=0.95),
        ]
        graph = builder.build(entities=entities, relationships=[])
        
        # Metadata should be empty
        assert graph.triples[0].metadata == {}
