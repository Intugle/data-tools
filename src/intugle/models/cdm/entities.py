"""CDM Entity and Attribute models."""

from typing import Any, Dict, List, Optional

from pydantic import Field

from intugle.common.schema import SchemaBase


class CDMAttribute(SchemaBase):
    """
    Represents an attribute within a Microsoft CDM entity.
    
    Attributes:
        name: The name of the attribute (e.g., "ContactId", "Email").
        display_name: Human-readable display name.
        description: Description of what this attribute represents.
        data_type: The CDM data type (e.g., "string", "integer", "datetime").
        is_nullable: Whether the attribute can be null.
        max_length: Maximum length for string attributes.
        metadata: Additional custom metadata.
    """
    
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    data_type: str = "string"
    is_nullable: bool = True
    max_length: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def __str__(self) -> str:
        return f"CDMAttribute(name='{self.name}', data_type='{self.data_type}')"


class CDMEntity(SchemaBase):
    """
    Represents a Microsoft Common Data Model entity.
    
    An entity in CDM is analogous to a table or class - it represents a business concept
    with defined attributes.
    
    Attributes:
        name: The CDM entity name (e.g., "Account", "Contact", "SalesOrder").
        namespace: The CDM namespace (e.g., "core.applicationCommon").
        display_name: Human-readable display name.
        description: Description of what this entity represents.
        version: CDM schema version.
        attributes: List of attributes that belong to this entity.
        metadata: Additional custom metadata.
    """
    
    name: str
    namespace: str = "core.applicationCommon"
    display_name: Optional[str] = None
    description: Optional[str] = None
    version: str = "1.0"
    attributes: List[CDMAttribute] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_attribute(self, name: str) -> Optional[CDMAttribute]:
        """
        Retrieve a CDM attribute by name.
        
        Args:
            name: The attribute name to search for.
            
        Returns:
            The CDMAttribute if found, None otherwise.
        """
        for attr in self.attributes:
            if attr.name == name:
                return attr
        return None

    def add_attribute(self, attribute: CDMAttribute) -> None:
        """
        Add an attribute to this entity.
        
        Args:
            attribute: The CDMAttribute to add.
        """
        if not self.get_attribute(attribute.name):
            self.attributes.append(attribute)

    @property
    def full_name(self) -> str:
        """Return the fully qualified CDM entity name."""
        return f"{self.namespace}.{self.name}"

    def __str__(self) -> str:
        return f"CDMEntity(name='{self.name}', namespace='{self.namespace}', attributes={len(self.attributes)})"
