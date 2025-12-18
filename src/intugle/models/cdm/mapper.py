"""Ontology Mapper for mapping semantic models to CDM entities."""

import json
import logging
import os

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import Field

from intugle.common.schema import SchemaBase
from intugle.models.cdm.catalog import CDMCatalog
from intugle.models.cdm.ontology import BusinessOntology

log = logging.getLogger(__name__)


class MappingStatus(str, Enum):
    """Status of a mapping."""
    PROPOSED = "proposed"
    APPROVED = "approved"
    DEPRECATED = "deprecated"
    IN_REVIEW = "in_review"


class MappingType(str, Enum):
    """Type of mapping between semantic and CDM."""
    ONE_TO_ONE = "one_to_one"  # One semantic entity -> One CDM entity
    MANY_TO_ONE = "many_to_one"  # Multiple semantic entities -> One CDM entity
    ONE_TO_MANY = "one_to_many"  # One semantic entity -> Multiple CDM entities
    COMPOSITE = "composite"  # Complex mapping with transformations


class AttributeMapping(SchemaBase):
    """
    Represents a mapping between a semantic attribute and a CDM attribute.
    
    Attributes:
        semantic_attribute: Name of the attribute in the semantic model.
        cdm_attribute: Full path to the CDM attribute (e.g., "Contact.Email").
        transformation: Optional transformation logic or description.
        confidence: Confidence score for the mapping (0.0 to 1.0).
        notes: Additional notes about the mapping.
        metadata: Additional custom metadata.
    """
    
    semantic_attribute: str
    cdm_attribute: str
    transformation: Optional[str] = None
    confidence: float = 1.0
    notes: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def __str__(self) -> str:
        return f"AttributeMapping({self.semantic_attribute} -> {self.cdm_attribute})"


class EntityMapping(SchemaBase):
    """
    Represents a mapping between semantic model entities and business concepts/CDM entities.
    
    Attributes:
        semantic_entities: List of semantic entity names (tables/objects).
        concept_name: Name of the business concept this maps to.
        cdm_entity_name: Name of the CDM entity.
        cdm_namespace: CDM namespace for the entity.
        mapping_type: Type of mapping (one-to-one, many-to-one, etc.).
        attribute_mappings: List of attribute-level mappings.
        status: Current status of the mapping.
        confidence: Confidence score for the mapping (0.0 to 1.0).
        owner: Mapping owner or steward.
        notes: Additional notes about the mapping.
        metadata: Additional custom metadata.
    """
    
    semantic_entities: List[str]
    concept_name: str
    cdm_entity_name: Optional[str] = None
    cdm_namespace: Optional[str] = None
    mapping_type: MappingType = MappingType.ONE_TO_ONE
    attribute_mappings: List[AttributeMapping] = Field(default_factory=list)
    status: MappingStatus = MappingStatus.PROPOSED
    confidence: float = 1.0
    owner: Optional[str] = None
    notes: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_attribute_mapping(
        self,
        semantic_attribute: str,
        cdm_attribute: str,
        transformation: Optional[str] = None,
        confidence: float = 1.0
    ) -> None:
        """
        Add an attribute mapping to this entity mapping.
        
        Args:
            semantic_attribute: Name of the semantic attribute.
            cdm_attribute: Full CDM attribute path.
            transformation: Optional transformation description.
            confidence: Confidence score (0.0 to 1.0).
        """
        mapping = AttributeMapping(
            semantic_attribute=semantic_attribute,
            cdm_attribute=cdm_attribute,
            transformation=transformation,
            confidence=confidence
        )
        self.attribute_mappings.append(mapping)

    def __str__(self) -> str:
        entities_str = ", ".join(self.semantic_entities)
        return f"EntityMapping({entities_str} -> {self.concept_name})"


