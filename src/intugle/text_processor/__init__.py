"""
Unstructured Text Processor Module.

Provides functionality to convert unstructured text into RDF triples
and map them to the existing Semantic Model.
"""

from intugle.text_processor.processor import TextToSemanticProcessor
from intugle.text_processor.models import RDFTriple, RDFGraph, Entity, Relationship

__all__ = [
    "TextToSemanticProcessor",
    "RDFTriple",
    "RDFGraph",
    "Entity",
    "Relationship",
]
