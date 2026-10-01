"""Unit tests for Business Ontology."""

import json
import os
import tempfile

import pytest

from intugle.models.cdm.catalog import CDMCatalog
from intugle.models.cdm.entities import CDMEntity
from intugle.models.cdm.ontology import (
    BusinessConcept,
    BusinessDomain,
    BusinessOntology,
    ConceptStatus,
    DomainType,
)


class TestBusinessDomain:
    """Test suite for BusinessDomain."""
    
    def test_create_basic_domain(self):
        """Test creating a basic business domain."""
        domain = BusinessDomain(
            name="CustomerDomain",
            domain_type=DomainType.CUSTOMER
        )
        
        assert domain.name == "CustomerDomain"
        assert domain.domain_type == DomainType.CUSTOMER
        assert domain.display_name is None
        assert domain.description is None

    def test_create_domain_with_details(self):
        """Test creating a domain with full details."""
        domain = BusinessDomain(
            name="SalesDomain",
            display_name="Sales Domain",
            description="All sales-related entities",
            domain_type=DomainType.SALES,
            owner="Sales Team",
            metadata={"priority": "high"}
        )
        
        assert domain.name == "SalesDomain"
        assert domain.display_name == "Sales Domain"
        assert domain.description == "All sales-related entities"
        assert domain.owner == "Sales Team"
        assert domain.metadata["priority"] == "high"


class TestBusinessConcept:
    """Test suite for BusinessConcept."""
    
    def test_create_basic_concept(self):
        """Test creating a basic business concept."""
        concept = BusinessConcept(
            name="Customer",
            domain="CustomerDomain"
        )
        
        assert concept.name == "Customer"
        assert concept.domain == "CustomerDomain"
        assert concept.status == ConceptStatus.PROPOSED
        assert concept.cdm_entity_name is None

    def test_create_concept_with_cdm_entity(self):
        """Test creating a concept linked to CDM entity."""
        concept = BusinessConcept(
            name="Customer",
            domain="CustomerDomain",
            cdm_entity_name="Contact",
            cdm_namespace="core.applicationCommon",
            status=ConceptStatus.APPROVED
        )
        
        assert concept.name == "Customer"
        assert concept.cdm_entity_name == "Contact"
        assert concept.cdm_namespace == "core.applicationCommon"
        assert concept.status == ConceptStatus.APPROVED

    def test_full_cdm_name_property(self):
        """Test the full_cdm_name property."""
        concept = BusinessConcept(
            name="Customer",
            cdm_entity_name="Contact",
            cdm_namespace="core.applicationCommon"
        )
        
        assert concept.full_cdm_name == "core.applicationCommon.Contact"

    def test_full_cdm_name_when_no_namespace(self):
        """Test full_cdm_name when namespace is missing."""
        concept = BusinessConcept(
            name="Customer",
            cdm_entity_name="Contact"
        )
        
        assert concept.full_cdm_name == "Contact"

    def test_concept_with_tags(self):
        """Test creating a concept with tags."""
        concept = BusinessConcept(
            name="Customer",
            domain="CustomerDomain",
            tags=["primary", "customer-facing", "pii"]
        )
        
        assert len(concept.tags) == 3
        assert "pii" in concept.tags


