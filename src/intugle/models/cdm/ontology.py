"""Business Ontology models for domain-level abstractions."""

import json
import logging
import os

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field

from intugle.common.schema import SchemaBase
from intugle.models.cdm.entities import CDMEntity

log = logging.getLogger(__name__)


class DomainType(str, Enum):
    """Common business domain types."""
    CUSTOMER = "customer"
    SALES = "sales"
    FINANCE = "finance"
    PRODUCT = "product"
    MARKETING = "marketing"
    OPERATIONS = "operations"
    SERVICE = "service"
    HR = "hr"
    CUSTOM = "custom"


class BusinessDomain(SchemaBase):
    """
    Represents a high-level business domain that groups related concepts.
    
    Examples: CustomerDomain, SalesDomain, FinanceDomain, ProductDomain
    
    Attributes:
        name: Name of the domain (e.g., "CustomerDomain", "SalesDomain").
        display_name: Human-readable display name.
        description: Description of what this domain encompasses.
        domain_type: The type of domain (from DomainType enum).
        owner: Domain owner or steward (e.g., "Sales Team", "Finance Dept").
        metadata: Additional custom metadata.
    """
    
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    domain_type: DomainType = DomainType.CUSTOM
    owner: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def __str__(self) -> str:
        return f"BusinessDomain(name='{self.name}', type='{self.domain_type}')"


class ConceptStatus(str, Enum):
    """Status of a business concept mapping."""
    PROPOSED = "proposed"
    APPROVED = "approved"
    DEPRECATED = "deprecated"
    IN_REVIEW = "in_review"


class BusinessConcept(SchemaBase):
    """
    Represents a business-level concept that maps to CDM entities.
    
    A Business Concept is a semantic abstraction that bridges the gap between
    technical semantic models and business terminology. It can reference one or
    more CDM entities and be mapped to semantic model entities.
    
    Attributes:
        name: Name of the business concept (e.g., "Customer", "Account", "SalesOrder").
        display_name: Human-readable display name.
        description: Description of what this concept represents.
        domain: Name of the business domain this concept belongs to.
        cdm_entity_name: Name of the associated CDM entity (e.g., "Account", "Contact").
        cdm_namespace: CDM namespace for the entity.
        status: Current status of the concept mapping.
        owner: Concept owner or steward.
        tags: List of tags for classification and search.
        metadata: Additional custom metadata.
    """
    
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None
    cdm_entity_name: Optional[str] = None
    cdm_namespace: Optional[str] = None
    status: ConceptStatus = ConceptStatus.PROPOSED
    owner: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def full_cdm_name(self) -> Optional[str]:
        """Return the fully qualified CDM entity name."""
        if self.cdm_entity_name and self.cdm_namespace:
            return f"{self.cdm_namespace}.{self.cdm_entity_name}"
        return self.cdm_entity_name

    def __str__(self) -> str:
        cdm_ref = f" -> CDM:{self.cdm_entity_name}" if self.cdm_entity_name else ""
        return f"BusinessConcept(name='{self.name}', domain='{self.domain}'{cdm_ref})"


