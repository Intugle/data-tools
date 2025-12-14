"""Unit tests for Ontology Mapper."""

import os
import tempfile
from unittest.mock import MagicMock

import pytest

from intugle.models.cdm.catalog import CDMCatalog
from intugle.models.cdm.entities import CDMAttribute, CDMEntity
from intugle.models.cdm.mapper import (
    AttributeMapping,
    EntityMapping,
    MappingStatus,
    MappingType,
    OntologyMapper,
)
from intugle.models.cdm.ontology import BusinessOntology


class TestAttributeMapping:
    """Test suite for AttributeMapping."""
    
    def test_create_basic_attribute_mapping(self):
        """Test creating a basic attribute mapping."""
        mapping = AttributeMapping(
            semantic_attribute="customer_id",
            cdm_attribute="Contact.ContactId"
        )
        
        assert mapping.semantic_attribute == "customer_id"
        assert mapping.cdm_attribute == "Contact.ContactId"
        assert mapping.confidence == 1.0

    def test_create_attribute_mapping_with_transformation(self):
        """Test creating an attribute mapping with transformation."""
        mapping = AttributeMapping(
            semantic_attribute="full_name",
            cdm_attribute="Contact.FullName",
            transformation="CONCAT(first_name, ' ', last_name)",
            confidence=0.9,
            notes="Combines first and last name"
        )
        
        assert mapping.transformation == "CONCAT(first_name, ' ', last_name)"
        assert mapping.confidence == 0.9
        assert mapping.notes == "Combines first and last name"


class TestEntityMapping:
    """Test suite for EntityMapping."""
    
    def test_create_basic_entity_mapping(self):
        """Test creating a basic entity mapping."""
        mapping = EntityMapping(
            semantic_entities=["customer"],
            concept_name="Customer",
            cdm_entity_name="Contact"
        )
        
        assert mapping.semantic_entities == ["customer"]
        assert mapping.concept_name == "Customer"
        assert mapping.cdm_entity_name == "Contact"
        assert mapping.mapping_type == MappingType.ONE_TO_ONE
        assert mapping.status == MappingStatus.PROPOSED

    def test_create_many_to_one_mapping(self):
        """Test creating a many-to-one mapping."""
        mapping = EntityMapping(
            semantic_entities=["sales_order_header", "sales_order_line"],
            concept_name="SalesOrder",
            cdm_entity_name="SalesOrder",
            mapping_type=MappingType.MANY_TO_ONE
        )
        
        assert len(mapping.semantic_entities) == 2
        assert mapping.mapping_type == MappingType.MANY_TO_ONE

    def test_add_attribute_mapping(self):
        """Test adding attribute mappings to entity mapping."""
        mapping = EntityMapping(
            semantic_entities=["customer"],
            concept_name="Customer"
        )
        
        mapping.add_attribute_mapping(
            semantic_attribute="customer_id",
            cdm_attribute="Contact.ContactId"
        )
        mapping.add_attribute_mapping(
            semantic_attribute="email",
            cdm_attribute="Contact.Email"
        )
        
        assert len(mapping.attribute_mappings) == 2
        assert mapping.attribute_mappings[0].semantic_attribute == "customer_id"
        assert mapping.attribute_mappings[1].semantic_attribute == "email"


