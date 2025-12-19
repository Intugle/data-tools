"""
Main TextToSemanticProcessor class.

High-level orchestrator for converting unstructured text to RDF graphs.
"""

import logging
from typing import Any, Dict, Literal, Optional

from intugle.text_processor.models import Entity, RDFGraph, Relationship
from intugle.text_processor.extractors.base import BaseExtractor
from intugle.text_processor.extractors.llm_extractor import LLMExtractor
from intugle.text_processor.rdf.builder import RDFBuilder

log = logging.getLogger(__name__)


class TextToSemanticProcessor:
    """
    High-level orchestrator for converting unstructured text to RDF graphs.
    
    Provides a simple API for text-to-semantic conversion as specified in the
    feature requirements.
    
    Example:
        >>> processor = TextToSemanticProcessor(model="gpt-4o-mini", output_format="rdf_star")
        >>> rdf_graph = processor.parse(text_input)
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        output_format: Literal["rdf", "rdf_star"] = "rdf_star",
        extractor: Optional[BaseExtractor] = None,
        namespace: Optional[str] = None,
    ):
        """
        Initialize the text processor.
        
        Args:
            model: Name of the LLM model for extraction (e.g., 'gpt-4o-mini', 'en_core_web_lg').
            output_format: Output format - 'rdf' for standard RDF, 'rdf_star' for RDF with annotations.
            extractor: Optional custom extractor instance. If not provided, uses LLMExtractor.
            namespace: Base namespace URI for generated entities.
        """
        self.model = model
        self.output_format = output_format
        self.namespace = namespace

        # Use provided extractor or default to LLM-based
        if extractor is not None:
            self.extractor = extractor
        else:
            self.extractor = LLMExtractor(model_name=model)

        # Configure RDF builder based on output format
        include_provenance = output_format == "rdf_star"
        self.rdf_builder = RDFBuilder(
            namespace=namespace,
            include_provenance=include_provenance,
        )

        log.info(f"TextToSemanticProcessor initialized with model={model}, format={output_format}")

    def parse(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> RDFGraph:
        """
        Parse unstructured text and convert to an RDF graph.
        
        This is the main entry point for text-to-RDF conversion.
        
        Args:
            text: Input text to process (e.g., from OCR, documents, etc.).
            metadata: Optional metadata to include in the graph (e.g., source document ID).
            
        Returns:
            RDFGraph containing extracted entities, relationships, and triples.
        """
        log.info(f"Processing text of length {len(text)}")

        # Extract entities and relationships
        entities, relationships = self.extractor.extract(text)

        # Build RDF graph
        graph_metadata = metadata or {}
        graph_metadata["model"] = self.model
        graph_metadata["output_format"] = self.output_format

        rdf_graph = self.rdf_builder.build(
            entities=entities,
            relationships=relationships,
            source_text=text,
            metadata=graph_metadata,
        )

        log.info(
            f"Parsed text into RDF graph: {len(entities)} entities, "
            f"{len(relationships)} relationships, {len(rdf_graph.triples)} triples"
        )

        return rdf_graph

    def extract_entities(self, text: str) -> list[Entity]:
        """
        Extract only entities from text (no relationships).
        
        Args:
            text: Input text to process.
            
        Returns:
            List of extracted Entity objects.
        """
        return self.extractor.extract_entities(text)

    def extract_relationships(
        self, text: str, entities: list[Entity]
    ) -> list[Relationship]:
        """
        Extract relationships between known entities.
        
        Args:
            text: Input text to process.
            entities: Pre-extracted entities.
            
        Returns:
            List of extracted Relationship objects.
        """
        return self.extractor.extract_relationships(text, entities)

    def export_turtle(self, rdf_graph: RDFGraph) -> str:
        """Export RDF graph to Turtle format."""
        return rdf_graph.to_turtle()

    def export_json_ld(self, rdf_graph: RDFGraph) -> Dict[str, Any]:
        """Export RDF graph to JSON-LD format."""
        return rdf_graph.to_json_ld()
