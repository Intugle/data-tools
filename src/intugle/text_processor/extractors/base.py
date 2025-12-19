"""Base extractor interface for pluggable NLP backends."""

from abc import ABC, abstractmethod
from typing import List, Tuple

from intugle.text_processor.models import Entity, Relationship


class BaseExtractor(ABC):
    """
    Abstract base class for text extractors.
    
    Implementations should extract entities and relationships from text.
    """

    @abstractmethod
    def extract_entities(self, text: str) -> List[Entity]:
        """
        Extract named entities from text.
        
        Args:
            text: Input text to process.
            
        Returns:
            List of extracted Entity objects.
        """
        pass

    @abstractmethod
    def extract_relationships(
        self, text: str, entities: List[Entity]
    ) -> List[Relationship]:
        """
        Extract relationships between entities.
        
        Args:
            text: Input text to process.
            entities: Previously extracted entities.
            
        Returns:
            List of extracted Relationship objects.
        """
        pass

    def extract(self, text: str) -> Tuple[List[Entity], List[Relationship]]:
        """
        Full extraction pipeline: entities then relationships.
        
        Args:
            text: Input text to process.
            
        Returns:
            Tuple of (entities, relationships).
        """
        entities = self.extract_entities(text)
        relationships = self.extract_relationships(text, entities)
        return entities, relationships
