"""Advanced edge case tests for CDM business ontology."""

import os
import tempfile

import pandas as pd
import pytest

from intugle import (
    BusinessOntology,
    CDMCatalog,
    OntologyMapper,
    SemanticModel,
)
from intugle.models.cdm.entities import CDMAttribute, CDMEntity
from intugle.models.cdm.mapper import MappingStatus, MappingType
from intugle.models.cdm.ontology import ConceptStatus, DomainType


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_semantic_model(self):
        """Test handling of empty semantic models."""
        # Create empty model
        empty_data = {}
        semantic_model = SemanticModel(empty_data)
        
        ontology = BusinessOntology(name="Test")
        catalog = CDMCatalog.load_builtin("cdm_core")
        
        mapper = OntologyMapper(semantic_model, ontology, catalog)
        
        # Should handle empty model gracefully
        unmapped = mapper.get_unmapped_semantic_entities()
        assert len(unmapped) == 0
        
        summary = mapper.get_mapping_summary()
        assert summary["total_mappings"] == 0
    
    def test_mapping_nonexistent_semantic_entity(self):
        """Test mapping a semantic entity that doesn't exist."""
        data = {"customers": pd.DataFrame({"id": [1, 2]})}
        semantic_model = SemanticModel(data)
        
        ontology = BusinessOntology(name="Test")
        catalog = CDMCatalog.load_builtin("cdm_core")
        
        ontology.add_concept(
            name="Customer",
            cdm_entity=catalog.get_entity("Contact")
        )
        
        mapper = OntologyMapper(semantic_model, ontology, catalog)
        
        # Map non-existent entity - should succeed (validation is separate)
        mapping = mapper.map_entity(
            semantic_entity="nonexistent_table",
            concept="Customer"
        )
        
        assert mapping is not None
        
        # But validation should catch it
        issues = mapper.validate_mappings()
        assert "missing_semantic_entities" in issues
        assert len(issues["missing_semantic_entities"]) > 0
    
    def test_mapping_to_deleted_concept(self):
        """Test behavior when a mapped concept is removed."""
        data = {"customers": pd.DataFrame({"id": [1]})}
        semantic_model = SemanticModel(data)
        
        ontology = BusinessOntology(name="Test")
        catalog = CDMCatalog.load_builtin("cdm_core")
        
        ontology.add_concept(
            name="Customer",
            cdm_entity=catalog.get_entity("Contact")
        )
        
        mapper = OntologyMapper(semantic_model, ontology, catalog)
        mapper.map_entity(semantic_entity="customers", concept="Customer")
        
        # Remove the concept
        del ontology.concepts["Customer"]
        
        # Validation should catch missing concept
        issues = mapper.validate_mappings()
        assert "missing_concepts" in issues
        assert len(issues["missing_concepts"]) > 0
    
    def test_duplicate_mappings_same_semantic_entity(self):
        """Test mapping same semantic entity to multiple concepts."""
        data = {"customers": pd.DataFrame({"id": [1]})}
        semantic_model = SemanticModel(data)
        
        ontology = BusinessOntology(name="Test")
        catalog = CDMCatalog.load_builtin("cdm_core")
        
        # Create two concepts
        ontology.add_concept(
            name="Customer",
            cdm_entity=catalog.get_entity("Contact")
        )
        ontology.add_concept(
            name="Person",
            cdm_entity=catalog.get_entity("Contact")
        )
        
        mapper = OntologyMapper(semantic_model, ontology, catalog)
        
        # Map same entity to both concepts
        mapper.map_entity(semantic_entity="customers", concept="Customer")
        mapper.map_entity(semantic_entity="customers", concept="Person")
        
        # Both mappings should exist
        assert len(mapper.mappings) == 2
        
        # Query should return both
        mappings = mapper.get_mappings_by_semantic_entity("customers")
        assert len(mappings) == 2
    
    def test_special_characters_in_names(self):
        """Test handling of special characters in entity/concept names."""
        data = {"customer-data_v2": pd.DataFrame({"id": [1]})}
        semantic_model = SemanticModel(data)
        
        ontology = BusinessOntology(name="Test Ontology (v2.0)")
        catalog = CDMCatalog.load_builtin("cdm_core")
        
        ontology.add_domain(name="Customer Domain (Primary)")
        ontology.add_concept(
            name="Customer-V2",
            domain="Customer Domain (Primary)",
            cdm_entity=catalog.get_entity("Contact")
        )
        
        mapper = OntologyMapper(semantic_model, ontology, catalog)
        mapper.map_entity(semantic_entity="customer-data_v2", concept="Customer-V2")
        
        # Should work without issues
        mapping = mapper.get_mapping("Customer-V2")
        assert mapping is not None
        assert mapping.semantic_entities[0] == "customer-data_v2"
    
    def test_unicode_in_metadata(self):
        """Test Unicode characters in descriptions and metadata."""
        ontology = BusinessOntology(
            name="国际化 Ontology",
            description="支持中文和其他语言"
        )
        
        ontology.add_domain(
            name="ClienteDomain",
            description="Domínio de clientes (português)"
        )
        
        ontology.add_concept(
            name="Cliente",
            description="客户实体 - Customer entity",
            metadata={"language": "多语言", "region": "全球"}
        )
        
        # Save and load
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "unicode_ontology.json")
            ontology.save(file_path)
            
            loaded = BusinessOntology.load(file_path)
            assert loaded.name == "国际化 Ontology"
            assert "中文" in loaded.description
    
    def test_very_large_attribute_mappings(self):
        """Test handling of entities with many attributes."""
        # Create entity with 100 columns
        data = {f"col_{i}": list(range(10)) for i in range(100)}
        df = pd.DataFrame(data)
        
        semantic_model = SemanticModel({"large_table": df})
        
        ontology = BusinessOntology(name="Test")
        catalog = CDMCatalog.load_builtin("cdm_core")
        
        ontology.add_concept(
            name="LargeEntity",
            cdm_entity=catalog.get_entity("Contact")
        )
        
        mapper = OntologyMapper(semantic_model, ontology, catalog)
        
        # Map many attributes
        attribute_map = {f"col_{i}": f"Contact.Attribute{i}" for i in range(100)}
        
        mapping = mapper.map_entity(
            semantic_entity="large_table",
            concept="LargeEntity",
            attribute_map=attribute_map
        )
        
        assert len(mapping.attribute_mappings) == 100
    
    def test_circular_concept_references(self):
        """Test that concepts don't create circular references."""
        ontology = BusinessOntology(name="Test")
        catalog = CDMCatalog.load_builtin("cdm_core")
        
        # Create concepts that could theoretically reference each other
        ontology.add_concept(
            name="Customer",
            cdm_entity=catalog.get_entity("Contact")
        )
        ontology.add_concept(
            name="Contact",
            cdm_entity=catalog.get_entity("Contact")
        )
        
        # Both map to same CDM entity - should be fine
        contact_concepts = ontology.get_concepts_by_cdm_entity("Contact")
        assert len(contact_concepts) == 2
    
    def test_status_transitions(self):
        """Test concept status lifecycle."""
        ontology = BusinessOntology(name="Test")
        
        # Create concept in proposed status
        concept = ontology.add_concept(
            name="Customer",
            status=ConceptStatus.PROPOSED
        )
        assert concept.status == ConceptStatus.PROPOSED
        
        # Update to in review
        concept.status = ConceptStatus.IN_REVIEW
        ontology.concepts["Customer"] = concept
        
        retrieved = ontology.get_concept("Customer")
        assert retrieved.status == ConceptStatus.IN_REVIEW
        
        # Approve
        concept.status = ConceptStatus.APPROVED
        ontology.concepts["Customer"] = concept
        
        # Deprecate
        concept.status = ConceptStatus.DEPRECATED
        ontology.concepts["Customer"] = concept
        
        assert ontology.get_concept("Customer").status == ConceptStatus.DEPRECATED
    
    def test_mapping_with_transformation_formulas(self):
        """Test attribute mappings with transformation logic."""
        data = {
            "orders": pd.DataFrame({
                "order_id": [1, 2],
                "first_name": ["John", "Jane"],
                "last_name": ["Doe", "Smith"]
            })
        }
        
        semantic_model = SemanticModel(data)
        ontology = BusinessOntology(name="Test")
        catalog = CDMCatalog.load_builtin("cdm_sales")
        
        ontology.add_concept(
            name="Order",
            cdm_entity=catalog.get_entity("SalesOrder")
        )
        
        mapper = OntologyMapper(semantic_model, ontology, catalog)
        
        mapping = mapper.map_entity(
            semantic_entity="orders",
            concept="Order"
        )
        
        # Add mapping with transformation
        mapping.add_attribute_mapping(
            semantic_attribute="first_name + last_name",
            cdm_attribute="SalesOrder.CustomerName",
            transformation="CONCAT(first_name, ' ', last_name)",
            confidence=0.95
        )
        
        assert len(mapping.attribute_mappings) == 1
        assert mapping.attribute_mappings[0].transformation is not None
        assert mapping.attribute_mappings[0].confidence == 0.95


