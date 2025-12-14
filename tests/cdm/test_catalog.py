"""Unit tests for CDM Catalog."""

import json
import os
import tempfile

import pytest

from intugle.models.cdm.catalog import CDMCatalog
from intugle.models.cdm.entities import CDMAttribute, CDMEntity


class TestCDMCatalog:
    """Test suite for CDM Catalog."""
    
    def test_create_empty_catalog(self):
        """Test creating an empty catalog."""
        catalog = CDMCatalog(name="Test Catalog")
        
        assert catalog.name == "Test Catalog"
        assert len(catalog.entities) == 0
        assert catalog.list_entities() == []

    def test_add_entity(self):
        """Test adding entities to the catalog."""
        catalog = CDMCatalog(name="Test Catalog")
        
        entity = CDMEntity(name="Contact", namespace="core.applicationCommon")
        catalog.add_entity(entity)
        
        assert len(catalog.entities) == 1
        assert "Contact" in catalog.entities
        assert catalog.list_entities() == ["Contact"]

    def test_get_entity(self):
        """Test retrieving entities from the catalog."""
        catalog = CDMCatalog(name="Test Catalog")
        
        entity = CDMEntity(name="Account", namespace="core.applicationCommon")
        catalog.add_entity(entity)
        
        retrieved = catalog.get_entity("Account")
        assert retrieved is not None
        assert retrieved.name == "Account"
        
        not_found = catalog.get_entity("NonExistent")
        assert not_found is None

    def test_search_entities_by_name(self):
        """Test searching entities by keyword in name."""
        catalog = CDMCatalog(name="Test Catalog")
        
        catalog.add_entity(CDMEntity(name="Account", namespace="core"))
        catalog.add_entity(CDMEntity(name="Contact", namespace="core"))
        catalog.add_entity(CDMEntity(name="SalesOrder", namespace="core"))
        
        results = catalog.search_entities("account")
        assert len(results) == 1
        assert results[0].name == "Account"

    def test_search_entities_by_description(self):
        """Test searching entities by keyword in description."""
        catalog = CDMCatalog(name="Test Catalog")
        
        catalog.add_entity(CDMEntity(
            name="Entity1",
            namespace="core",
            description="This is about customers"
        ))
        catalog.add_entity(CDMEntity(
            name="Entity2",
            namespace="core",
            description="This is about products"
        ))
        
        results = catalog.search_entities("customer")
        assert len(results) == 1
        assert results[0].name == "Entity1"

    def test_save_and_load_catalog(self):
        """Test saving and loading a catalog."""
        # Create a catalog with entities
        catalog = CDMCatalog(name="Test Catalog")
        
        entity = CDMEntity(name="Contact", namespace="core.applicationCommon")
        entity.add_attribute(CDMAttribute(name="ContactId", data_type="guid"))
        entity.add_attribute(CDMAttribute(name="Email", data_type="string"))
        catalog.add_entity(entity)
        
        # Save to temp file
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "catalog.json")
            catalog.save(file_path)
            
            # Load it back
            loaded_catalog = CDMCatalog.load(file_path)
            
            assert loaded_catalog.name == "Test Catalog"
            assert len(loaded_catalog.entities) == 1
            
            loaded_entity = loaded_catalog.get_entity("Contact")
            assert loaded_entity is not None
            assert loaded_entity.name == "Contact"
            assert len(loaded_entity.attributes) == 2

    def test_load_builtin_cdm_core(self):
        """Test loading the built-in CDM core catalog."""
        catalog = CDMCatalog.load_builtin("cdm_core")
        
        assert catalog.name == "Microsoft CDM - Core"
        assert len(catalog.entities) > 0
        
        # Check for expected core entities
        assert catalog.get_entity("Account") is not None
        assert catalog.get_entity("Contact") is not None
        assert catalog.get_entity("Address") is not None

    def test_load_builtin_cdm_sales(self):
        """Test loading the built-in CDM sales catalog."""
        catalog = CDMCatalog.load_builtin("cdm_sales")
        
        assert catalog.name == "Microsoft CDM - Sales"
        assert len(catalog.entities) > 0
        
        # Check for expected sales entities
        assert catalog.get_entity("SalesOrder") is not None
        assert catalog.get_entity("Product") is not None
        assert catalog.get_entity("Invoice") is not None

    def test_load_builtin_cdm_service(self):
        """Test loading the built-in CDM service catalog."""
        catalog = CDMCatalog.load_builtin("cdm_service")
        
        assert catalog.name == "Microsoft CDM - Service"
        assert len(catalog.entities) > 0
        
        # Check for expected service entities
        assert catalog.get_entity("Case") is not None

    def test_builtin_entities_have_attributes(self):
        """Test that built-in entities have proper attributes."""
        catalog = CDMCatalog.load_builtin("cdm_core")
        
        account = catalog.get_entity("Account")
        assert account is not None
        assert len(account.attributes) > 0
        
        # Check for specific attributes
        assert account.get_attribute("AccountId") is not None
        assert account.get_attribute("Name") is not None
        assert account.get_attribute("Balance") is not None

    def test_catalog_string_representation(self):
        """Test string representation of catalog."""
        catalog = CDMCatalog(name="Test Catalog")
        catalog.add_entity(CDMEntity(name="Contact", namespace="core"))
        
        catalog_str = str(catalog)
        assert "Test Catalog" in catalog_str
        assert "1" in catalog_str  # Number of entities


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