class TestOntologyMapper:
    """Test suite for OntologyMapper."""
    
    @pytest.fixture
    def setup_ontology_and_catalog(self):
        """Create a basic ontology and catalog for testing."""
        # Create ontology
        ontology = BusinessOntology(name="Test Ontology")
        ontology.add_domain(name="CustomerDomain")
        ontology.add_domain(name="SalesDomain")
        
        # Create CDM catalog
        catalog = CDMCatalog(name="Test CDM")
        
        contact = CDMEntity(name="Contact", namespace="core.applicationCommon")
        contact.add_attribute(CDMAttribute(name="ContactId", data_type="guid"))
        contact.add_attribute(CDMAttribute(name="Email", data_type="string"))
        catalog.add_entity(contact)
        
        account = CDMEntity(name="Account", namespace="core.applicationCommon")
        account.add_attribute(CDMAttribute(name="AccountId", data_type="guid"))
        account.add_attribute(CDMAttribute(name="Name", data_type="string"))
        catalog.add_entity(account)
        
        # Add concepts to ontology
        ontology.add_concept(
            name="Customer",
            domain="CustomerDomain",
            cdm_entity=contact
        )
        
        ontology.add_concept(
            name="Account",
            domain="CustomerDomain",
            cdm_entity=account
        )
        
        return ontology, catalog
    
    @pytest.fixture
    def mock_semantic_model(self):
        """Create a mock semantic model."""
        model = MagicMock()
        model.datasets = {
            "customer": MagicMock(),
            "account": MagicMock(),
            "sales_order": MagicMock()
        }
        return model
    
    def test_create_mapper(self, setup_ontology_and_catalog, mock_semantic_model):
        """Test creating an ontology mapper."""
        ontology, catalog = setup_ontology_and_catalog
        
        mapper = OntologyMapper(mock_semantic_model, ontology, catalog)
        
        assert mapper.semantic_model == mock_semantic_model
        assert mapper.business_ontology == ontology
        assert mapper.cdm_catalog == catalog
        assert len(mapper.mappings) == 0
    
    def test_map_single_entity(self, setup_ontology_and_catalog, mock_semantic_model):
        """Test mapping a single semantic entity to a concept."""
        ontology, catalog = setup_ontology_and_catalog
        mapper = OntologyMapper(mock_semantic_model, ontology, catalog)
        
        mapping = mapper.map_entity(
            semantic_entity="customer",
            concept="Customer",
            attribute_map={
                "customer_id": "Contact.ContactId",
                "email": "Contact.Email"
            }
        )
        
        assert mapping is not None
        assert mapping.semantic_entities == ["customer"]
        assert mapping.concept_name == "Customer"
        assert mapping.cdm_entity_name == "Contact"
        assert len(mapping.attribute_mappings) == 2
        assert len(mapper.mappings) == 1
    
    def test_map_multiple_entities(self, setup_ontology_and_catalog, mock_semantic_model):
        """Test mapping multiple semantic entities to one concept."""
        ontology, catalog = setup_ontology_and_catalog
        mapper = OntologyMapper(mock_semantic_model, ontology, catalog)
        
        mapping = mapper.map_entity(
            semantic_entity=["sales_order_header", "sales_order_line"],
            concept="Customer",
            mapping_type=MappingType.MANY_TO_ONE
        )
        
        assert len(mapping.semantic_entities) == 2
        assert mapping.mapping_type == MappingType.MANY_TO_ONE
    
    def test_map_to_nonexistent_concept(self, setup_ontology_and_catalog, mock_semantic_model):
        """Test that mapping to a non-existent concept raises error."""
        ontology, catalog = setup_ontology_and_catalog
        mapper = OntologyMapper(mock_semantic_model, ontology, catalog)
        
        with pytest.raises(ValueError) as exc_info:
            mapper.map_entity(
                semantic_entity="customer",
                concept="NonExistentConcept"
            )
        
        assert "not found in ontology" in str(exc_info.value)
    
    def test_get_mapping(self, setup_ontology_and_catalog, mock_semantic_model):
        """Test retrieving a mapping by concept name."""
        ontology, catalog = setup_ontology_and_catalog
        mapper = OntologyMapper(mock_semantic_model, ontology, catalog)
        
        mapper.map_entity(semantic_entity="customer", concept="Customer")
        
        mapping = mapper.get_mapping("Customer")
        assert mapping is not None
        assert mapping.concept_name == "Customer"
        
        not_found = mapper.get_mapping("NonExistent")
        assert not_found is None
    
    def test_get_mappings_by_semantic_entity(self, setup_ontology_and_catalog, mock_semantic_model):
        """Test getting mappings by semantic entity name."""
        ontology, catalog = setup_ontology_and_catalog
        mapper = OntologyMapper(mock_semantic_model, ontology, catalog)
        
        mapper.map_entity(semantic_entity="customer", concept="Customer")
        mapper.map_entity(semantic_entity="account", concept="Account")
        
        customer_mappings = mapper.get_mappings_by_semantic_entity("customer")
        assert len(customer_mappings) == 1
        assert customer_mappings[0].concept_name == "Customer"
    
    def test_get_mappings_by_cdm_entity(self, setup_ontology_and_catalog, mock_semantic_model):
        """Test getting mappings by CDM entity name."""
        ontology, catalog = setup_ontology_and_catalog
        mapper = OntologyMapper(mock_semantic_model, ontology, catalog)
        
        mapper.map_entity(semantic_entity="customer", concept="Customer")
        
        contact_mappings = mapper.get_mappings_by_cdm_entity("Contact")
        assert len(contact_mappings) == 1
        assert contact_mappings[0].cdm_entity_name == "Contact"
    
    def test_get_unmapped_semantic_entities(self, setup_ontology_and_catalog, mock_semantic_model):
        """Test getting unmapped semantic entities."""
        ontology, catalog = setup_ontology_and_catalog
        mapper = OntologyMapper(mock_semantic_model, ontology, catalog)
        
        # Map only one entity
        mapper.map_entity(semantic_entity="customer", concept="Customer")
        
        unmapped = mapper.get_unmapped_semantic_entities()
        assert len(unmapped) == 2  # account and sales_order should be unmapped
        assert "account" in unmapped
        assert "sales_order" in unmapped
        assert "customer" not in unmapped
    
    def test_get_unmapped_cdm_entities(self, setup_ontology_and_catalog, mock_semantic_model):
        """Test getting unmapped CDM entities."""
        ontology, catalog = setup_ontology_and_catalog
        mapper = OntologyMapper(mock_semantic_model, ontology, catalog)
        
        # Map only customer -> Contact
        mapper.map_entity(semantic_entity="customer", concept="Customer")
        
        unmapped = mapper.get_unmapped_cdm_entities()
        assert len(unmapped) == 1
        assert "Account" in unmapped
        assert "Contact" not in unmapped
    
    def test_validate_mappings(self, setup_ontology_and_catalog, mock_semantic_model):
        """Test mapping validation."""
        ontology, catalog = setup_ontology_and_catalog
        mapper = OntologyMapper(mock_semantic_model, ontology, catalog)
        
        # Create a valid mapping
        mapper.map_entity(semantic_entity="customer", concept="Customer")
        
        issues = mapper.validate_mappings()
        assert len(issues) == 0  # Should have no issues
    
    def test_export_and_import_mappings(self, setup_ontology_and_catalog, mock_semantic_model):
        """Test exporting and importing mappings."""
        ontology, catalog = setup_ontology_and_catalog
        mapper = OntologyMapper(mock_semantic_model, ontology, catalog)
        
        # Create mappings
        mapper.map_entity(
            semantic_entity="customer",
            concept="Customer",
            attribute_map={"customer_id": "Contact.ContactId"}
        )
        
        # Export to temp file
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "mappings.json")
            mapper.export_mappings(file_path)
            
            # Import into new mapper
            new_mapper = OntologyMapper.import_mappings(
                file_path,
                mock_semantic_model,
                ontology,
                catalog
            )
            
            assert len(new_mapper.mappings) == 1
            mapping = new_mapper.get_mapping("Customer")
            assert mapping is not None
            assert len(mapping.attribute_mappings) == 1
    
    def test_get_mapping_summary(self, setup_ontology_and_catalog, mock_semantic_model):
        """Test getting mapping summary."""
        ontology, catalog = setup_ontology_and_catalog
        mapper = OntologyMapper(mock_semantic_model, ontology, catalog)
        
        # Create some mappings with different statuses
        mapper.map_entity(
            semantic_entity="customer",
            concept="Customer",
            status=MappingStatus.APPROVED
        )
        mapper.map_entity(
            semantic_entity="account",
            concept="Account",
            status=MappingStatus.PROPOSED
        )
        
        summary = mapper.get_mapping_summary()
        
        assert summary["total_mappings"] == 2
        assert "approved" in summary["mappings_by_status"]
        assert "proposed" in summary["mappings_by_status"]
        assert summary["mappings_by_status"]["approved"] == 1
        assert summary["mappings_by_status"]["proposed"] == 1
        assert summary["unmapped_semantic_entities"] == 1  # sales_order
    
    def test_mapper_with_dict_semantic_model(self, setup_ontology_and_catalog):
        """Test mapper works with dict-based semantic model."""
        ontology, catalog = setup_ontology_and_catalog
        
        # Use a dict instead of mock object
        dict_model = {
            "customer": {"data": "..."},
            "account": {"data": "..."}
        }
        
        mapper = OntologyMapper(dict_model, ontology, catalog)
        mapper.map_entity(semantic_entity="customer", concept="Customer")
        
        unmapped = mapper.get_unmapped_semantic_entities()
        assert "account" in unmapped
        assert "customer" not in unmapped


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