class TestComplexMappingScenarios:
    """Test complex real-world mapping scenarios."""
    
    def test_header_detail_split_mapping(self):
        """Test mapping split tables (header/detail) to single CDM entity."""
        order_header = pd.DataFrame({
            "order_id": [1, 2],
            "order_date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "customer_id": [101, 102]
        })
        
        order_detail = pd.DataFrame({
            "order_id": [1, 1, 2],
            "line_number": [1, 2, 1],
            "product_id": [501, 502, 503],
            "quantity": [10, 5, 20]
        })
        
        semantic_model = SemanticModel({
            "order_header": order_header,
            "order_detail": order_detail
        })
        
        ontology = BusinessOntology(name="Test")
        catalog = CDMCatalog.load_builtin("cdm_sales")
        
        ontology.add_concept(
            name="CompleteSalesOrder",
            cdm_entity=catalog.get_entity("SalesOrder")
        )
        
        mapper = OntologyMapper(semantic_model, ontology, catalog)
        
        # Map both tables to single concept
        mapping = mapper.map_entity(
            semantic_entity=["order_header", "order_detail"],
            concept="CompleteSalesOrder",
            mapping_type=MappingType.MANY_TO_ONE,
            attribute_map={
                "order_header.order_id": "SalesOrder.SalesOrderId",
                "order_header.order_date": "SalesOrder.OrderDate",
                "order_detail.quantity": "SalesOrder.TotalQuantity"
            }
        )
        
        assert mapping.mapping_type == MappingType.MANY_TO_ONE
        assert len(mapping.semantic_entities) == 2
        assert "order_header" in mapping.semantic_entities
        assert "order_detail" in mapping.semantic_entities
    
    def test_denormalized_to_normalized_mapping(self):
        """Test mapping denormalized table to multiple CDM entities."""
        denormalized = pd.DataFrame({
            "order_id": [1, 2],
            "customer_name": ["Alice", "Bob"],
            "customer_email": ["alice@x.com", "bob@x.com"],
            "product_name": ["Widget", "Gadget"],
            "quantity": [10, 5]
        })
        
        semantic_model = SemanticModel({"orders_denorm": denormalized})
        
        ontology = BusinessOntology(name="Test")
        core_catalog = CDMCatalog.load_builtin("cdm_core")
        sales_catalog = CDMCatalog.load_builtin("cdm_sales")
        
        # Create concepts for customer and order
        ontology.add_concept(
            name="Customer",
            cdm_entity=core_catalog.get_entity("Contact")
        )
        ontology.add_concept(
            name="Order",
            cdm_entity=sales_catalog.get_entity("SalesOrder")
        )
        
        mapper = OntologyMapper(semantic_model, ontology, core_catalog)
        
        # Map to customer
        mapper.map_entity(
            semantic_entity="orders_denorm",
            concept="Customer",
            attribute_map={
                "customer_name": "Contact.FullName",
                "customer_email": "Contact.Email"
            }
        )
        
        # Also map to order
        mapper.map_entity(
            semantic_entity="orders_denorm",
            concept="Order",
            attribute_map={
                "order_id": "SalesOrder.SalesOrderId",
                "quantity": "SalesOrder.TotalQuantity"
            }
        )
        
        # One semantic entity mapped to two concepts
        mappings = mapper.get_mappings_by_semantic_entity("orders_denorm")
        assert len(mappings) == 2
    
    def test_cross_catalog_mapping(self):
        """Test mapping using entities from multiple catalogs."""
        data = {
            "customers": pd.DataFrame({"id": [1], "name": ["Alice"]}),
            "orders": pd.DataFrame({"id": [1], "customer_id": [1]})
        }
        
        semantic_model = SemanticModel(data)
        
        ontology = BusinessOntology(name="Test")
        core_catalog = CDMCatalog.load_builtin("cdm_core")
        sales_catalog = CDMCatalog.load_builtin("cdm_sales")
        
        # Use entities from both catalogs
        ontology.add_concept(
            name="Customer",
            domain="CustomerDomain",
            cdm_entity=core_catalog.get_entity("Contact")
        )
        ontology.add_concept(
            name="Order",
            domain="SalesDomain",
            cdm_entity=sales_catalog.get_entity("SalesOrder")
        )
        
        mapper = OntologyMapper(semantic_model, ontology, core_catalog)
        
        mapper.map_entity(semantic_entity="customers", concept="Customer")
        mapper.map_entity(semantic_entity="orders", concept="Order")
        
        assert len(mapper.mappings) == 2


