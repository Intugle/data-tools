# -*- coding: utf-8 -*-
"""
Example: Business Ontology Layer with Microsoft CDM Support

This example demonstrates how to use the business ontology layer to map
a semantic model to Microsoft Common Data Model entities.
"""

import sys
import io
import pandas as pd

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from intugle import (
    BusinessOntology,
    CDMCatalog,
    OntologyMapper,
    SemanticModel,
)


def main():
    # Sample data for demonstration
    customer_data = pd.DataFrame({
        "customer_id": [1, 2, 3, 4, 5],
        "email": ["alice@example.com", "bob@example.com", "charlie@example.com", 
                  "diana@example.com", "eve@example.com"],
        "full_name": ["Alice Smith", "Bob Jones", "Charlie Brown", "Diana Prince", "Eve Wilson"],
        "phone": ["555-0001", "555-0002", "555-0003", "555-0004", "555-0005"]
    })
    
    account_data = pd.DataFrame({
        "account_id": [101, 102, 103],
        "account_name": ["Acme Corp", "TechStart Inc", "Global Solutions"],
        "account_balance": [50000.00, 75000.00, 120000.00]
    })
    
    sales_order_data = pd.DataFrame({
        "order_id": [1001, 1002, 1003, 1004],
        "order_date": pd.to_datetime(["2024-01-15", "2024-01-16", "2024-01-17", "2024-01-18"]),
        "customer_id": [1, 2, 1, 3],
        "total_amount": [1500.00, 2300.00, 890.00, 3200.00]
    })
    
    data_dict = {
        "customer": customer_data,
        "account": account_data,
        "sales_order_header": sales_order_data
    }
    
    print("=" * 80)
    print("Business Ontology Layer Example - Microsoft CDM Integration")
    print("=" * 80)
    print()
    
    # 1. Load the existing semantic data model
    print("Step 1: Creating semantic model from data...")
    semantic_model = SemanticModel(data_dict, domain="E-commerce")
    print(f"✓ Created semantic model with {len(semantic_model.datasets)} datasets")
    print(f"  Datasets: {', '.join(semantic_model.datasets.keys())}")
    print()
    
    # 2. Load or initialize the Microsoft CDM catalog
    print("Step 2: Loading Microsoft CDM catalog...")
    cdm_catalog = CDMCatalog.load_builtin("cdm_core")
    print(f"✓ Loaded CDM catalog: {cdm_catalog.name}")
    print(f"  Available entities: {', '.join(cdm_catalog.list_entities()[:5])}...")
    print()
    
    # Also load sales catalog
    sales_catalog = CDMCatalog.load_builtin("cdm_sales")
    print(f"✓ Loaded sales catalog: {sales_catalog.name}")
    print(f"  Available entities: {', '.join(sales_catalog.list_entities())}")
    print()
    
    # 3. Create / load a business ontology
    print("Step 3: Creating business ontology...")
    business_ontology = BusinessOntology(name="Enterprise Business Ontology (CDM)")
    print(f"✓ Created business ontology: {business_ontology.name}")
    print()
    
    # Define domains
    print("Step 4: Defining business domains...")
    business_ontology.add_domain(
        name="CustomerDomain",
        description="All customer and account-related concepts"
    )
    business_ontology.add_domain(
        name="SalesDomain",
        description="Sales orders, invoices, and related concepts"
    )
    print(f"✓ Added {len(business_ontology.domains)} domains")
    for domain_name in business_ontology.list_domains():
        domain = business_ontology.get_domain(domain_name)
        print(f"  - {domain_name}: {domain.description}")
    print()
    
    # Define business concepts linked to CDM entities
    print("Step 5: Defining business concepts linked to CDM entities...")
    
    customer_concept = business_ontology.add_concept(
        name="Customer",
        domain="CustomerDomain",
        cdm_entity=cdm_catalog.get_entity("Contact"),
    )
    print(f"✓ Added concept: {customer_concept.name} -> CDM:{customer_concept.cdm_entity_name}")
    
    account_concept = business_ontology.add_concept(
        name="Account",
        domain="CustomerDomain",
        cdm_entity=cdm_catalog.get_entity("Account"),
    )
    print(f"✓ Added concept: {account_concept.name} -> CDM:{account_concept.cdm_entity_name}")
    
    sales_order_concept = business_ontology.add_concept(
        name="SalesOrder",
        domain="SalesDomain",
        cdm_entity=sales_catalog.get_entity("SalesOrder"),
    )
    print(f"✓ Added concept: {sales_order_concept.name} -> CDM:{sales_order_concept.cdm_entity_name}")
    print()
    
    # 4. Map semantic entities to business concepts / CDM
    print("Step 6: Mapping semantic entities to business concepts and CDM...")
    mapper = OntologyMapper(semantic_model, business_ontology, cdm_catalog)
    print(f"✓ Created ontology mapper")
    print()
    
    print("Mapping: semantic.customer -> Business Concept: Customer -> CDM: Contact")
    mapper.map_entity(
        semantic_entity="customer",
        concept="Customer",
        attribute_map={
            "customer_id": "Contact.ContactId",
            "email": "Contact.Email",
            "full_name": "Contact.FullName",
            "phone": "Contact.PhoneNumber",
        },
    )
    print("✓ Mapped customer entity with 4 attributes")
    print()
    
    print("Mapping: semantic.account -> Business Concept: Account -> CDM: Account")
    mapper.map_entity(
        semantic_entity="account",
        concept="Account",
        attribute_map={
            "account_id": "Account.AccountId",
            "account_name": "Account.Name",
            "account_balance": "Account.Balance",
        },
    )
    print("✓ Mapped account entity with 3 attributes")
    print()
    
    print("Mapping: semantic.sales_order_header -> Business Concept: SalesOrder -> CDM: SalesOrder")
    mapper.map_entity(
        semantic_entity="sales_order_header",
        concept="SalesOrder",
        attribute_map={
            "order_id": "SalesOrder.SalesOrderId",
            "order_date": "SalesOrder.OrderDate",
            "customer_id": "SalesOrder.CustomerId",
            "total_amount": "SalesOrder.TotalAmount",
        },
    )
    print("✓ Mapped sales_order_header entity with 4 attributes")
    print()
    
    # 5. Query and analyze mappings
    print("=" * 80)
    print("Mapping Analysis")
    print("=" * 80)
    print()
    
    summary = mapper.get_mapping_summary()
    print(f"Total mappings: {summary['total_mappings']}")
    print(f"Unmapped semantic entities: {summary['unmapped_semantic_entities']}")
    print(f"Unmapped CDM entities: {summary['unmapped_cdm_entities']}")
    print()
    
    print("Mappings by status:")
    for status, count in summary['mappings_by_status'].items():
        print(f"  - {status}: {count}")
    print()
    
    print("Mappings by type:")
    for map_type, count in summary['mappings_by_type'].items():
        print(f"  - {map_type}: {count}")
    print()
    
    # Query specific mappings
    print("Query: Which semantic entities map to CDM Contact?")
    contact_mappings = mapper.get_mappings_by_cdm_entity("Contact")
    for mapping in contact_mappings:
        print(f"  - {', '.join(mapping.semantic_entities)} -> {mapping.concept_name}")
    print()
    
    print("Query: Which CDM entities are in CustomerDomain?")
    customer_concepts = business_ontology.get_concepts_by_domain("CustomerDomain")
    for concept in customer_concepts:
        print(f"  - {concept.name} -> CDM:{concept.cdm_entity_name}")
    print()
    
    # 6. Save ontology + mappings
    print("=" * 80)
    print("Saving Ontology and Mappings")
    print("=" * 80)
    print()
    
    print("Saving business ontology...")
    business_ontology.save("business_ontology_cdm.json")
    print("✓ Saved to: business_ontology_cdm.json")
    print()
    
    print("Saving semantic-to-CDM mappings...")
    mapper.export_mappings("semantic_to_cdm_mappings.json")
    print("✓ Saved to: semantic_to_cdm_mappings.json")
    print()
    
    print("=" * 80)
    print("Example Complete!")
    print("=" * 80)
    print()
    print("Key capabilities demonstrated:")
    print("  ✓ Business domain organization (CustomerDomain, SalesDomain)")
    print("  ✓ Business concepts aligned with CDM entities")
    print("  ✓ Semantic model to CDM mappings at entity and attribute level")
    print("  ✓ Query and analysis of mappings")
    print("  ✓ Persistence of ontology and mappings")
    print()
    print("Next steps:")
    print("  - Extend to other CDM catalogs (FIBO, custom ontologies)")
    print("  - Use mappings for data product generation")
    print("  - Integrate with governance and cataloging tools")
    print()


if __name__ == "__main__":
    main()
