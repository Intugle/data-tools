"""
Final Stress Test - Run Everything Multiple Times

This test ensures complete stability by running all operations multiple times.
"""

import pytest
import pandas as pd
from intugle import SemanticModel, BusinessOntology, CDMCatalog, OntologyMapper
from intugle.models.cdm.ontology import ConceptStatus, DomainType


class TestStability:
    """Stress tests to ensure stability."""
    
    def test_repeated_catalog_loads(self):
        """Load catalogs 10 times to ensure no memory leaks or state issues."""
        for i in range(10):
            cdm_core = CDMCatalog.load_builtin("cdm_core")
            cdm_sales = CDMCatalog.load_builtin("cdm_sales")
            cdm_service = CDMCatalog.load_builtin("cdm_service")
            
            assert "Contact" in cdm_core.entities
            assert "SalesOrder" in cdm_sales.entities
            assert "Case" in cdm_service.entities
    
    def test_repeated_ontology_creation(self):
        """Create ontologies 10 times with different data."""
        for i in range(10):
            ontology = BusinessOntology(
                name=f"Test Ontology {i}",
                description=f"Iteration {i}",
                version=f"{i}.0"
            )
            
            # Add domains
            for j in range(5):
                ontology.add_domain(
                    f"Domain_{i}_{j}",
                    f"Domain {j} in iteration {i}",
                    DomainType.CUSTOM
                )
            
            # Add concepts
            for j in range(10):
                ontology.add_concept(
                    f"Concept_{i}_{j}",
                    f"Domain_{i}_{j % 5}",
                    description=f"Concept {j}"
                )
            
            assert len(ontology.domains) == 5
            assert len(ontology.concepts) == 10
    
    def test_repeated_mapping_operations(self):
        """Create and query mappings 10 times."""
        cdm = CDMCatalog.load_builtin("cdm_core")
        
        for i in range(10):
            # Create fresh data each time
            data = {
                f"table_{j}": pd.DataFrame({
                    "id": [1, 2, 3],
                    "value": [f"a_{i}", f"b_{i}", f"c_{i}"]
                })
                for j in range(5)
            }
            
            semantic_model = SemanticModel(data, domain=f"Test{i}")
            ontology = BusinessOntology(f"Ont{i}", f"Desc{i}", f"{i}.0")
            ontology.add_domain("D1", "Domain", DomainType.CUSTOM)
            
            for j in range(5):
                ontology.add_concept(
                    f"C{j}",
                    "D1",
                    cdm.get_entity("Contact"),
                    status=ConceptStatus.APPROVED
                )
            
            mapper = OntologyMapper(semantic_model, ontology, cdm)
            
            for j in range(5):
                mapper.map_entity(f"table_{j}", f"C{j}", status="approved")
            
            assert len(mapper.mappings) == 5
            
            # Query operations
            summary = mapper.get_mapping_summary()
            assert summary['total_mappings'] == 5
            
            unmapped = mapper.get_unmapped_semantic_entities()
            assert len(unmapped) == 0
    
    def test_mixed_operations_stability(self):
        """Mix various operations to test stability."""
        for iteration in range(5):
            # Load catalogs
            cdm_core = CDMCatalog.load_builtin("cdm_core")
            cdm_sales = CDMCatalog.load_builtin("cdm_sales")
            
            # Create semantic model
            data = {
                "customers": pd.DataFrame({
                    "id": list(range(100)),
                    "name": [f"Customer {i}" for i in range(100)]
                }),
                "orders": pd.DataFrame({
                    "order_id": list(range(200)),
                    "customer_id": [i % 100 for i in range(200)]
                })
            }
            
            semantic_model = SemanticModel(data, domain="Stress Test")
            
            # Create ontology
            ontology = BusinessOntology(
                f"Stress Test {iteration}",
                "Testing stability",
                f"{iteration}.0"
            )
            
            ontology.add_domain("Customer", "Customers", DomainType.CUSTOMER)
            ontology.add_domain("Sales", "Sales", DomainType.SALES)
            
            ontology.add_concept(
                "Customer",
                "Customer",
                cdm_core.get_entity("Contact"),
                status=ConceptStatus.APPROVED
            )
            
            ontology.add_concept(
                "Order",
                "Sales",
                cdm_sales.get_entity("SalesOrder"),
                status=ConceptStatus.APPROVED
            )
            
            # Create mapper
            mapper = OntologyMapper(semantic_model, ontology, cdm_core)
            
            # Create mappings
            mapper.map_entity("customers", "Customer", status="approved")
            mapper.map_entity("orders", "Order", status="approved")
            
            # Validate
            issues = mapper.validate_mappings()
            assert isinstance(issues, dict)
            
            # Query
            contact_mappings = mapper.get_mappings_by_cdm_entity("Contact")
            assert len(contact_mappings) == 1
            
            customer_concepts = ontology.get_concepts_by_domain("Customer")
            assert len(customer_concepts) == 1
            
            summary = mapper.get_mapping_summary()
            assert summary['total_mappings'] == 2
    
    def test_unicode_handling_stability(self):
        """Test Unicode handling across multiple iterations."""
        test_strings = [
            "测试",  # Chinese
            "Тест",  # Russian
            "テスト",  # Japanese
            "🎉✓🔥",  # Emojis
            "Ñoño",  # Spanish
            "Müller",  # German
        ]
        
        for name in test_strings:
            ontology = BusinessOntology(
                name=f"Test {name}",
                description=f"Description with {name}",
                version="1.0"
            )
            
            ontology.add_domain(
                f"Domain_{name}",
                f"Domain with {name}",
                DomainType.CUSTOM
            )
            
            ontology.add_concept(
                f"Concept_{name}",
                f"Domain_{name}",
                description=f"Concept with {name}"
            )
            
            # Verify
            assert name in ontology.name
            concepts = ontology.list_concepts()
            assert len(concepts) == 1
    
    def test_error_recovery_stability(self):
        """Test that errors don't leave system in bad state."""
        ontology = BusinessOntology("Test", "Test", "1.0")
        ontology.add_domain("D1", "Domain", DomainType.CUSTOM)
        
        # Multiple failed operations shouldn't break state
        for i in range(10):
            # Try to get non-existent concept
            result = ontology.get_concept(f"NonExistent_{i}")
            assert result is None
            
            # Try to get non-existent domain
            result = ontology.get_domain(f"NoSuchDomain_{i}")
            assert result is None
        
        # System should still work after errors
        ontology.add_concept("GoodConcept", "D1", description="Should work")
        result = ontology.get_concept("GoodConcept")
        assert result is not None
        assert result.name == "GoodConcept"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