class TestGovernanceWorkflows:
    """Test governance and collaboration workflows."""
    
    def test_mapping_approval_workflow(self):
        """Test typical approval workflow for mappings."""
        data = {"customers": pd.DataFrame({"id": [1]})}
        semantic_model = SemanticModel(data)
        
        ontology = BusinessOntology(name="Test")
        catalog = CDMCatalog.load_builtin("cdm_core")
        
        ontology.add_concept(
            name="Customer",
            status=ConceptStatus.PROPOSED,
            cdm_entity=catalog.get_entity("Contact")
        )
        
        mapper = OntologyMapper(semantic_model, ontology, catalog)
        
        # Create mapping in proposed state
        mapping = mapper.map_entity(
            semantic_entity="customers",
            concept="Customer",
            status=MappingStatus.PROPOSED,
            owner="data_architect@company.com",
            notes="Initial draft mapping"
        )
        
        assert mapping.status == MappingStatus.PROPOSED
        assert mapping.owner == "data_architect@company.com"
        
        # Move to review
        mapping.status = MappingStatus.IN_REVIEW
        mapping.notes = "Sent for business stakeholder review"
        mapper.mappings["Customer"] = mapping
        
        # Get review summary
        summary = mapper.get_mapping_summary()
        assert summary["mappings_by_status"]["in_review"] == 1
        
        # Approve
        mapping.status = MappingStatus.APPROVED
        mapper.mappings["Customer"] = mapping
        
        # Verify
        summary = mapper.get_mapping_summary()
        assert summary["mappings_by_status"]["approved"] == 1
    
    def test_concept_ownership_tracking(self):
        """Test tracking concept ownership."""
        ontology = BusinessOntology(name="Test")
        
        # Different teams own different domains
        ontology.add_domain(
            name="CustomerDomain",
            owner="Customer Success Team"
        )
        ontology.add_domain(
            name="SalesDomain",
            owner="Sales Operations Team"
        )
        
        # Concepts have owners
        ontology.add_concept(
            name="Customer",
            domain="CustomerDomain",
            owner="john.doe@company.com"
        )
        ontology.add_concept(
            name="Order",
            domain="SalesDomain",
            owner="jane.smith@company.com"
        )
        
        # Query by domain
        customer_concepts = ontology.get_concepts_by_domain("CustomerDomain")
        assert len(customer_concepts) == 1
        assert customer_concepts[0].owner == "john.doe@company.com"
    
    def test_mapping_confidence_scoring(self):
        """Test confidence scoring for mappings."""
        data = {"customers": pd.DataFrame({"id": [1], "name": ["Alice"]})}
        semantic_model = SemanticModel(data)
        
        ontology = BusinessOntology(name="Test")
        catalog = CDMCatalog.load_builtin("cdm_core")
        
        ontology.add_concept(name="Customer", cdm_entity=catalog.get_entity("Contact"))
        
        mapper = OntologyMapper(semantic_model, ontology, catalog)
        
        # Create mapping with high confidence
        mapping = mapper.map_entity(
            semantic_entity="customers",
            concept="Customer",
            confidence=0.95
        )
        
        # Add attribute mappings with varying confidence
        mapping.add_attribute_mapping(
            semantic_attribute="id",
            cdm_attribute="Contact.ContactId",
            confidence=1.0  # Perfect match
        )
        mapping.add_attribute_mapping(
            semantic_attribute="name",
            cdm_attribute="Contact.FullName",
            confidence=0.9  # Good match but not exact
        )
        
        assert mapping.confidence == 0.95
        assert mapping.attribute_mappings[0].confidence == 1.0
        assert mapping.attribute_mappings[1].confidence == 0.9
    
    def test_versioned_ontology_changes(self):
        """Test versioning of ontology changes."""
        ontology_v1 = BusinessOntology(
            name="Enterprise Ontology",
            version="1.0"
        )
        ontology_v1.add_concept(name="Customer")
        
        # Save v1
        with tempfile.TemporaryDirectory() as temp_dir:
            v1_path = os.path.join(temp_dir, "ontology_v1.json")
            ontology_v1.save(v1_path)
            
            # Create v2 with changes
            ontology_v2 = BusinessOntology.load(v1_path)
            ontology_v2.version = "2.0"
            ontology_v2.add_concept(name="Account")
            
            v2_path = os.path.join(temp_dir, "ontology_v2.json")
            ontology_v2.save(v2_path)
            
            # Load and compare
            loaded_v1 = BusinessOntology.load(v1_path)
            loaded_v2 = BusinessOntology.load(v2_path)
            
            assert loaded_v1.version == "1.0"
            assert loaded_v2.version == "2.0"
            assert len(loaded_v1.concepts) == 1
            assert len(loaded_v2.concepts) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
