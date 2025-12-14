"""
Quick Start: Business Ontology with Microsoft CDM
=================================================

This guide shows how to quickly get started with the CDM business ontology layer.
"""

from intugle import (
    BusinessOntology,
    CDMCatalog,
    OntologyMapper,
    SemanticModel,
)
import pandas as pd


# Step 1: Create sample data
data = {
    "customers": pd.DataFrame({
        "id": [1, 2, 3],
        "email": ["a@x.com", "b@x.com", "c@x.com"],
        "name": ["Alice", "Bob", "Charlie"]
    })
}

# Step 2: Create semantic model
semantic_model = SemanticModel(data)

# Step 3: Load CDM catalog
cdm_catalog = CDMCatalog.load_builtin("cdm_core")
print(f"Available CDM entities: {cdm_catalog.list_entities()}")

# Step 4: Create business ontology
ontology = BusinessOntology(name="My Ontology")

# Step 5: Add domain
ontology.add_domain(name="CustomerDomain", description="Customer data")

# Step 6: Add concept linked to CDM
ontology.add_concept(
    name="Customer",
    domain="CustomerDomain",
    cdm_entity=cdm_catalog.get_entity("Contact")
)

# Step 7: Create mapper
mapper = OntologyMapper(semantic_model, ontology, cdm_catalog)

# Step 8: Map semantic entity to concept
mapper.map_entity(
    semantic_entity="customers",
    concept="Customer",
    attribute_map={
        "id": "Contact.ContactId",
        "email": "Contact.Email",
        "name": "Contact.FullName"
    }
)

# Step 9: Query mappings
print(f"\nMapping summary: {mapper.get_mapping_summary()}")

# Step 10: Save
ontology.save("my_ontology.json")
mapper.export_mappings("my_mappings.json")
print("\n✓ Ontology and mappings saved successfully!")
