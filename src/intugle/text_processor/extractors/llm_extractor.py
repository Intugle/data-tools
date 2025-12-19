"""
LLM-based extractor using LangChain infrastructure.

Uses the existing LangChain setup in intugle for entity and relationship extraction.
"""

import hashlib
import logging

from typing import List

from pydantic import BaseModel, Field

from intugle.text_processor.extractors.base import BaseExtractor
from intugle.text_processor.models import Entity, Relationship

log = logging.getLogger(__name__)


class ExtractedEntity(BaseModel):
    """Schema for LLM-extracted entity."""

    text: str = Field(..., description="The entity text as it appears in the document")
    label: str = Field(
        ...,
        description="Entity type: PERSON, ORGANIZATION, LOCATION, DATE, MONEY, PRODUCT, DOCUMENT, or OTHER",
    )
    normalized_id: str = Field(
        ..., description="A normalized identifier (e.g., 'Invoice_123' from 'Invoice 123')"
    )


class ExtractedRelationship(BaseModel):
    """Schema for LLM-extracted relationship."""

    subject: str = Field(..., description="The normalized_id of the subject entity")
    predicate: str = Field(
        ...,
        description="The relationship type in camelCase (e.g., 'hasAmount', 'issuedBy', 'locatedIn')",
    )
    object: str = Field(
        ..., description="The normalized_id of the object entity OR a literal value"
    )


class ExtractionResult(BaseModel):
    """Combined extraction result from LLM."""

    entities: List[ExtractedEntity] = Field(default_factory=list)
    relationships: List[ExtractedRelationship] = Field(default_factory=list)


class LLMExtractor(BaseExtractor):
    """
    LLM-based entity and relationship extractor.
    
    Uses LangChain structured output for reliable extraction.
    Supports multiple LLM providers via LLM_PROVIDER environment variable.
    """

    def __init__(self, model_name: str = "gpt-4o-mini"):
        """
        Initialize the LLM extractor.
        
        Args:
            model_name: Name of the LLM model to use.
        """
        self.model_name = model_name
        self._llm = None

    def _get_llm(self):
        """Lazy initialization of LLM based on provider."""
        if self._llm is None:
            import os
            provider = os.environ.get("LLM_PROVIDER", "openai").lower()
            
            if provider == "google-genai" or self.model_name.startswith("gemini"):
                from langchain_google_genai import ChatGoogleGenerativeAI
                model = self.model_name if self.model_name.startswith("gemini") else "gemini-2.5-flash"
                self._llm = ChatGoogleGenerativeAI(model=model, temperature=0)
            else:
                from langchain_openai import ChatOpenAI
                self._llm = ChatOpenAI(model=self.model_name, temperature=0)
                
        return self._llm

    def _generate_entity_id(self, text: str, label: str) -> str:
        """Generate a unique ID for an entity."""
        content = f"{label}:{text}".lower()
        return hashlib.md5(content.encode()).hexdigest()[:8]

    def extract_entities(self, text: str) -> List[Entity]:
        """Extract entities using LLM."""
        llm = self._get_llm()

        prompt = f"""Extract all named entities from the following text.
For each entity, identify:
- The exact text as it appears
- The entity type (PERSON, ORGANIZATION, LOCATION, DATE, MONEY, PRODUCT, DOCUMENT, or OTHER)
- A normalized identifier (convert spaces to underscores, remove special chars)

Text:
{text}

Extract entities:"""

        structured_llm = llm.with_structured_output(ExtractionResult)
        result: ExtractionResult = structured_llm.invoke(prompt)

        entities = []
        for ext in result.entities:
            entity = Entity(
                id=ext.normalized_id or self._generate_entity_id(ext.text, ext.label),
                text=ext.text,
                label=ext.label,
                confidence=0.9,
            )
            entities.append(entity)

        log.info(f"Extracted {len(entities)} entities from text")
        return entities

    def extract_relationships(
        self, text: str, entities: List[Entity]
    ) -> List[Relationship]:
        """Extract relationships between entities using LLM."""
        if not entities:
            return []

        llm = self._get_llm()

        entity_list = "\n".join([f"- {e.id} ({e.label}): {e.text}" for e in entities])

        prompt = f"""Given the following text and extracted entities, identify relationships between them.

Text:
{text}

Entities:
{entity_list}

For each relationship, specify:
- subject: The normalized_id of the subject entity
- predicate: The relationship type in camelCase (e.g., 'hasAmount', 'issuedBy', 'worksFor')
- object: The normalized_id of the object entity OR a literal value

Extract relationships:"""

        structured_llm = llm.with_structured_output(ExtractionResult)
        result: ExtractionResult = structured_llm.invoke(prompt)

        relationships = []
        {e.id for e in entities}

        for rel in result.relationships:
            relationship = Relationship(
                subject_id=rel.subject,
                predicate=rel.predicate,
                object_id=rel.object,
                confidence=0.85,
            )
            relationships.append(relationship)

        log.info(f"Extracted {len(relationships)} relationships from text")
        return relationships

    def extract_all(self, text: str) -> ExtractionResult:
        """
        Single-pass extraction of both entities and relationships.
        
        More efficient than separate calls as it uses one LLM invocation.
        """
        llm = self._get_llm()

        prompt = f"""Analyze the following text and extract:
1. All named entities (PERSON, ORGANIZATION, LOCATION, DATE, MONEY, PRODUCT, DOCUMENT, or OTHER)
2. All relationships between entities

For entities:
- text: The exact text as it appears
- label: The entity type
- normalized_id: A normalized identifier (e.g., 'Invoice_123' from 'Invoice 123')

For relationships:
- subject: The normalized_id of the subject entity
- predicate: The relationship type in camelCase (e.g., 'hasAmount', 'issuedBy')
- object: The normalized_id of the object entity OR a literal value

Text:
{text}

Extract:"""

        structured_llm = llm.with_structured_output(ExtractionResult)
        result: ExtractionResult = structured_llm.invoke(prompt)

        log.info(
            f"Single-pass extraction: {len(result.entities)} entities, "
            f"{len(result.relationships)} relationships"
        )
        return result