class OntologyMapper:
    """
    Maps semantic model entities and attributes to business concepts and CDM entities.
    
    The OntologyMapper is the bridge between the technical semantic model and the
    business ontology layer. It maintains mappings at both entity and attribute levels.
    
    Attributes:
        semantic_model: Reference to the SemanticModel (can be dict for flexibility).
        business_ontology: The BusinessOntology being mapped to.
        cdm_catalog: The CDM catalog for entity/attribute references.
        mappings: Dictionary of entity mappings keyed by concept name.
    """
    
    def __init__(
        self,
        semantic_model: Any,  # Can be SemanticModel or dict representation
        business_ontology: BusinessOntology,
        cdm_catalog: Optional[CDMCatalog] = None
    ):
        self.semantic_model = semantic_model
        self.business_ontology = business_ontology
        self.cdm_catalog = cdm_catalog
        self.mappings: Dict[str, EntityMapping] = {}

    def map_entity(
        self,
        semantic_entity: Union[str, List[str]],
        concept: str,
        attribute_map: Optional[Dict[str, str]] = None,
        mapping_type: Optional[MappingType] = None,
        status: MappingStatus = MappingStatus.PROPOSED,
        **kwargs
    ) -> EntityMapping:
        """
        Create a mapping between semantic entity/entities and a business concept.
        
        Args:
            semantic_entity: Name(s) of the semantic entity/entities (table names).
            concept: Name of the business concept to map to.
            attribute_map: Dictionary mapping semantic attributes to CDM attributes.
                          Format: {"semantic_col": "CDMEntity.CDMAttribute"}
            mapping_type: Type of mapping. Auto-detected if not provided.
            status: Status of the mapping.
            **kwargs: Additional metadata for the mapping.
            
        Returns:
            The created EntityMapping.
            
        Raises:
            ValueError: If the concept doesn't exist in the ontology.
        """
        # Normalize semantic_entity to list
        if isinstance(semantic_entity, str):
            semantic_entities = [semantic_entity]
        else:
            semantic_entities = semantic_entity
        
        # Validate concept exists
        business_concept = self.business_ontology.get_concept(concept)
        if not business_concept:
            raise ValueError(
                f"Business concept '{concept}' not found in ontology. "
                f"Available concepts: {self.business_ontology.list_concepts()}"
            )
        
        # Auto-detect mapping type if not provided
        if mapping_type is None:
            if len(semantic_entities) == 1:
                mapping_type = MappingType.ONE_TO_ONE
            else:
                mapping_type = MappingType.MANY_TO_ONE
        
        # Extract known parameters from kwargs
        confidence = kwargs.pop('confidence', 1.0)
        owner = kwargs.pop('owner', None)
        notes = kwargs.pop('notes', None)
        
        # Create the entity mapping
        entity_mapping = EntityMapping(
            semantic_entities=semantic_entities,
            concept_name=concept,
            cdm_entity_name=business_concept.cdm_entity_name,
            cdm_namespace=business_concept.cdm_namespace,
            mapping_type=mapping_type,
            status=status,
            confidence=confidence,
            owner=owner,
            notes=notes,
            metadata=kwargs  # Remaining kwargs go to metadata
        )
        
        # Add attribute mappings if provided
        if attribute_map:
            for semantic_attr, cdm_attr in attribute_map.items():
                entity_mapping.add_attribute_mapping(semantic_attr, cdm_attr)
        
        # Store the mapping
        self.mappings[concept] = entity_mapping
        log.info(
            f"Mapped semantic entities {semantic_entities} to concept '{concept}' "
            f"(CDM: {business_concept.cdm_entity_name})"
        )
        
        return entity_mapping

    def get_mapping(self, concept_name: str) -> Optional[EntityMapping]:
        """
        Get the entity mapping for a specific concept.
        
        Args:
            concept_name: Name of the business concept.
            
        Returns:
            The EntityMapping if found, None otherwise.
        """
        return self.mappings.get(concept_name)

    def get_mappings_by_semantic_entity(self, entity_name: str) -> List[EntityMapping]:
        """
        Get all mappings that include a specific semantic entity.
        
        Args:
            entity_name: Name of the semantic entity.
            
        Returns:
            List of EntityMapping objects that reference this entity.
        """
        return [
            mapping for mapping in self.mappings.values()
            if entity_name in mapping.semantic_entities
        ]

    def get_mappings_by_cdm_entity(self, cdm_entity_name: str) -> List[EntityMapping]:
        """
        Get all mappings that target a specific CDM entity.
        
        Args:
            cdm_entity_name: Name of the CDM entity.
            
        Returns:
            List of EntityMapping objects that map to this CDM entity.
        """
        return [
            mapping for mapping in self.mappings.values()
            if mapping.cdm_entity_name == cdm_entity_name
        ]

    def get_unmapped_semantic_entities(self) -> List[str]:
        """
        Get list of semantic entities that are not yet mapped to any concept.
        
        Returns:
            List of unmapped semantic entity names.
        """
        # Get all semantic entities from the model
        if hasattr(self.semantic_model, 'datasets'):
            all_entities = list(self.semantic_model.datasets.keys())
        elif isinstance(self.semantic_model, dict):
            all_entities = list(self.semantic_model.keys())
        else:
            return []
        
        # Get all mapped entities
        mapped_entities = set()
        for mapping in self.mappings.values():
            mapped_entities.update(mapping.semantic_entities)
        
        # Return unmapped
        return [entity for entity in all_entities if entity not in mapped_entities]

    def get_unmapped_cdm_entities(self) -> List[str]:
        """
        Get list of CDM entities in the catalog that are not yet mapped.
        
        Returns:
            List of unmapped CDM entity names.
        """
        if not self.cdm_catalog:
            return []
        
        all_cdm_entities = set(self.cdm_catalog.list_entities())
        mapped_cdm_entities = {
            mapping.cdm_entity_name
            for mapping in self.mappings.values()
            if mapping.cdm_entity_name
        }
        
        return list(all_cdm_entities - mapped_cdm_entities)

    def validate_mappings(self) -> Dict[str, List[str]]:
        """
        Validate all mappings and return any issues found.
        
        Returns:
            Dictionary of validation issues grouped by type.
        """
        issues: Dict[str, List[str]] = {
            "missing_concepts": [],
            "missing_cdm_entities": [],
            "missing_semantic_entities": [],
            "attribute_issues": []
        }
        
        for concept_name, mapping in self.mappings.items():
            # Check if concept exists
            if not self.business_ontology.get_concept(concept_name):
                issues["missing_concepts"].append(
                    f"Mapping references non-existent concept: {concept_name}"
                )
            
            # Check if CDM entity exists in catalog
            if self.cdm_catalog and mapping.cdm_entity_name:
                if not self.cdm_catalog.get_entity(mapping.cdm_entity_name):
                    issues["missing_cdm_entities"].append(
                        f"Mapping references non-existent CDM entity: {mapping.cdm_entity_name}"
                    )
            
            # Check if semantic entities exist
            if hasattr(self.semantic_model, 'datasets'):
                for semantic_entity in mapping.semantic_entities:
                    if semantic_entity not in self.semantic_model.datasets:
                        issues["missing_semantic_entities"].append(
                            f"Mapping references non-existent semantic entity: {semantic_entity}"
                        )
        
        return {k: v for k, v in issues.items() if v}

    def export_mappings(self, file_path: str) -> None:
        """
        Export all mappings to a JSON file.
        
        Args:
            file_path: Path where the mappings should be saved.
        """
        mappings_data = {
            "ontology_name": self.business_ontology.name,
            "ontology_version": self.business_ontology.version,
            "catalog_name": self.cdm_catalog.name if self.cdm_catalog else None,
            "mappings": [mapping.model_dump() for mapping in self.mappings.values()]
        }
        
        dir_path = os.path.dirname(file_path)
        if dir_path:  # Only create directories if there's a directory path
            os.makedirs(dir_path, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(mappings_data, f, indent=2)
        
        log.info(f"Mappings exported to {file_path}")

    @classmethod
    def import_mappings(
        cls,
        file_path: str,
        semantic_model: Any,
        business_ontology: BusinessOntology,
        cdm_catalog: Optional[CDMCatalog] = None
    ) -> "OntologyMapper":
        """
        Import mappings from a JSON file.
        
        Args:
            file_path: Path to the mappings file.
            semantic_model: The semantic model to use.
            business_ontology: The business ontology to use.
            cdm_catalog: The CDM catalog to use.
            
        Returns:
            An OntologyMapper instance with loaded mappings.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            mappings_data = json.load(f)
        
        mapper = cls(semantic_model, business_ontology, cdm_catalog)
        
        for mapping_data in mappings_data.get("mappings", []):
            mapping = EntityMapping(**mapping_data)
            mapper.mappings[mapping.concept_name] = mapping
        
        log.info(f"Mappings imported from {file_path}")
        return mapper

    def get_mapping_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current mappings.
        
        Returns:
            Dictionary with mapping statistics and summary.
        """
        total_mappings = len(self.mappings)
        mappings_by_status = {}
        mappings_by_type = {}
        
        for mapping in self.mappings.values():
            # Count by status
            status = mapping.status.value if isinstance(mapping.status, MappingStatus) else mapping.status
            mappings_by_status[status] = mappings_by_status.get(status, 0) + 1
            
            # Count by type
            map_type = mapping.mapping_type.value if isinstance(mapping.mapping_type, MappingType) else mapping.mapping_type
            mappings_by_type[map_type] = mappings_by_type.get(map_type, 0) + 1
        
        unmapped_semantic = self.get_unmapped_semantic_entities()
        unmapped_cdm = self.get_unmapped_cdm_entities()
        
        return {
            "total_mappings": total_mappings,
            "mappings_by_status": mappings_by_status,
            "mappings_by_type": mappings_by_type,
            "unmapped_semantic_entities": len(unmapped_semantic),
            "unmapped_cdm_entities": len(unmapped_cdm),
            "validation_issues": self.validate_mappings()
        }

    def __str__(self) -> str:
        return f"OntologyMapper(mappings={len(self.mappings)})"

    def __repr__(self) -> str:
        return (
            f"OntologyMapper(ontology={self.business_ontology.name!r}, "
            f"mappings={list(self.mappings.keys())!r})"
        )
