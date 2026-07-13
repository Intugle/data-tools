# -*- coding: utf-8 -*-
"""
Real-World Example: Financial Services Data Mapping to Microsoft CDM

This example demonstrates mapping financial services data (accounts, transactions,
customers) to CDM entities, showing practical banking/finance use case.
"""

import sys
import io
import pandas as pd
from datetime import datetime, timedelta
import random

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
from intugle.models.cdm.ontology import ConceptStatus, DomainType


def create_financial_data():
    """Create sample financial services data."""
    
    # Customer data
    customers = pd.DataFrame({
        "customer_id": [f"C{str(i).zfill(5)}" for i in range(1, 11)],
        "customer_type": ["Individual"] * 7 + ["Business"] * 3,
        "full_name": [
            "Alice Johnson", "Bob Williams", "Carol Davis", "David Martinez",
            "Eva Garcia", "Frank Miller", "Grace Wilson", 
            "Acme Corp", "Tech Solutions LLC", "Retail Enterprises Inc"
        ],
        "email": [
            "alice.j@email.com", "bob.w@email.com", "carol.d@email.com", "david.m@email.com",
            "eva.g@email.com", "frank.m@email.com", "grace.w@email.com",
            "contact@acme.com", "info@techsolutions.com", "admin@retailent.com"
        ],
        "phone": [f"555-{str(random.randint(1000, 9999))}" for _ in range(10)],
        "join_date": pd.to_datetime([
            datetime.now() - timedelta(days=random.randint(365, 3650)) for _ in range(10)
        ]),
        "credit_rating": ["A"] * 3 + ["B"] * 4 + ["A"] * 2 + ["B"],
        "kyc_status": ["Verified"] * 9 + ["Pending"]
    })
    
    # Account data
    accounts = pd.DataFrame({
        "account_id": [f"ACC{str(i).zfill(6)}" for i in range(1, 21)],
        "customer_id": [f"C{str(random.randint(1, 10)).zfill(5)}" for _ in range(20)],
        "account_type": (["Checking"] * 8 + ["Savings"] * 7 + ["Credit Card"] * 3 + 
                        ["Business Checking"] * 2),
        "account_number": [f"{random.randint(1000000000, 9999999999)}" for _ in range(20)],
        "open_date": pd.to_datetime([
            datetime.now() - timedelta(days=random.randint(30, 1825)) for _ in range(20)
        ]),
        "balance": [round(random.uniform(100, 50000), 2) for _ in range(20)],
        "currency": ["USD"] * 20,
        "status": ["Active"] * 18 + ["Closed", "Frozen"]
    })
    
    # Transaction data
    base_date = datetime.now() - timedelta(days=90)
    transactions = pd.DataFrame({
        "transaction_id": [f"TXN{str(i).zfill(8)}" for i in range(1, 101)],
        "account_id": [f"ACC{str(random.randint(1, 20)).zfill(6)}" for _ in range(100)],
        "transaction_date": pd.to_datetime([
            base_date + timedelta(days=random.randint(0, 90)) for _ in range(100)
        ]),
        "transaction_type": random.choices(
            ["Deposit", "Withdrawal", "Transfer", "Payment", "Fee"],
            weights=[30, 25, 20, 20, 5],
            k=100
        ),
        "amount": [round(random.uniform(10, 5000), 2) for _ in range(100)],
        "merchant": [
            f"Merchant_{random.randint(1, 50)}" if random.random() > 0.3 else None 
            for _ in range(100)
        ],
        "category": random.choices(
            ["Groceries", "Utilities", "Entertainment", "Healthcare", "Transfer", "Other"],
            k=100
        ),
        "status": ["Completed"] * 95 + ["Pending"] * 4 + ["Failed"]
    })
    
    # Loan data
    loans = pd.DataFrame({
        "loan_id": [f"LOAN{str(i).zfill(5)}" for i in range(1, 16)],
        "customer_id": [f"C{str(random.randint(1, 10)).zfill(5)}" for _ in range(15)],
        "loan_type": random.choices(
            ["Mortgage", "Auto", "Personal", "Business"],
            weights=[5, 4, 4, 2],
            k=15
        ),
        "principal_amount": [round(random.uniform(5000, 500000), 2) for _ in range(15)],
        "interest_rate": [round(random.uniform(3.5, 12.5), 2) for _ in range(15)],
        "term_months": [random.choice([12, 24, 36, 60, 120, 180, 360]) for _ in range(15)],
        "origination_date": pd.to_datetime([
            datetime.now() - timedelta(days=random.randint(180, 1825)) for _ in range(15)
        ]),
        "outstanding_balance": [round(random.uniform(1000, 400000), 2) for _ in range(15)],
        "status": ["Current"] * 12 + ["Delinquent", "Paid Off", "Current"]
    })
    
    return {
        "customers": customers,
        "accounts": accounts,
        "transactions": transactions,
        "loans": loans
    }


