"""
Pydantic models for RDF triples and graph representation.

Supports RDF-star annotations for provenance and confidence metadata.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Entity(BaseModel):
    """Represents an extracted entity from text."""

    id: str = Field(..., description="Unique identifier for the entity")
    text: str = Field(..., description="Original text of the entity")
    label: str = Field(..., description="Entity type/label (e.g., PERSON, ORG, MONEY)")
    start_char: Optional[int] = Field(None, description="Start character position in source text")
    end_char: Optional[int] = Field(None, description="End character position in source text")
    confidence: float = Field(1.0, description="Confidence score for the entity extraction")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Additional entity attributes")


class Relationship(BaseModel):
    """Represents a relationship between two entities."""

    subject_id: str = Field(..., description="ID of the subject entity")
    predicate: str = Field(..., description="Relationship type/predicate")
    object_id: str = Field(..., description="ID of the object entity")
    confidence: float = Field(1.0, description="Confidence score for the relationship")


class RDFTriple(BaseModel):
    """
    Represents an RDF triple (subject, predicate, object).
    
    Supports RDF-star annotations via the metadata field for provenance,
    confidence, and other contextual information.
    """

    subject: str = Field(..., description="Subject of the triple")
    predicate: str = Field(..., description="Predicate/relationship of the triple")
    object: str = Field(..., description="Object of the triple")
    object_type: str = Field("literal", description="Type of object: 'uri' or 'literal'")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="RDF-star annotations (provenance, confidence, source, etc.)",
    )

    def to_turtle(self) -> str:
        """Convert triple to Turtle format."""
        obj = f'"{self.object}"' if self.object_type == "literal" else f"<{self.object}>"
        return f"<{self.subject}> <{self.predicate}> {obj} ."

    def to_ntriples(self) -> str:
        """Convert triple to N-Triples format."""
        return self.to_turtle()


class RDFGraph(BaseModel):
    """
    Represents a collection of RDF triples forming a graph.
    
    Includes extracted entities, relationships, and the resulting triples.
    """

    entities: List[Entity] = Field(default_factory=list, description="Extracted entities")
    relationships: List[Relationship] = Field(default_factory=list, description="Extracted relationships")
    triples: List[RDFTriple] = Field(default_factory=list, description="RDF triples")
    source_text: Optional[str] = Field(None, description="Original source text")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Graph-level metadata (processing info, model used, etc.)",
    )

    def add_triple(
        self,
        subject: str,
        predicate: str,
        obj: str,
        object_type: str = "literal",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "RDFGraph":
        """Add a triple to the graph."""
        triple = RDFTriple(
            subject=subject,
            predicate=predicate,
            object=obj,
            object_type=object_type,
            metadata=metadata or {},
        )
        self.triples.append(triple)
        return self

    def get_entity_by_id(self, entity_id: str) -> Optional[Entity]:
        """Retrieve an entity by its ID."""
        for entity in self.entities:
            if entity.id == entity_id:
                return entity
        return None

    def to_turtle(self) -> str:
        """Export graph to Turtle format."""
        lines = ["@prefix ex: <http://example.org/> .", ""]
        for triple in self.triples:
            lines.append(triple.to_turtle())
        return "\n".join(lines)

    def to_json_ld(self) -> Dict[str, Any]:
        """Export graph to JSON-LD format."""
        return {
            "@context": {"ex": "http://example.org/"},
            "@graph": [
                {
                    "@id": t.subject,
                    t.predicate: {"@value": t.object} if t.object_type == "literal" else {"@id": t.object},
                }
                for t in self.triples
            ],
        }

    def to_dict(self) -> Dict[str, Any]:
        """Export graph as a dictionary."""
        return self.model_dump()
