"""
Semantic Mapper for aligning RDF graphs with SemanticModel.

Maps extracted entities and relationships to existing semantic nodes.
"""

import logging

from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from intugle.text_processor.models import Entity, RDFGraph

log = logging.getLogger(__name__)


class MappingResult:
    """Result of mapping an entity to a semantic node."""

    def __init__(
        self,
        entity: Entity,
        matched_table: Optional[str] = None,
        matched_column: Optional[str] = None,
        confidence: float = 0.0,
        is_new: bool = False,
    ):
        self.entity = entity
        self.matched_table = matched_table
        self.matched_column = matched_column
        self.confidence = confidence
        self.is_new = is_new

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity.id,
            "entity_text": self.entity.text,
            "entity_label": self.entity.label,
            "matched_table": self.matched_table,
            "matched_column": self.matched_column,
            "confidence": self.confidence,
            "is_new": self.is_new,
        }


class SemanticMapper:
    """
    Maps RDF graph entities to existing SemanticModel nodes.
    
    Uses string similarity and optional embeddings for matching.
    """

    def __init__(
        self,
        match_threshold: float = 0.85,
        use_embeddings: bool = False,
    ):
        """
        Initialize the semantic mapper.
        
        Args:
            match_threshold: Minimum similarity score for a match (0.0-1.0).
            use_embeddings: Whether to use embedding-based matching.
        """
        self.match_threshold = match_threshold
        self.use_embeddings = use_embeddings

    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity using SequenceMatcher."""
        s1_lower = s1.lower().replace("_", " ")
        s2_lower = s2.lower().replace("_", " ")
        return SequenceMatcher(None, s1_lower, s2_lower).ratio()

    def _find_best_match(
        self,
        entity: Entity,
        candidates: List[Tuple[str, str]],  # (table_name, column_name)
    ) -> Optional[Tuple[str, str, float]]:
        """
        Find the best matching candidate for an entity.
        
        Args:
            entity: The entity to match.
            candidates: List of (table_name, column_name) tuples to match against.
            
        Returns:
            Tuple of (table_name, column_name, confidence) or None if no match.
        """
        best_match = None
        best_score = 0.0

        for table_name, column_name in candidates:
            # Compare against column name
            score = self._string_similarity(entity.text, column_name)

            # Also try the entity ID
            id_score = self._string_similarity(entity.id, column_name)
            score = max(score, id_score)

            if score > best_score:
                best_score = score
                best_match = (table_name, column_name, score)

        if best_match and best_match[2] >= self.match_threshold:
            return best_match
        return None

    def map_to_semantic_model(
        self,
        rdf_graph: RDFGraph,
        semantic_model: Any,  # SemanticModel type
    ) -> List[MappingResult]:
        """
        Map RDF graph entities to a SemanticModel.
        
        Args:
            rdf_graph: The RDF graph to map.
            semantic_model: The target SemanticModel instance.
            
        Returns:
            List of MappingResult objects describing the mappings.
        """
        results = []

        # Extract candidate columns from semantic model datasets
        candidates = []
        for dataset_name, dataset in semantic_model.datasets.items():
            if hasattr(dataset, "source") and hasattr(dataset.source, "table"):
                for col in dataset.source.table.columns:
                    candidates.append((dataset_name, col.name))

        log.info(f"Mapping {len(rdf_graph.entities)} entities against {len(candidates)} candidates")

        for entity in rdf_graph.entities:
            match = self._find_best_match(entity, candidates)

            if match:
                table_name, column_name, confidence = match
                result = MappingResult(
                    entity=entity,
                    matched_table=table_name,
                    matched_column=column_name,
                    confidence=confidence,
                    is_new=False,
                )
                log.debug(
                    f"Matched entity '{entity.id}' to {table_name}.{column_name} "
                    f"(confidence: {confidence:.2f})"
                )
            else:
                result = MappingResult(
                    entity=entity,
                    is_new=True,
                )
                log.debug(f"No match found for entity '{entity.id}' - marked as new")

            results.append(result)

        matched = sum(1 for r in results if not r.is_new)
        log.info(f"Mapping complete: {matched}/{len(results)} entities matched")

        return results

    def suggest_new_nodes(
        self,
        mapping_results: List[MappingResult],
    ) -> List[Dict[str, Any]]:
        """
        Generate suggestions for new semantic nodes from unmapped entities.
        
        Args:
            mapping_results: Results from map_to_semantic_model.
            
        Returns:
            List of suggested new node definitions.
        """
        suggestions = []

        for result in mapping_results:
            if result.is_new:
                suggestion = {
                    "suggested_name": result.entity.id,
                    "entity_type": result.entity.label,
                    "original_text": result.entity.text,
                    "suggested_table_name": f"text_extracted_{result.entity.label.lower()}",
                }
                suggestions.append(suggestion)

        return suggestions
