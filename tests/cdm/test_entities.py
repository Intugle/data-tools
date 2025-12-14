"""Unit tests for CDM entities and attributes."""

import pytest

from intugle.models.cdm.entities import CDMAttribute, CDMEntity


class TestCDMAttribute:
    """Test suite for CDMAttribute."""
    
    def test_create_basic_attribute(self):
        """Test creating a basic CDM attribute."""
        attr = CDMAttribute(
            name="Email",
            data_type="string",
            is_nullable=True
        )
        
        assert attr.name == "Email"
        assert attr.data_type == "string"
        assert attr.is_nullable is True
        assert attr.display_name is None
        assert attr.description is None

    def test_create_attribute_with_full_details(self):
        """Test creating a CDM attribute with all fields."""
        attr = CDMAttribute(
            name="ContactId",
            display_name="Contact ID",
            description="Unique identifier for the contact",
            data_type="guid",
            is_nullable=False,
            max_length=None,
            metadata={"format": "uuid"}
        )
        
        assert attr.name == "ContactId"
        assert attr.display_name == "Contact ID"
        assert attr.description == "Unique identifier for the contact"
        assert attr.data_type == "guid"
        assert attr.is_nullable is False
        assert attr.metadata["format"] == "uuid"

    def test_attribute_string_representation(self):
        """Test string representation of CDM attribute."""
        attr = CDMAttribute(name="Email", data_type="string")
        assert "Email" in str(attr)
        assert "string" in str(attr)


class TestCDMEntity:
    """Test suite for CDMEntity."""
    
    def test_create_basic_entity(self):
        """Test creating a basic CDM entity."""
        entity = CDMEntity(
            name="Contact",
            namespace="core.applicationCommon"
        )
        
        assert entity.name == "Contact"
        assert entity.namespace == "core.applicationCommon"
        assert entity.version == "1.0"
        assert len(entity.attributes) == 0

    def test_create_entity_with_details(self):
        """Test creating a CDM entity with full details."""
        entity = CDMEntity(
            name="Account",
            namespace="core.applicationCommon",
            display_name="Account",
            description="Business account entity",
            version="2.0",
            metadata={"category": "customer"}
        )
        
        assert entity.name == "Account"
        assert entity.display_name == "Account"
        assert entity.description == "Business account entity"
        assert entity.version == "2.0"
        assert entity.metadata["category"] == "customer"

    def test_add_attribute(self):
        """Test adding attributes to an entity."""
        entity = CDMEntity(name="Contact", namespace="core.applicationCommon")
        
        attr1 = CDMAttribute(name="ContactId", data_type="guid")
        attr2 = CDMAttribute(name="Email", data_type="string")
        
        entity.add_attribute(attr1)
        entity.add_attribute(attr2)
        
        assert len(entity.attributes) == 2
        assert entity.attributes[0].name == "ContactId"
        assert entity.attributes[1].name == "Email"

    def test_add_duplicate_attribute(self):
        """Test that adding duplicate attributes doesn't create duplicates."""
        entity = CDMEntity(name="Contact", namespace="core.applicationCommon")
        
        attr1 = CDMAttribute(name="Email", data_type="string")
        attr2 = CDMAttribute(name="Email", data_type="string")
        
        entity.add_attribute(attr1)
        entity.add_attribute(attr2)
        
        # Should only have one attribute
        assert len(entity.attributes) == 1

    def test_get_attribute(self):
        """Test retrieving an attribute by name."""
        entity = CDMEntity(name="Contact", namespace="core.applicationCommon")
        
        attr = CDMAttribute(name="Email", data_type="string")
        entity.add_attribute(attr)
        
        retrieved = entity.get_attribute("Email")
        assert retrieved is not None
        assert retrieved.name == "Email"
        
        not_found = entity.get_attribute("NonExistent")
        assert not_found is None

    def test_full_name_property(self):
        """Test the full_name property."""
        entity = CDMEntity(name="Account", namespace="core.applicationCommon")
        assert entity.full_name == "core.applicationCommon.Account"

    def test_entity_string_representation(self):
        """Test string representation of CDM entity."""
        entity = CDMEntity(
            name="Contact",
            namespace="core.applicationCommon"
        )
        entity.add_attribute(CDMAttribute(name="Email", data_type="string"))
        
        entity_str = str(entity)
        assert "Contact" in entity_str
        assert "core.applicationCommon" in entity_str
        assert "1" in entity_str  # Number of attributes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