def main():
    print("=" * 80)
    print("Financial Services Data Mapping to Microsoft CDM - Real World Example")
    print("=" * 80)
    print()
    
    # Step 1: Create semantic model
    print("Step 1: Loading financial services data...")
    financial_data = create_financial_data()
    semantic_model = SemanticModel(financial_data, domain="Financial Services")
    
    print(f"✓ Created semantic model with {len(semantic_model.datasets)} datasets:")
    for name, dataset in semantic_model.datasets.items():
        row_count = len(dataset.data) if hasattr(dataset.data, '__len__') else "N/A"
        print(f"  - {name}: {row_count} records")
    print()
    
    # Step 2: Load CDM catalogs
    print("Step 2: Loading Microsoft CDM catalogs...")
    cdm_core = CDMCatalog.load_builtin("cdm_core")
    cdm_sales = CDMCatalog.load_builtin("cdm_sales")
    
    print(f"✓ Loaded CDM Core: {', '.join(cdm_core.list_entities()[:3])}...")
    print(f"✓ Loaded CDM Sales: {', '.join(cdm_sales.list_entities()[:3])}...")
    print()
    
    # Step 3: Create financial services ontology
    print("Step 3: Creating financial services business ontology...")
    ontology = BusinessOntology(
        name="Financial Services Enterprise Ontology (CDM)",
        description="Banking and financial services ontology aligned with Microsoft CDM",
        version="2.0"
    )
    
    # Define domains
    ontology.add_domain(
        name="CustomerDomain",
        description="Customer master data and relationships",
        domain_type=DomainType.CUSTOMER,
        owner="Customer Experience Department"
    )
    
    ontology.add_domain(
        name="AccountDomain",
        description="Banking accounts and products",
        domain_type=DomainType.PRODUCT,
        owner="Product Management"
    )
    
    ontology.add_domain(
        name="TransactionDomain",
        description="Financial transactions and payments",
        domain_type=DomainType.SALES,
        owner="Payments & Transactions"
    )
    
    ontology.add_domain(
        name="LendingDomain",
        description="Loans and credit products",
        domain_type=DomainType.FINANCE,
        owner="Lending Department"
    )
    
    print(f"✓ Created {len(ontology.domains)} business domains")
    print()
    
    # Step 4: Map to CDM
    print("Step 4: Mapping financial entities to CDM...")
    
    # Customer → CDM Account
    customer_concept = ontology.add_concept(
        name="BankCustomer",
        domain="CustomerDomain",
        cdm_entity=cdm_core.get_entity("Account"),
        description="Individual or business banking customer",
        status=ConceptStatus.APPROVED,
        owner="customer_data@bank.com",
        tags=["PII", "customer", "core"],
        display_name="Bank Customer"
    )
    print(f"✓ Mapped BankCustomer -> CDM:{customer_concept.cdm_entity_name}")
    
    # Account → CDM Product
    account_concept = ontology.add_concept(
        name="BankAccount",
        domain="AccountDomain",
        cdm_entity=cdm_sales.get_entity("Product"),
        description="Deposit and credit accounts",
        status=ConceptStatus.APPROVED,
        owner="product_data@bank.com",
        tags=["account", "product"]
    )
    print(f"✓ Mapped BankAccount -> CDM:{account_concept.cdm_entity_name}")
    
    # Transaction → CDM SalesOrder
    transaction_concept = ontology.add_concept(
        name="FinancialTransaction",
        domain="TransactionDomain",
        cdm_entity=cdm_sales.get_entity("SalesOrder"),
        description="All financial transactions",
        status=ConceptStatus.APPROVED,
        owner="transactions@bank.com",
        tags=["transaction", "payment"]
    )
    print(f"✓ Mapped FinancialTransaction -> CDM:{transaction_concept.cdm_entity_name}")
    
    # Loan → CDM Invoice (best fit from available CDM)
    loan_concept = ontology.add_concept(
        name="Loan",
        domain="LendingDomain",
        cdm_entity=cdm_sales.get_entity("Invoice"),
        description="Loan agreements and schedules",
        status=ConceptStatus.IN_REVIEW,
        owner="lending@bank.com",
        tags=["loan", "credit"],
        notes="Using CDM Invoice as closest match; consider custom financial CDM extension"
    )
    print(f"✓ Mapped Loan -> CDM:{loan_concept.cdm_entity_name} (under review)")
    print()
    
    # Step 5: Create detailed mappings
    print("Step 5: Creating entity and attribute mappings...")
    mapper = OntologyMapper(semantic_model, ontology, cdm_core)
    
    # Map customers
    customer_mapping = mapper.map_entity(
        semantic_entity="customers",
        concept="BankCustomer",
        status="approved",
        confidence=0.95,
        owner="data_governance@bank.com",
        notes="Customer master data aligned with CDM Account",
        attribute_map={
            "customer_id": "Account.AccountId",
            "full_name": "Account.AccountName",
            "email": "Account.Email",
            "phone": "Account.PhoneNumber"
        }
    )
    print(f"✓ Mapped customers: {len(customer_mapping.attribute_mappings)} attributes")
    
    # Map accounts
    account_mapping = mapper.map_entity(
        semantic_entity="accounts",
        concept="BankAccount",
        status="approved",
        confidence=0.92,
        owner="product_data@bank.com",
        notes="Banking accounts mapped to CDM Product",
        attribute_map={
            "account_id": "Product.ProductId",
            "account_number": "Product.ProductNumber",
            "account_type": "Product.ProductName"
        }
    )
    print(f"✓ Mapped accounts: {len(account_mapping.attribute_mappings)} attributes")
    
    # Map transactions
    transaction_mapping = mapper.map_entity(
        semantic_entity="transactions",
        concept="FinancialTransaction",
        status="approved",
        confidence=0.88,
        owner="transactions@bank.com",
        notes="Transactions mapped to CDM SalesOrder",
        attribute_map={
            "transaction_id": "SalesOrder.SalesOrderId",
            "transaction_date": "SalesOrder.OrderDate",
            "amount": "SalesOrder.TotalAmount",
            "account_id": "SalesOrder.CustomerId"
        }
    )
    print(f"✓ Mapped transactions: {len(transaction_mapping.attribute_mappings)} attributes")
    
    # Map loans
    loan_mapping = mapper.map_entity(
        semantic_entity="loans",
        concept="Loan",
        status="in_review",
        confidence=0.75,
        owner="lending@bank.com",
        notes="Loan mapping under review; awaiting financial services CDM extension",
        attribute_map={
            "loan_id": "Invoice.InvoiceId",
            "origination_date": "Invoice.InvoiceDate",
            "outstanding_balance": "Invoice.TotalAmount"
        }
    )
    print(f"✓ Mapped loans: {len(loan_mapping.attribute_mappings)} attributes")
    print()
    
    # Step 6: Analysis and insights
    print("=" * 80)
    print("Mapping Analysis & Business Insights")
    print("=" * 80)
    print()
    
    summary = mapper.get_mapping_summary()
    print(f"Total mappings: {summary['total_mappings']}")
    print(f"Fully approved mappings: {summary['mappings_by_status'].get('approved', 0)}")
    print(f"Mappings under review: {summary['mappings_by_status'].get('in_review', 0)}")
    print()
    
    print("Domain Coverage:")
    for domain_name, domain in ontology.domains.items():
        concepts = ontology.get_concepts_by_domain(domain_name)
        print(f"  • {domain_name} ({domain.domain_type}): {len(concepts)} concepts")
    print()
    
    print("CDM Alignment Status:")
    cdm_aligned = sum(1 for c in ontology.concepts.values() if c.cdm_entity_name)
    print(f"  • {cdm_aligned}/{len(ontology.concepts)} concepts aligned to CDM entities")
    print(f"  • {summary['mappings_by_status'].get('approved', 0)} approved for production")
    print()
    
    # Query examples
    print("Query: What financial entities map to CDM Account?")
    account_mappings = mapper.get_mappings_by_cdm_entity("Account")
    for mapping in account_mappings:
        print(f"  → {', '.join(mapping.semantic_entities)} via {mapping.concept_name}")
    print()
    
    print("Query: All concepts in CustomerDomain:")
    for concept in ontology.get_concepts_by_domain("CustomerDomain"):
        print(f"  → {concept.display_name or concept.name} (CDM: {concept.cdm_entity_name})")
    print()
    
    # Step 7: Governance review
    print("=" * 80)
    print("Governance & Compliance")
    print("=" * 80)
    print()
    
    print("Data Ownership:")
    owners = {}
    for concept in ontology.concepts.values():
        owner = concept.owner or "Unassigned"
        owners[owner] = owners.get(owner, 0) + 1
    
    for owner, count in owners.items():
        print(f"  • {owner}: {count} concept(s)")
    print()
    
    print("PII/Sensitive Data Tagging:")
    pii_concepts = [c for c in ontology.concepts.values() if "PII" in c.tags]
    if pii_concepts:
        for concept in pii_concepts:
            print(f"  ⚠ {concept.name}: {concept.description}")
    print()
    
    # Validation
    issues = mapper.validate_mappings()
    if issues:
        print("⚠ Validation Issues:")
        for issue_type, issue_list in issues.items():
            print(f"  {issue_type}:")
            for issue in issue_list:
                print(f"    - {issue}")
    else:
        print("✓ All mappings validated successfully")
    print()
    
    # Step 8: Persistence
    print("=" * 80)
    print("Persisting Artifacts")
    print("=" * 80)
    print()
    
    ontology_file = "financial_services_ontology_cdm.json"
    mappings_file = "financial_services_mappings_cdm.json"
    
    ontology.save(ontology_file)
    print(f"✓ Saved ontology: {ontology_file}")
    
    mapper.export_mappings(mappings_file)
    print(f"✓ Saved mappings: {mappings_file}")
    print()
    
    # Step 9: Executive summary
    print("=" * 80)
    print("Executive Summary")
    print("=" * 80)
    print()
    print("Financial Services CDM Alignment - Complete ✓")
    print()
    print("Business Value Delivered:")
    print("  • Standardized data model across 4 financial domains")
    print("  • 4 core entities mapped to Microsoft CDM")
    print("  • PII data governance with clear ownership")
    print("  • Foundation for regulatory compliance (GDPR, SOC2)")
    print("  • Ready for Power BI and Dynamics 365 integration")
    print()
    print("Production Readiness:")
    approved = summary['mappings_by_status'].get('approved', 0)
    total = summary['total_mappings']
    print(f"  • {approved}/{total} mappings approved for production")
    print(f"  • {len([c for c in ontology.concepts.values() if c.status == ConceptStatus.APPROVED])} concepts production-ready")
    print()
    print("Next Steps:")
    print("  • Review and approve loan mapping (awaiting financial CDM extension)")
    print("  • Deploy to data warehouse and analytics platforms")
    print("  • Configure Power Platform connectors")
    print("  • Train business users on CDM-aligned data catalog")
    print()


if __name__ == "__main__":
    main()
