"""
RDF Graph Builder.

Constructs RDF triples from extracted entities and relationships.
"""

import logging

from typing import Any, Dict, List, Optional

from intugle.text_processor.models import Entity, RDFGraph, RDFTriple, Relationship

log = logging.getLogger(__name__)


class RDFBuilder:
    """
    Builds RDF graphs from extracted entities and relationships.
    
    Supports configurable ontology prefixes and RDF-star annotations.
    """

    DEFAULT_NAMESPACE = "http://intugle.ai/ontology/"
    
    # Standard predicates for entity properties
    PREDICATE_TYPE = "rdf:type"
    PREDICATE_LABEL = "rdfs:label"
    PREDICATE_VALUE = "hasValue"

    def __init__(
        self,
        namespace: Optional[str] = None,
        include_entity_triples: bool = True,
        include_provenance: bool = True,
    ):
        """
        Initialize the RDF builder.
        
        Args:
            namespace: Base namespace URI for generated entities.
            include_entity_triples: Whether to generate type/label triples for entities.
            include_provenance: Whether to include provenance metadata in triples.
        """
        self.namespace = namespace or self.DEFAULT_NAMESPACE
        self.include_entity_triples = include_entity_triples
        self.include_provenance = include_provenance

    def _make_uri(self, local_name: str) -> str:
        """Create a full URI from a local name."""
        # Clean the local name for URI usage
        clean_name = local_name.replace(" ", "_").replace("$", "").replace(",", "")
        return f"{self.namespace}{clean_name}"

    def _entity_to_triples(self, entity: Entity) -> List[RDFTriple]:
        """Generate RDF triples for an entity."""
        triples = []
        entity_uri = self._make_uri(entity.id)

        # Type triple
        triples.append(
            RDFTriple(
                subject=entity_uri,
                predicate=self._make_uri(self.PREDICATE_TYPE),
                object=self._make_uri(entity.label),
                object_type="uri",
                metadata={"confidence": entity.confidence} if self.include_provenance else {},
            )
        )

        # Label triple
        triples.append(
            RDFTriple(
                subject=entity_uri,
                predicate=self._make_uri(self.PREDICATE_LABEL),
                object=entity.text,
                object_type="literal",
                metadata={"confidence": entity.confidence} if self.include_provenance else {},
            )
        )

        # Additional attribute triples
        for attr_key, attr_value in entity.attributes.items():
            triples.append(
                RDFTriple(
                    subject=entity_uri,
                    predicate=self._make_uri(attr_key),
                    object=str(attr_value),
                    object_type="literal",
                )
            )

        return triples

    def _relationship_to_triple(
        self,
        relationship: Relationship,
        entities: Dict[str, Entity],
    ) -> RDFTriple:
        """Convert a relationship to an RDF triple."""
        subject_uri = self._make_uri(relationship.subject_id)
        predicate_uri = self._make_uri(relationship.predicate)

        # Check if object is an entity or a literal
        if relationship.object_id in entities:
            object_value = self._make_uri(relationship.object_id)
            object_type = "uri"
        else:
            # Treat as literal value
            object_value = relationship.object_id
            object_type = "literal"

        metadata = {}
        if self.include_provenance:
            metadata["confidence"] = relationship.confidence

        return RDFTriple(
            subject=subject_uri,
            predicate=predicate_uri,
            object=object_value,
            object_type=object_type,
            metadata=metadata,
        )

    def build(
        self,
        entities: List[Entity],
        relationships: List[Relationship],
        source_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RDFGraph:
        """
        Build an RDF graph from entities and relationships.
        
        Args:
            entities: List of extracted entities.
            relationships: List of extracted relationships.
            source_text: Original source text (for provenance).
            metadata: Additional graph-level metadata.
            
        Returns:
            RDFGraph containing all generated triples.
        """
        triples = []
        entity_map = {e.id: e for e in entities}

        # Generate entity triples
        if self.include_entity_triples:
            for entity in entities:
                triples.extend(self._entity_to_triples(entity))

        # Generate relationship triples
        for relationship in relationships:
            triple = self._relationship_to_triple(relationship, entity_map)
            triples.append(triple)

        graph = RDFGraph(
            entities=entities,
            relationships=relationships,
            triples=triples,
            source_text=source_text,
            metadata=metadata or {},
        )

        log.info(f"Built RDF graph with {len(triples)} triples")
        return graph