class BusinessOntology:
    """
    A business ontology layer that sits on top of the semantic model.
    
    The Business Ontology provides domain-level organization and CDM alignment
    for semantic models, allowing users to group entities into business domains
    and map them to Microsoft Common Data Model entities.
    
    Attributes:
        name: Name of the business ontology.
        description: Description of the ontology's purpose and scope.
        version: Version of the ontology.
        domains: Dictionary mapping domain names to BusinessDomain objects.
        concepts: Dictionary mapping concept names to BusinessConcept objects.
    """
    
    def __init__(
        self,
        name: str = "Business Ontology",
        description: Optional[str] = None,
        version: str = "1.0"
    ):
        self.name = name
        self.description = description
        self.version = version
        self.domains: Dict[str, BusinessDomain] = {}
        self.concepts: Dict[str, BusinessConcept] = {}

    def add_domain(
        self,
        name: str,
        description: Optional[str] = None,
        domain_type: DomainType = DomainType.CUSTOM,
        owner: Optional[str] = None,
        **kwargs
    ) -> BusinessDomain:
        """
        Add a business domain to the ontology.
        
        Args:
            name: Name of the domain.
            description: Description of the domain.
            domain_type: Type of the domain.
            owner: Domain owner or steward.
            **kwargs: Additional metadata.
            
        Returns:
            The created BusinessDomain.
        """
        domain = BusinessDomain(
            name=name,
            description=description,
            domain_type=domain_type,
            owner=owner,
            metadata=kwargs
        )
        self.domains[name] = domain
        log.info(f"Added domain '{name}' to ontology '{self.name}'")
        return domain

    def get_domain(self, name: str) -> Optional[BusinessDomain]:
        """
        Retrieve a business domain by name.
        
        Args:
            name: The domain name to search for.
            
        Returns:
            The BusinessDomain if found, None otherwise.
        """
        return self.domains.get(name)

    def add_concept(
        self,
        name: str,
        domain: Optional[str] = None,
        cdm_entity: Optional[CDMEntity] = None,
        description: Optional[str] = None,
        status: ConceptStatus = ConceptStatus.PROPOSED,
        **kwargs
    ) -> BusinessConcept:
        """
        Add a business concept to the ontology.
        
        Args:
            name: Name of the concept.
            domain: Name of the domain this concept belongs to.
            cdm_entity: The CDM entity to associate with this concept.
            description: Description of the concept.
            status: Status of the concept mapping.
            **kwargs: Additional metadata.
            
        Returns:
            The created BusinessConcept.
        """
        # Extract known parameters from kwargs
        owner = kwargs.pop('owner', None)
        tags = kwargs.pop('tags', [])
        display_name = kwargs.pop('display_name', None)
        
        concept = BusinessConcept(
            name=name,
            display_name=display_name,
            description=description,
            domain=domain,
            status=status,
            owner=owner,
            tags=tags,
            metadata=kwargs  # Remaining kwargs go to metadata
        )
        
        if cdm_entity:
            concept.cdm_entity_name = cdm_entity.name
            concept.cdm_namespace = cdm_entity.namespace
        
        self.concepts[name] = concept
        log.info(f"Added concept '{name}' to ontology '{self.name}'")
        return concept

    def get_concept(self, name: str) -> Optional[BusinessConcept]:
        """
        Retrieve a business concept by name.
        
        Args:
            name: The concept name to search for.
            
        Returns:
            The BusinessConcept if found, None otherwise.
        """
        return self.concepts.get(name)

    def get_concepts_by_domain(self, domain_name: str) -> List[BusinessConcept]:
        """
        Get all concepts that belong to a specific domain.
        
        Args:
            domain_name: Name of the domain.
            
        Returns:
            List of BusinessConcept objects in the domain.
        """
        return [
            concept for concept in self.concepts.values()
            if concept.domain == domain_name
        ]

    def get_concepts_by_cdm_entity(self, cdm_entity_name: str) -> List[BusinessConcept]:
        """
        Get all concepts that map to a specific CDM entity.
        
        Args:
            cdm_entity_name: Name of the CDM entity.
            
        Returns:
            List of BusinessConcept objects mapped to the CDM entity.
        """
        return [
            concept for concept in self.concepts.values()
            if concept.cdm_entity_name == cdm_entity_name
        ]

    def list_domains(self) -> List[str]:
        """
        List all domain names in the ontology.
        
        Returns:
            List of domain names.
        """
        return list(self.domains.keys())

    def list_concepts(self) -> List[str]:
        """
        List all concept names in the ontology.
        
        Returns:
            List of concept names.
        """
        return list(self.concepts.keys())

    def save(self, file_path: str) -> None:
        """
        Save the business ontology to a JSON file.
        
        Args:
            file_path: Path where the ontology should be saved.
        """
        ontology_data = {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "domains": [domain.model_dump() for domain in self.domains.values()],
            "concepts": [concept.model_dump() for concept in self.concepts.values()]
        }
        
        dir_path = os.path.dirname(file_path)
        if dir_path:  # Only create directories if there's a directory path
            os.makedirs(dir_path, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(ontology_data, f, indent=2)
        
        log.info(f"Business ontology saved to {file_path}")

    @classmethod
    def load(cls, file_path: str) -> "BusinessOntology":
        """
        Load a business ontology from a JSON file.
        
        Args:
            file_path: Path to the ontology file.
            
        Returns:
            A BusinessOntology instance.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            ontology_data = json.load(f)
        
        ontology = cls(
            name=ontology_data.get("name", "Business Ontology"),
            description=ontology_data.get("description"),
            version=ontology_data.get("version", "1.0")
        )
        
        # Load domains
        for domain_data in ontology_data.get("domains", []):
            domain = BusinessDomain(**domain_data)
            ontology.domains[domain.name] = domain
        
        # Load concepts
        for concept_data in ontology_data.get("concepts", []):
            concept = BusinessConcept(**concept_data)
            ontology.concepts[concept.name] = concept
        
        log.info(f"Business ontology loaded from {file_path}")
        return ontology

    def __str__(self) -> str:
        return f"BusinessOntology(name='{self.name}', domains={len(self.domains)}, concepts={len(self.concepts)})"

    def __repr__(self) -> str:
        return (
            f"BusinessOntology(name={self.name!r}, version={self.version!r}, "
            f"domains={list(self.domains.keys())!r}, concepts={list(self.concepts.keys())!r})"
        )
