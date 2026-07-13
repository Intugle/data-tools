"""CDM Catalog for managing Microsoft CDM entities."""

import json
import logging
import os

from typing import Dict, List, Optional

from intugle.models.cdm.entities import CDMAttribute, CDMEntity

log = logging.getLogger(__name__)


class CDMCatalog:
    """
    A catalog of Microsoft Common Data Model entities.
    
    The CDM Catalog provides access to CDM entity definitions and serves as
    the reference for mapping semantic models to CDM concepts.
    
    Attributes:
        name: Name of the catalog (e.g., "CDM Core", "CDM Sales").
        entities: Dictionary mapping entity names to CDMEntity objects.
    """
    
    def __init__(self, name: str = "Microsoft CDM"):
        self.name = name
        self.entities: Dict[str, CDMEntity] = {}

    def add_entity(self, entity: CDMEntity) -> None:
        """
        Add a CDM entity to the catalog.
        
        Args:
            entity: The CDMEntity to add.
        """
        self.entities[entity.name] = entity
        log.debug(f"Added CDM entity '{entity.name}' to catalog '{self.name}'")

    def get_entity(self, name: str) -> Optional[CDMEntity]:
        """
        Retrieve a CDM entity by name.
        
        Args:
            name: The entity name to search for.
            
        Returns:
            The CDMEntity if found, None otherwise.
        """
        return self.entities.get(name)

    def list_entities(self) -> List[str]:
        """
        List all entity names in the catalog.
        
        Returns:
            List of entity names.
        """
        return list(self.entities.keys())

    def search_entities(self, keyword: str) -> List[CDMEntity]:
        """
        Search for entities matching a keyword in name or description.
        
        Args:
            keyword: The keyword to search for (case-insensitive).
            
        Returns:
            List of matching CDMEntity objects.
        """
        keyword_lower = keyword.lower()
        matches = []
        for entity in self.entities.values():
            if keyword_lower in entity.name.lower():
                matches.append(entity)
            elif entity.description and keyword_lower in entity.description.lower():
                matches.append(entity)
        return matches

    def save(self, file_path: str) -> None:
        """
        Save the CDM catalog to a JSON file.
        
        Args:
            file_path: Path where the catalog should be saved.
        """
        catalog_data = {
            "name": self.name,
            "entities": [
                entity.model_dump() for entity in self.entities.values()
            ]
        }
        
        dir_path = os.path.dirname(file_path)
        if dir_path:  # Only create directories if there's a directory path
            os.makedirs(dir_path, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(catalog_data, f, indent=2)
        
        log.info(f"CDM catalog saved to {file_path}")

    @classmethod
    def load(cls, file_path: str) -> "CDMCatalog":
        """
        Load a CDM catalog from a JSON file.
        
        Args:
            file_path: Path to the catalog file.
            
        Returns:
            A CDMCatalog instance.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            catalog_data = json.load(f)
        
        catalog = cls(name=catalog_data.get("name", "Microsoft CDM"))
        
        for entity_data in catalog_data.get("entities", []):
            entity = CDMEntity(**entity_data)
            catalog.add_entity(entity)
        
        log.info(f"CDM catalog loaded from {file_path}")
        return catalog

    @classmethod
    def load_builtin(cls, catalog_name: str = "cdm_core") -> "CDMCatalog":
        """
        Load a built-in CDM catalog that ships with intugle.
        
        Args:
            catalog_name: Name of the built-in catalog to load.
                         Options: "cdm_core", "cdm_sales", "cdm_service"
            
        Returns:
            A CDMCatalog instance with built-in entities.
        """
        catalog = cls(name=f"Microsoft CDM - {catalog_name}")
        
        # Define core CDM entities that ship with intugle
        if catalog_name == "cdm_core":
            catalog = cls._load_cdm_core()
        elif catalog_name == "cdm_sales":
            catalog = cls._load_cdm_sales()
        elif catalog_name == "cdm_service":
            catalog = cls._load_cdm_service()
        else:
            log.warning(f"Unknown built-in catalog '{catalog_name}', loading empty catalog")
        
        return catalog

    @classmethod
    def _load_cdm_core(cls) -> "CDMCatalog":
        """Load core CDM entities (Account, Contact, etc.)."""
        catalog = cls(name="Microsoft CDM - Core")
        
        # Account entity
        account = CDMEntity(
            name="Account",
            namespace="core.applicationCommon",
            display_name="Account",
            description="Business that represents a customer or potential customer.",
            version="1.0"
        )
        account.add_attribute(CDMAttribute(
            name="AccountId",
            display_name="Account ID",
            description="Unique identifier for the account",
            data_type="guid",
            is_nullable=False
        ))
        account.add_attribute(CDMAttribute(
            name="Name",
            display_name="Account Name",
            description="Name of the account",
            data_type="string",
            max_length=160
        ))
        account.add_attribute(CDMAttribute(
            name="AccountNumber",
            display_name="Account Number",
            description="Unique account number for reference",
            data_type="string",
            max_length=20
        ))
        account.add_attribute(CDMAttribute(
            name="Balance",
            display_name="Balance",
            description="Current account balance",
            data_type="decimal"
        ))
        account.add_attribute(CDMAttribute(
            name="CreditLimit",
            display_name="Credit Limit",
            description="Credit limit for the account",
            data_type="decimal"
        ))
        catalog.add_entity(account)
        
        # Contact entity
        contact = CDMEntity(
            name="Contact",
            namespace="core.applicationCommon",
            display_name="Contact",
            description="Person with whom a business unit has a relationship.",
            version="1.0"
        )
        contact.add_attribute(CDMAttribute(
            name="ContactId",
            display_name="Contact ID",
            description="Unique identifier for the contact",
            data_type="guid",
            is_nullable=False
        ))
        contact.add_attribute(CDMAttribute(
            name="FullName",
            display_name="Full Name",
            description="Full name of the contact",
            data_type="string",
            max_length=160
        ))
        contact.add_attribute(CDMAttribute(
            name="FirstName",
            display_name="First Name",
            description="First name of the contact",
            data_type="string",
            max_length=50
        ))
        contact.add_attribute(CDMAttribute(
            name="LastName",
            display_name="Last Name",
            description="Last name of the contact",
            data_type="string",
            max_length=50
        ))
        contact.add_attribute(CDMAttribute(
            name="Email",
            display_name="Email",
            description="Email address of the contact",
            data_type="string",
            max_length=100
        ))
        contact.add_attribute(CDMAttribute(
            name="PhoneNumber",
            display_name="Phone Number",
            description="Phone number of the contact",
            data_type="string",
            max_length=50
        ))
        catalog.add_entity(contact)
        
        # Address entity
        address = CDMEntity(
            name="Address",
            namespace="core.applicationCommon",
            display_name="Address",
            description="Physical address information.",
            version="1.0"
        )
        address.add_attribute(CDMAttribute(
            name="AddressId",
            display_name="Address ID",
            description="Unique identifier for the address",
            data_type="guid",
            is_nullable=False
        ))
        address.add_attribute(CDMAttribute(
            name="Line1",
            display_name="Street 1",
            description="First line of the street address",
            data_type="string",
            max_length=250
        ))
        address.add_attribute(CDMAttribute(
            name="City",
            display_name="City",
            description="City name",
            data_type="string",
            max_length=80
        ))
        address.add_attribute(CDMAttribute(
            name="StateOrProvince",
            display_name="State/Province",
            description="State or province",
            data_type="string",
            max_length=50
        ))
        address.add_attribute(CDMAttribute(
            name="PostalCode",
            display_name="Postal Code",
            description="ZIP or postal code",
            data_type="string",
            max_length=20
        ))
        address.add_attribute(CDMAttribute(
            name="Country",
            display_name="Country",
            description="Country/region",
            data_type="string",
            max_length=80
        ))
        catalog.add_entity(address)
        
        return catalog

    @classmethod
    def _load_cdm_sales(cls) -> "CDMCatalog":
        """Load sales-related CDM entities."""
        catalog = cls(name="Microsoft CDM - Sales")
        
        # SalesOrder entity
        sales_order = CDMEntity(
            name="SalesOrder",
            namespace="core.applicationCommon.foundationCommon.crmCommon.sales",
            display_name="Sales Order",
            description="Order that has been placed for products.",
            version="1.0"
        )
        sales_order.add_attribute(CDMAttribute(
            name="SalesOrderId",
            display_name="Sales Order ID",
            description="Unique identifier for the sales order",
            data_type="guid",
            is_nullable=False
        ))
        sales_order.add_attribute(CDMAttribute(
            name="OrderNumber",
            display_name="Order Number",
            description="Order number for customer reference",
            data_type="string",
            max_length=100
        ))
        sales_order.add_attribute(CDMAttribute(
            name="OrderDate",
            display_name="Order Date",
            description="Date when the order was placed",
            data_type="datetime"
        ))
        sales_order.add_attribute(CDMAttribute(
            name="CustomerId",
            display_name="Customer ID",
            description="Reference to the customer",
            data_type="guid"
        ))
        sales_order.add_attribute(CDMAttribute(
            name="TotalAmount",
            display_name="Total Amount",
            description="Total order amount",
            data_type="decimal"
        ))
        sales_order.add_attribute(CDMAttribute(
            name="Status",
            display_name="Status",
            description="Current status of the order",
            data_type="string",
            max_length=50
        ))
        catalog.add_entity(sales_order)
        
        # SalesOrderLine entity
        sales_order_line = CDMEntity(
            name="SalesOrderLine",
            namespace="core.applicationCommon.foundationCommon.crmCommon.sales",
            display_name="Sales Order Line",
            description="Line item in a sales order.",
            version="1.0"
        )
        sales_order_line.add_attribute(CDMAttribute(
            name="SalesOrderLineId",
            display_name="Sales Order Line ID",
            description="Unique identifier for the order line",
            data_type="guid",
            is_nullable=False
        ))
        sales_order_line.add_attribute(CDMAttribute(
            name="SalesOrderId",
            display_name="Sales Order ID",
            description="Reference to the parent sales order",
            data_type="guid"
        ))
        sales_order_line.add_attribute(CDMAttribute(
            name="ProductId",
            display_name="Product ID",
            description="Reference to the product",
            data_type="guid"
        ))
        sales_order_line.add_attribute(CDMAttribute(
            name="Quantity",
            display_name="Quantity",
            description="Quantity ordered",
            data_type="decimal"
        ))
        sales_order_line.add_attribute(CDMAttribute(
            name="UnitPrice",
            display_name="Unit Price",
            description="Price per unit",
            data_type="decimal"
        ))
        sales_order_line.add_attribute(CDMAttribute(
            name="LineTotal",
            display_name="Line Total",
            description="Total amount for the line",
            data_type="decimal"
        ))
        catalog.add_entity(sales_order_line)
        
        # Product entity
        product = CDMEntity(
            name="Product",
            namespace="core.applicationCommon.foundationCommon.crmCommon.products",
            display_name="Product",
            description="Information about products and their pricing.",
            version="1.0"
        )
        product.add_attribute(CDMAttribute(
            name="ProductId",
            display_name="Product ID",
            description="Unique identifier for the product",
            data_type="guid",
            is_nullable=False
        ))
        product.add_attribute(CDMAttribute(
            name="ProductNumber",
            display_name="Product Number",
            description="User-defined product number",
            data_type="string",
            max_length=100
        ))
        product.add_attribute(CDMAttribute(
            name="Name",
            display_name="Product Name",
            description="Name of the product",
            data_type="string",
            max_length=100
        ))
        product.add_attribute(CDMAttribute(
            name="Description",
            display_name="Description",
            description="Description of the product",
            data_type="string",
            max_length=2000
        ))
        product.add_attribute(CDMAttribute(
            name="Price",
            display_name="Price",
            description="List price of the product",
            data_type="decimal"
        ))
        catalog.add_entity(product)
        
        # Invoice entity
        invoice = CDMEntity(
            name="Invoice",
            namespace="core.applicationCommon.foundationCommon.crmCommon.sales",
            display_name="Invoice",
            description="Invoice for products delivered to a customer.",
            version="1.0"
        )
        invoice.add_attribute(CDMAttribute(
            name="InvoiceId",
            display_name="Invoice ID",
            description="Unique identifier for the invoice",
            data_type="guid",
            is_nullable=False
        ))
        invoice.add_attribute(CDMAttribute(
            name="InvoiceNumber",
            display_name="Invoice Number",
            description="Invoice number for customer reference",
            data_type="string",
            max_length=100
        ))
        invoice.add_attribute(CDMAttribute(
            name="InvoiceDate",
            display_name="Invoice Date",
            description="Date when the invoice was created",
            data_type="datetime"
        ))
        invoice.add_attribute(CDMAttribute(
            name="CustomerId",
            display_name="Customer ID",
            description="Reference to the customer",
            data_type="guid"
        ))
        invoice.add_attribute(CDMAttribute(
            name="TotalAmount",
            display_name="Total Amount",
            description="Total invoice amount",
            data_type="decimal"
        ))
        catalog.add_entity(invoice)
        
        return catalog

    @classmethod
    def _load_cdm_service(cls) -> "CDMCatalog":
        """Load service-related CDM entities."""
        catalog = cls(name="Microsoft CDM - Service")
        
        # Case entity
        case = CDMEntity(
            name="Case",
            namespace="core.applicationCommon.foundationCommon.crmCommon.service",
            display_name="Case",
            description="Service request case associated with a customer.",
            version="1.0"
        )
        case.add_attribute(CDMAttribute(
            name="CaseId",
            display_name="Case ID",
            description="Unique identifier for the case",
            data_type="guid",
            is_nullable=False
        ))
        case.add_attribute(CDMAttribute(
            name="CaseNumber",
            display_name="Case Number",
            description="Case number for customer reference",
            data_type="string",
            max_length=100
        ))
        case.add_attribute(CDMAttribute(
            name="Title",
            display_name="Title",
            description="Title of the case",
            data_type="string",
            max_length=200
        ))
        case.add_attribute(CDMAttribute(
            name="Description",
            display_name="Description",
            description="Detailed description of the case",
            data_type="string"
        ))
        case.add_attribute(CDMAttribute(
            name="CustomerId",
            display_name="Customer ID",
            description="Reference to the customer",
            data_type="guid"
        ))
        case.add_attribute(CDMAttribute(
            name="Priority",
            display_name="Priority",
            description="Priority of the case",
            data_type="string",
            max_length=50
        ))
        case.add_attribute(CDMAttribute(
            name="Status",
            display_name="Status",
            description="Current status of the case",
            data_type="string",
            max_length=50
        ))
        catalog.add_entity(case)
        
        return catalog

    def __str__(self) -> str:
        return f"CDMCatalog(name='{self.name}', entities={len(self.entities)})"

    def __repr__(self) -> str:
        return f"CDMCatalog(name={self.name!r}, entities={list(self.entities.keys())!r})"
