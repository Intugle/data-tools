"""Integration tests for CDM business ontology layer."""

import os
import tempfile

import pandas as pd
import pytest

from intugle import (
    BusinessConcept,
    BusinessOntology,
    CDMCatalog,
    OntologyMapper,
    SemanticModel,
)
from intugle.models.cdm.ontology import ConceptStatus, DomainType


class TestCDMIntegration:
    """Integration tests demonstrating full CDM workflow."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        customer_df = pd.DataFrame({
            "customer_id": [1, 2, 3],
            "email": ["alice@example.com", "bob@example.com", "charlie@example.com"],
            "full_name": ["Alice Smith", "Bob Jones", "Charlie Brown"],
            "phone": ["555-0001", "555-0002", "555-0003"]
        })
        
        account_df = pd.DataFrame({
            "account_id": [101, 102, 103],
            "account_name": ["Acme Corp", "TechStart Inc", "Global Solutions"],
            "account_balance": [50000.00, 75000.00, 120000.00]
        })
        
        sales_order_df = pd.DataFrame({
            "order_id": [1001, 1002, 1003],
            "order_date": pd.to_datetime(["2024-01-15", "2024-01-16", "2024-01-17"]),
            "customer_id": [1, 2, 1],
            "total_amount": [1500.00, 2300.00, 890.00]
        })
        
        return {
            "customer": customer_df,
            "account": account_df,
            "sales_order": sales_order_df
        }
    
    def test_full_workflow_from_scratch(self, sample_data):
        """Test the complete workflow from semantic model to CDM mapping."""
        
        # 1. Create a semantic model from sample data
        semantic_model = SemanticModel(sample_data, domain="E-commerce")
        
        # Verify semantic model was created
        assert len(semantic_model.datasets) == 3
        assert "customer" in semantic_model.datasets
        assert "account" in semantic_model.datasets
        assert "sales_order" in semantic_model.datasets
        
        # 2. Load the CDM catalog
        cdm_catalog = CDMCatalog.load_builtin("cdm_core")
        
        # Verify catalog has expected entities
        assert cdm_catalog.get_entity("Contact") is not None
        assert cdm_catalog.get_entity("Account") is not None
        
        # 3. Create a business ontology
        business_ontology = BusinessOntology(
            name="E-commerce Business Ontology (CDM)",
            description="Business ontology for e-commerce domain aligned with Microsoft CDM",
            version="1.0"
        )
        
        # 4. Define business domains
        customer_domain = business_ontology.add_domain(
            name="CustomerDomain",
            description="All customer and account-related concepts",
            domain_type=DomainType.CUSTOMER,
            owner="Customer Success Team"
        )
        
        sales_domain = business_ontology.add_domain(
            name="SalesDomain",
            description="Sales orders, invoices, and related concepts",
            domain_type=DomainType.SALES,
            owner="Sales Team"
        )
        
        assert len(business_ontology.domains) == 2
        
        # 5. Define business concepts linked to CDM entities
        customer_concept = business_ontology.add_concept(
            name="Customer",
            domain="CustomerDomain",
            cdm_entity=cdm_catalog.get_entity("Contact"),
            description="Customer contact information",
            status=ConceptStatus.APPROVED
        )
        
        account_concept = business_ontology.add_concept(
            name="Account",
            domain="CustomerDomain",
            cdm_entity=cdm_catalog.get_entity("Account"),
            description="Business account information",
            status=ConceptStatus.APPROVED
        )
        
        # Load sales catalog for SalesOrder
        sales_catalog = CDMCatalog.load_builtin("cdm_sales")
        sales_order_concept = business_ontology.add_concept(
            name="SalesOrder",
            domain="SalesDomain",
            cdm_entity=sales_catalog.get_entity("SalesOrder"),
            description="Sales order information",
            status=ConceptStatus.PROPOSED
        )
        
        assert len(business_ontology.concepts) == 3
        
        # 6. Create ontology mapper
        mapper = OntologyMapper(semantic_model, business_ontology, cdm_catalog)
        
        # 7. Map semantic entities to business concepts / CDM
        customer_mapping = mapper.map_entity(
            semantic_entity="customer",
            concept="Customer",
            attribute_map={
                "customer_id": "Contact.ContactId",
                "email": "Contact.Email",
                "full_name": "Contact.FullName",
                "phone": "Contact.PhoneNumber"
            }
        )
        
        assert customer_mapping is not None
        assert len(customer_mapping.attribute_mappings) == 4
        
        account_mapping = mapper.map_entity(
            semantic_entity="account",
            concept="Account",
            attribute_map={
                "account_id": "Account.AccountId",
                "account_name": "Account.Name",
                "account_balance": "Account.Balance"
            }
        )
        
        assert account_mapping is not None
        assert len(account_mapping.attribute_mappings) == 3
        
        sales_order_mapping = mapper.map_entity(
            semantic_entity="sales_order",
            concept="SalesOrder",
            attribute_map={
                "order_id": "SalesOrder.SalesOrderId",
                "order_date": "SalesOrder.OrderDate",
                "customer_id": "SalesOrder.CustomerId",
                "total_amount": "SalesOrder.TotalAmount"
            }
        )
        
        assert sales_order_mapping is not None
        
        # 8. Verify all entities are mapped
        unmapped = mapper.get_unmapped_semantic_entities()
        assert len(unmapped) == 0
        
        # 9. Get mapping summary
        summary = mapper.get_mapping_summary()
        assert summary["total_mappings"] == 3
        assert summary["unmapped_semantic_entities"] == 0
        
        # 10. Test querying mappings
        customer_mappings = mapper.get_mappings_by_semantic_entity("customer")
        assert len(customer_mappings) == 1
        assert customer_mappings[0].concept_name == "Customer"
        
        contact_mappings = mapper.get_mappings_by_cdm_entity("Contact")
        assert len(contact_mappings) == 1
        
        # 11. Test domain queries
        customer_concepts = business_ontology.get_concepts_by_domain("CustomerDomain")
        assert len(customer_concepts) == 2
        
        # 12. Test saving and loading
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save ontology
            ontology_path = os.path.join(temp_dir, "business_ontology_cdm.json")
            business_ontology.save(ontology_path)
            assert os.path.exists(ontology_path)
            
            # Save mappings
            mappings_path = os.path.join(temp_dir, "semantic_to_cdm_mappings.json")
            mapper.export_mappings(mappings_path)
            assert os.path.exists(mappings_path)
            
            # Load them back
            loaded_ontology = BusinessOntology.load(ontology_path)
            assert loaded_ontology.name == business_ontology.name
            assert len(loaded_ontology.concepts) == 3
            
            loaded_mapper = OntologyMapper.import_mappings(
                mappings_path,
                semantic_model,
                loaded_ontology,
                cdm_catalog
            )
            assert len(loaded_mapper.mappings) == 3
    
    def test_many_to_one_mapping(self, sample_data):
        """Test mapping multiple semantic entities to one CDM entity."""
        semantic_model = SemanticModel(sample_data)
        cdm_catalog = CDMCatalog.load_builtin("cdm_sales")
        ontology = BusinessOntology(name="Test Ontology")
        
        # Create a concept for combined sales order
        ontology.add_concept(
            name="CompleteSalesOrder",
            domain="SalesDomain",
            cdm_entity=cdm_catalog.get_entity("SalesOrder")
        )
        
        mapper = OntologyMapper(semantic_model, ontology, cdm_catalog)
        
        # Map both customer and sales_order to the concept
        # (simulating a scenario where data is split across tables)
        from intugle.models.cdm.mapper import MappingType
        
        mapping = mapper.map_entity(
            semantic_entity=["customer", "sales_order"],
            concept="CompleteSalesOrder",
            mapping_type=MappingType.MANY_TO_ONE
        )
        
        assert len(mapping.semantic_entities) == 2
        assert mapping.mapping_type == MappingType.MANY_TO_ONE
    
    def test_validation_and_unmapped_detection(self, sample_data):
        """Test validation and detection of unmapped entities."""
        semantic_model = SemanticModel(sample_data)
        cdm_catalog = CDMCatalog.load_builtin("cdm_core")
        ontology = BusinessOntology(name="Test Ontology")
        
        # Only create concept for customer
        ontology.add_concept(
            name="Customer",
            domain="CustomerDomain",
            cdm_entity=cdm_catalog.get_entity("Contact")
        )
        
        mapper = OntologyMapper(semantic_model, ontology, cdm_catalog)
        
        # Map only customer
        mapper.map_entity(semantic_entity="customer", concept="Customer")
        
        # Check unmapped entities
        unmapped_semantic = mapper.get_unmapped_semantic_entities()
        assert len(unmapped_semantic) == 2  # account and sales_order
        assert "account" in unmapped_semantic
        assert "sales_order" in unmapped_semantic
        
        unmapped_cdm = mapper.get_unmapped_cdm_entities()
        assert "Account" in unmapped_cdm
        assert "Contact" not in unmapped_cdm  # This one is mapped
    
    def test_concept_by_cdm_entity_query(self):
        """Test querying concepts by CDM entity."""
        cdm_catalog = CDMCatalog.load_builtin("cdm_core")
        ontology = BusinessOntology(name="Test Ontology")
        
        contact_entity = cdm_catalog.get_entity("Contact")
        
        # Create multiple concepts that map to the same CDM entity
        ontology.add_concept(
            name="Customer",
            cdm_entity=contact_entity
        )
        ontology.add_concept(
            name="Supplier",
            cdm_entity=contact_entity
        )
        ontology.add_concept(
            name="Partner",
            cdm_entity=contact_entity
        )
        
        # Query concepts by CDM entity
        contact_concepts = ontology.get_concepts_by_cdm_entity("Contact")
        assert len(contact_concepts) == 3
        
        concept_names = [c.name for c in contact_concepts]
        assert "Customer" in concept_names
        assert "Supplier" in concept_names
        assert "Partner" in concept_names
    
    def test_search_cdm_entities(self):
        """Test searching CDM entities."""
        catalog = CDMCatalog.load_builtin("cdm_core")
        
        # Search by name
        results = catalog.search_entities("account")
        assert len(results) >= 1
        assert any(e.name == "Account" for e in results)
        
        # Search by description
        results = catalog.search_entities("customer")
        assert len(results) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