class TestBusinessOntology:
    """Test suite for BusinessOntology."""
    
    def test_create_empty_ontology(self):
        """Test creating an empty ontology."""
        ontology = BusinessOntology(name="Test Ontology")
        
        assert ontology.name == "Test Ontology"
        assert ontology.version == "1.0"
        assert len(ontology.domains) == 0
        assert len(ontology.concepts) == 0

    def test_add_domain(self):
        """Test adding domains to ontology."""
        ontology = BusinessOntology(name="Test Ontology")
        
        domain = ontology.add_domain(
            name="CustomerDomain",
            description="Customer-related entities",
            domain_type=DomainType.CUSTOMER
        )
        
        assert domain.name == "CustomerDomain"
        assert len(ontology.domains) == 1
        assert "CustomerDomain" in ontology.list_domains()

    def test_get_domain(self):
        """Test retrieving a domain."""
        ontology = BusinessOntology(name="Test Ontology")
        ontology.add_domain(name="CustomerDomain")
        
        domain = ontology.get_domain("CustomerDomain")
        assert domain is not None
        assert domain.name == "CustomerDomain"
        
        not_found = ontology.get_domain("NonExistent")
        assert not_found is None

    def test_add_concept_without_cdm(self):
        """Test adding a concept without CDM entity."""
        ontology = BusinessOntology(name="Test Ontology")
        ontology.add_domain(name="CustomerDomain")
        
        concept = ontology.add_concept(
            name="Customer",
            domain="CustomerDomain",
            description="Customer business entity"
        )
        
        assert concept.name == "Customer"
        assert concept.domain == "CustomerDomain"
        assert concept.cdm_entity_name is None
        assert len(ontology.concepts) == 1

    def test_add_concept_with_cdm(self):
        """Test adding a concept with CDM entity."""
        ontology = BusinessOntology(name="Test Ontology")
        
        cdm_entity = CDMEntity(name="Contact", namespace="core.applicationCommon")
        
        concept = ontology.add_concept(
            name="Customer",
            domain="CustomerDomain",
            cdm_entity=cdm_entity,
            status=ConceptStatus.APPROVED
        )
        
        assert concept.name == "Customer"
        assert concept.cdm_entity_name == "Contact"
        assert concept.cdm_namespace == "core.applicationCommon"
        assert concept.status == ConceptStatus.APPROVED

    def test_get_concept(self):
        """Test retrieving a concept."""
        ontology = BusinessOntology(name="Test Ontology")
        ontology.add_concept(name="Customer", domain="CustomerDomain")
        
        concept = ontology.get_concept("Customer")
        assert concept is not None
        assert concept.name == "Customer"
        
        not_found = ontology.get_concept("NonExistent")
        assert not_found is None

    def test_get_concepts_by_domain(self):
        """Test getting concepts by domain."""
        ontology = BusinessOntology(name="Test Ontology")
        
        ontology.add_concept(name="Customer", domain="CustomerDomain")
        ontology.add_concept(name="Account", domain="CustomerDomain")
        ontology.add_concept(name="SalesOrder", domain="SalesDomain")
        
        customer_concepts = ontology.get_concepts_by_domain("CustomerDomain")
        assert len(customer_concepts) == 2
        
        concept_names = [c.name for c in customer_concepts]
        assert "Customer" in concept_names
        assert "Account" in concept_names

    def test_get_concepts_by_cdm_entity(self):
        """Test getting concepts by CDM entity."""
        ontology = BusinessOntology(name="Test Ontology")
        
        contact_entity = CDMEntity(name="Contact", namespace="core")
        account_entity = CDMEntity(name="Account", namespace="core")
        
        ontology.add_concept(name="Customer", cdm_entity=contact_entity)
        ontology.add_concept(name="Person", cdm_entity=contact_entity)
        ontology.add_concept(name="CompanyAccount", cdm_entity=account_entity)
        
        contact_concepts = ontology.get_concepts_by_cdm_entity("Contact")
        assert len(contact_concepts) == 2
        
        concept_names = [c.name for c in contact_concepts]
        assert "Customer" in concept_names
        assert "Person" in concept_names

    def test_list_domains(self):
        """Test listing all domains."""
        ontology = BusinessOntology(name="Test Ontology")
        
        ontology.add_domain(name="CustomerDomain")
        ontology.add_domain(name="SalesDomain")
        ontology.add_domain(name="ProductDomain")
        
        domains = ontology.list_domains()
        assert len(domains) == 3
        assert "CustomerDomain" in domains
        assert "SalesDomain" in domains
        assert "ProductDomain" in domains

    def test_list_concepts(self):
        """Test listing all concepts."""
        ontology = BusinessOntology(name="Test Ontology")
        
        ontology.add_concept(name="Customer")
        ontology.add_concept(name="Account")
        ontology.add_concept(name="SalesOrder")
        
        concepts = ontology.list_concepts()
        assert len(concepts) == 3
        assert "Customer" in concepts
        assert "Account" in concepts
        assert "SalesOrder" in concepts

    def test_save_and_load_ontology(self):
        """Test saving and loading an ontology."""
        # Create ontology with domains and concepts
        ontology = BusinessOntology(
            name="Test Ontology",
            description="Test description",
            version="1.5"
        )
        
        ontology.add_domain(
            name="CustomerDomain",
            description="Customer domain",
            domain_type=DomainType.CUSTOMER
        )
        
        ontology.add_concept(
            name="Customer",
            domain="CustomerDomain",
            description="Customer concept"
        )
        
        # Save to temp file
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "ontology.json")
            ontology.save(file_path)
            
            # Load it back
            loaded_ontology = BusinessOntology.load(file_path)
            
            assert loaded_ontology.name == "Test Ontology"
            assert loaded_ontology.description == "Test description"
            assert loaded_ontology.version == "1.5"
            assert len(loaded_ontology.domains) == 1
            assert len(loaded_ontology.concepts) == 1
            
            loaded_domain = loaded_ontology.get_domain("CustomerDomain")
            assert loaded_domain is not None
            assert loaded_domain.description == "Customer domain"
            
            loaded_concept = loaded_ontology.get_concept("Customer")
            assert loaded_concept is not None
            assert loaded_concept.domain == "CustomerDomain"

    def test_ontology_string_representation(self):
        """Test string representation of ontology."""
        ontology = BusinessOntology(name="Test Ontology")
        ontology.add_domain(name="CustomerDomain")
        ontology.add_concept(name="Customer")
        
        ontology_str = str(ontology)
        assert "Test Ontology" in ontology_str
        assert "1" in ontology_str  # Number of domains and concepts


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
