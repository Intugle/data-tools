"""
Performance Benchmark Tests for CDM Business Ontology Layer

Tests performance characteristics and scalability of the CDM implementation.
"""

import pytest
import time
import pandas as pd
from intugle import SemanticModel, BusinessOntology, CDMCatalog, OntologyMapper
from intugle.models.cdm.ontology import DomainType, ConceptStatus


class TestPerformance:
    """Performance benchmarks for CDM operations."""
    
    def test_large_catalog_loading(self):
        """Test loading and searching large CDM catalogs."""
        start = time.time()
        
        # Create a large catalog
        catalog = CDMCatalog(name="Large Test Catalog")
        
        # Add 1000 entities with 50 attributes each
        for i in range(1000):
            from intugle.models.cdm.entities import CDMEntity, CDMAttribute
            entity = CDMEntity(
                name=f"Entity_{i}",
                description=f"Test entity number {i}"
            )
            
            # Add 50 attributes per entity
            for j in range(50):
                entity.add_attribute(CDMAttribute(
                    name=f"attr_{j}",
                    data_type="string" if j % 3 == 0 else ("integer" if j % 3 == 1 else "decimal"),
                    description=f"Attribute {j}"
                ))
            
            catalog.add_entity(entity)
        
        load_time = time.time() - start
        
        # Search performance
        search_start = time.time()
        results = catalog.search_entities("Entity_999")
        search_time = time.time() - search_start
        
        print(f"\n  Large catalog metrics:")
        print(f"    - Entities: 1000")
        print(f"    - Total attributes: 50,000")
        print(f"    - Load time: {load_time:.3f}s")
        print(f"    - Search time: {search_time:.4f}s")
        print(f"    - Search results: {len(results)}")
        
        # Assertions
        assert len(catalog.entities) == 1000
        assert load_time < 5.0, f"Loading took {load_time:.2f}s, expected < 5s"
        assert search_time < 0.5, f"Search took {search_time:.4f}s, expected < 0.5s"
        assert len(results) > 0
    
    def test_large_ontology_operations(self):
        """Test ontology operations with many domains and concepts."""
        start = time.time()
        
        ontology = BusinessOntology(
            name="Large Ontology Test",
            description="Performance test",
            version="1.0"
        )
        
        # Add 50 domains
        domain_types = list(DomainType)
        for i in range(50):
            ontology.add_domain(
                name=f"Domain_{i}",
                description=f"Test domain {i}",
                domain_type=domain_types[i % len(domain_types)]
            )
        
        # Add 500 concepts (10 per domain average)
        for i in range(500):
            domain_idx = i % 50
            ontology.add_concept(
                name=f"Concept_{i}",
                domain=f"Domain_{domain_idx}",
                description=f"Test concept {i}",
                status=ConceptStatus.APPROVED if i % 3 == 0 else ConceptStatus.IN_REVIEW
            )
        
        create_time = time.time() - start
        
        # Query performance
        query_start = time.time()
        domain_0_concepts = ontology.get_concepts_by_domain("Domain_0")
        query_time = time.time() - query_start
        
        # List operations
        list_start = time.time()
        all_domains = ontology.list_domains()
        all_concepts = ontology.list_concepts()
        list_time = time.time() - list_start
        
        print(f"\n  Large ontology metrics:")
        print(f"    - Domains: {len(ontology.domains)}")
        print(f"    - Concepts: {len(ontology.concepts)}")
        print(f"    - Creation time: {create_time:.3f}s")
        print(f"    - Query time: {query_time:.4f}s")
        print(f"    - List time: {list_time:.4f}s")
        print(f"    - Domain_0 concepts: {len(domain_0_concepts)}")
        
        # Assertions
        assert len(ontology.domains) == 50
        assert len(ontology.concepts) == 500
        assert create_time < 3.0, f"Creation took {create_time:.2f}s, expected < 3s"
        assert query_time < 0.1, f"Query took {query_time:.4f}s, expected < 0.1s"
        assert list_time < 0.1, f"List took {list_time:.4f}s, expected < 0.1s"
    
    def test_large_mapping_operations(self):
        """Test mapping operations with many entities."""
        # Create semantic model with 200 tables
        data = {}
        for i in range(200):
            data[f"table_{i}"] = pd.DataFrame({
                f"col_{j}": [f"value_{j}" for _ in range(10)]
                for j in range(20)  # 20 columns per table
            })
        
        semantic_model = SemanticModel(data, domain="Test")
        
        # Create ontology with concepts
        ontology = BusinessOntology(
            name="Large Mapping Test",
            description="Performance test",
            version="1.0"
        )
        
        ontology.add_domain("TestDomain", "Test domain", DomainType.PRODUCT)
        
        # Add 200 concepts
        for i in range(200):
            ontology.add_concept(
                name=f"Concept_{i}",
                domain="TestDomain",
                description=f"Test concept {i}",
                status=ConceptStatus.APPROVED
            )
        
        # Load CDM catalog
        cdm_catalog = CDMCatalog.load_builtin("cdm_core")
        
        # Create mapper
        mapper = OntologyMapper(semantic_model, ontology, cdm_catalog)
        
        # Map all entities
        map_start = time.time()
        for i in range(200):
            mapper.map_entity(
                semantic_entity=f"table_{i}",
                concept=f"Concept_{i}",
                status="approved"
            )
        map_time = time.time() - map_start
        
        # Query performance
        query_start = time.time()
        all_mappings = [mapper.get_mapping(f"table_{i}") for i in range(200)]
        query_time = time.time() - query_start
        
        # Summary performance
        summary_start = time.time()
        summary = mapper.get_mapping_summary()
        summary_time = time.time() - summary_start
        
        # Validation performance
        validate_start = time.time()
        issues = mapper.validate_mappings()
        validate_time = time.time() - validate_start
        
        print(f"\n  Large mapping metrics:")
        print(f"    - Semantic entities: 200 (4,000 attributes)")
        print(f"    - Mappings created: {len(mapper.mappings)}")
        print(f"    - Mapping time: {map_time:.3f}s ({map_time/200*1000:.2f}ms per entity)")
        print(f"    - Query time: {query_time:.3f}s ({query_time/200*1000:.2f}ms per query)")
        print(f"    - Summary time: {summary_time:.4f}s")
        print(f"    - Validation time: {validate_time:.3f}s")
        
        # Assertions
        assert len(mapper.mappings) == 200
        assert map_time < 5.0, f"Mapping took {map_time:.2f}s, expected < 5s"
        assert query_time < 2.0, f"Querying took {query_time:.2f}s, expected < 2s"
        assert summary_time < 0.5, f"Summary took {summary_time:.4f}s, expected < 0.5s"
        assert validate_time < 2.0, f"Validation took {validate_time:.2f}s, expected < 2s"
        assert summary['total_mappings'] == 200
    
    def test_persistence_performance(self):
        """Test save/load performance with large artifacts."""
        import tempfile
        import os
        
        # Create large ontology
        ontology = BusinessOntology(
            name="Persistence Test",
            description="Large ontology for persistence testing",
            version="1.0"
        )
        
        # Add 20 domains with 25 concepts each (500 total)
        for d in range(20):
            domain_name = f"Domain_{d}"
            ontology.add_domain(
                domain_name,
                f"Test domain {d}",
                DomainType.PRODUCT
            )
            
            for c in range(25):
                ontology.add_concept(
                    name=f"Concept_{d}_{c}",
                    domain=domain_name,
                    description=f"Concept {c} in domain {d}",
                    status=ConceptStatus.APPROVED,
                    tags=[f"tag_{i}" for i in range(5)],
                    owner=f"owner_{d}@test.com"
                )
        
        # Test save performance
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "large_ontology.json")
            
            save_start = time.time()
            ontology.save(filepath)
            save_time = time.time() - save_start
            
            # Get file size
            file_size = os.path.getsize(filepath)
            
            # Test load performance
            load_start = time.time()
            loaded = BusinessOntology.load(filepath)
            load_time = time.time() - load_start
            
            print(f"\n  Persistence metrics:")
            print(f"    - Domains: {len(ontology.domains)}")
            print(f"    - Concepts: {len(ontology.concepts)}")
            print(f"    - File size: {file_size / 1024:.1f} KB")
            print(f"    - Save time: {save_time:.4f}s")
            print(f"    - Load time: {load_time:.4f}s")
            
            # Assertions
            assert save_time < 1.0, f"Save took {save_time:.4f}s, expected < 1s"
            assert load_time < 1.0, f"Load took {load_time:.4f}s, expected < 1s"
            assert len(loaded.domains) == len(ontology.domains)
            assert len(loaded.concepts) == len(ontology.concepts)
    
    def test_concurrent_mapping_queries(self):
        """Test query performance under simulated concurrent load."""
        # Setup
        data = {
            f"table_{i}": pd.DataFrame({
                "id": range(100),
                "value": [f"val_{j}" for j in range(100)]
            })
            for i in range(50)
        }
        
        semantic_model = SemanticModel(data, domain="Test")
        ontology = BusinessOntology("Test", "Test", "1.0")
        ontology.add_domain("TestDomain", "Test", DomainType.PRODUCT)
        
        for i in range(50):
            ontology.add_concept(
                name=f"Concept_{i}",
                domain="TestDomain",
                description="Test concept",
                status=ConceptStatus.APPROVED
            )
        
        cdm_catalog = CDMCatalog.load_builtin("cdm_core")
        mapper = OntologyMapper(semantic_model, ontology, cdm_catalog)
        
        # Create mappings
        for i in range(50):
            mapper.map_entity(f"table_{i}", f"Concept_{i}", status="approved")
        
        # Simulate 1000 concurrent queries
        query_start = time.time()
        results = []
        for _ in range(1000):
            # Random queries
            results.append(mapper.get_mapping(f"table_{_ % 50}"))
            if _ % 10 == 0:
                results.append(mapper.get_unmapped_semantic_entities())
            if _ % 20 == 0:
                results.append(mapper.get_mapping_summary())
        
        query_time = time.time() - query_start
        avg_query_time = query_time / 1000
        
        print(f"\n  Concurrent query metrics:")
        print(f"    - Total queries: 1000")
        print(f"    - Total time: {query_time:.3f}s")
        print(f"    - Avg query time: {avg_query_time*1000:.2f}ms")
        print(f"    - Queries per second: {1000/query_time:.1f}")
        
        # Assertions
        assert query_time < 5.0, f"1000 queries took {query_time:.2f}s, expected < 5s"
        assert avg_query_time < 0.005, f"Avg query {avg_query_time*1000:.2f}ms, expected < 5ms"


class TestMemoryEfficiency:
    """Test memory efficiency of CDM operations."""
    
    def test_catalog_memory_footprint(self):
        """Test memory usage of large catalogs."""
        import sys
        
        catalog = CDMCatalog(name="Memory Test")
        
        # Add entities
        from intugle.models.cdm.entities import CDMEntity, CDMAttribute
        for i in range(100):
            entity = CDMEntity(name=f"Entity_{i}", description=f"Test {i}")
            for j in range(50):
                entity.add_attribute(CDMAttribute(
                    name=f"attr_{j}",
                    data_type="string",
                    description=f"Attribute {j}"
                ))
            catalog.add_entity(entity)
        
        # Rough size estimation
        size = sys.getsizeof(catalog)
        entity_count = len(catalog.entities)
        total_attrs = sum(len(e.attributes) for e in catalog.entities.values())
        
        print(f"\n  Memory efficiency metrics:")
        print(f"    - Catalog size: ~{size:,} bytes")
        print(f"    - Entities: {entity_count}")
        print(f"    - Attributes: {total_attrs}")
        print(f"    - Bytes per entity: ~{size/entity_count:.0f}")
        
        # Basic assertion
        assert entity_count == 100
        assert total_attrs == 5000


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
