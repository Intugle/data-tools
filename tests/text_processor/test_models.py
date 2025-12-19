"""Tests for text processor Pydantic models."""

from intugle.text_processor.models import Entity, RDFGraph, RDFTriple, Relationship


class TestEntity:
    def test_entity_creation(self):
        entity = Entity(id="Invoice_123", text="Invoice 123", label="DOCUMENT")
        assert entity.id == "Invoice_123"
        assert entity.text == "Invoice 123"
        assert entity.label == "DOCUMENT"
        assert entity.confidence == 1.0

    def test_entity_with_attributes(self):
        entity = Entity(
            id="Amount_5400",
            text="$5,400",
            label="MONEY",
            attributes={"currency": "USD", "value": 5400},
        )
        assert entity.attributes["currency"] == "USD"
        assert entity.attributes["value"] == 5400


class TestRelationship:
    def test_relationship_creation(self):
        rel = Relationship(
            subject_id="Invoice_123",
            predicate="hasAmount",
            object_id="Amount_5400",
        )
        assert rel.subject_id == "Invoice_123"
        assert rel.predicate == "hasAmount"
        assert rel.object_id == "Amount_5400"
        assert rel.confidence == 1.0


class TestRDFTriple:
    def test_triple_creation(self):
        triple = RDFTriple(
            subject="http://example.org/Invoice_123",
            predicate="http://example.org/hasAmount",
            object="5400",
            object_type="literal",
        )
        assert triple.subject == "http://example.org/Invoice_123"
        assert triple.object_type == "literal"

    def test_triple_to_turtle(self):
        triple = RDFTriple(
            subject="http://example.org/Invoice_123",
            predicate="http://example.org/hasAmount",
            object="5400",
            object_type="literal",
        )
        turtle = triple.to_turtle()
        assert "<http://example.org/Invoice_123>" in turtle
        assert '"5400"' in turtle

    def test_triple_with_uri_object(self):
        triple = RDFTriple(
            subject="http://example.org/Invoice_123",
            predicate="http://example.org/issuedBy",
            object="http://example.org/Vendor_A",
            object_type="uri",
        )
        turtle = triple.to_turtle()
        assert "<http://example.org/Vendor_A>" in turtle


class TestRDFGraph:
    def test_graph_creation(self):
        graph = RDFGraph()
        assert len(graph.entities) == 0
        assert len(graph.triples) == 0

    def test_add_triple(self):
        graph = RDFGraph()
        graph.add_triple(
            subject="http://example.org/Invoice_123",
            predicate="http://example.org/hasAmount",
            obj="5400",
        )
        assert len(graph.triples) == 1

    def test_to_turtle(self):
        graph = RDFGraph()
        graph.add_triple(
            subject="http://example.org/Invoice_123",
            predicate="http://example.org/hasAmount",
            obj="5400",
        )
        turtle = graph.to_turtle()
        assert "@prefix" in turtle
        assert "http://example.org/Invoice_123" in turtle

    def test_to_json_ld(self):
        graph = RDFGraph()
        graph.add_triple(
            subject="http://example.org/Invoice_123",
            predicate="http://example.org/hasAmount",
            obj="5400",
        )
        json_ld = graph.to_json_ld()
        assert "@context" in json_ld
        assert "@graph" in json_ld
        assert len(json_ld["@graph"]) == 1

    def test_get_entity_by_id(self):
        entity = Entity(id="test_id", text="Test", label="TEST")
        graph = RDFGraph(entities=[entity])
        found = graph.get_entity_by_id("test_id")
        assert found is not None
        assert found.text == "Test"
        
        not_found = graph.get_entity_by_id("nonexistent")
        assert not_found is None
