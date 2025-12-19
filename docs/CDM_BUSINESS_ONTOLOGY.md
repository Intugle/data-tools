# Business Ontology Layer - Microsoft CDM Support

This feature introduces a business ontology layer on top of the semantic model, providing alignment with Microsoft Common Data Model (CDM) entities.

## Overview

The business ontology layer provides:

1. **Business Domains** - High-level groupings of related business concepts (e.g., CustomerDomain, SalesDomain)
2. **Business Concepts** - Business-level entities that map to CDM entities (e.g., Customer → CDM Contact)
3. **CDM Catalog** - Built-in catalog of Microsoft CDM entities with attributes
4. **Ontology Mapper** - Mapping engine between semantic models and CDM entities

## Key Components

### CDM Catalog

Built-in catalogs for common Microsoft CDM entities:

- `cdm_core` - Core entities (Account, Contact, Address)
- `cdm_sales` - Sales entities (SalesOrder, Product, Invoice)
- `cdm_service` - Service entities (Case)

### Business Ontology

Organize semantic models into business domains and concepts:

```python
from intugle import BusinessOntology, CDMCatalog

# Create ontology
ontology = BusinessOntology(name="Enterprise Ontology")

# Add domains
ontology.add_domain(
    name="CustomerDomain",
    description="Customer-related concepts",
    domain_type=DomainType.CUSTOMER
)

# Add concepts linked to CDM
cdm_catalog = CDMCatalog.load_builtin("cdm_core")
ontology.add_concept(
    name="Customer",
    domain="CustomerDomain",
    cdm_entity=cdm_catalog.get_entity("Contact")
)
```

### Ontology Mapper

Map semantic model entities to business concepts and CDM:

```python
from intugle import OntologyMapper, SemanticModel

# Create semantic model
semantic_model = SemanticModel(data_dict)

# Create mapper
mapper = OntologyMapper(semantic_model, ontology, cdm_catalog)

# Map entities
mapper.map_entity(
    semantic_entity="customer",
    concept="Customer",
    attribute_map={
        "customer_id": "Contact.ContactId",
        "email": "Contact.Email",
        "full_name": "Contact.FullName"
    }
)
```

## Usage Example

See `examples/cdm_business_ontology_example.py` for a complete example:

```bash
python examples/cdm_business_ontology_example.py
```

## API Reference

### CDM Classes

- `CDMCatalog` - Catalog of CDM entities
- `CDMEntity` - Represents a CDM entity with attributes
- `CDMAttribute` - Represents a CDM attribute

### Ontology Classes

- `BusinessOntology` - Container for domains and concepts
- `BusinessDomain` - High-level business domain
- `BusinessConcept` - Business concept mapped to CDM entity

### Mapping Classes

- `OntologyMapper` - Maps semantic models to ontology/CDM
- `EntityMapping` - Entity-level mapping
- `AttributeMapping` - Attribute-level mapping

## Features

### Querying

```python
# Get concepts by domain
customer_concepts = ontology.get_concepts_by_domain("CustomerDomain")

# Get mappings by semantic entity
mappings = mapper.get_mappings_by_semantic_entity("customer")

# Get mappings by CDM entity
mappings = mapper.get_mappings_by_cdm_entity("Contact")

# Get unmapped entities
unmapped = mapper.get_unmapped_semantic_entities()
```

### Validation

```python
# Validate mappings
issues = mapper.validate_mappings()

# Get mapping summary
summary = mapper.get_mapping_summary()
```

### Persistence

```python
# Save ontology
ontology.save("business_ontology.json")

# Save mappings
mapper.export_mappings("semantic_to_cdm_mappings.json")

# Load ontology
ontology = BusinessOntology.load("business_ontology.json")

# Import mappings
mapper = OntologyMapper.import_mappings(
    "semantic_to_cdm_mappings.json",
    semantic_model,
    ontology,
    cdm_catalog
)
```

## Mapping Types

- `ONE_TO_ONE` - Single semantic entity maps to one CDM entity
- `MANY_TO_ONE` - Multiple semantic entities map to one CDM entity
- `ONE_TO_MANY` - One semantic entity maps to multiple CDM entities
- `COMPOSITE` - Complex mapping with transformations

## Benefits

1. **Business Alignment** - Bridge technical and business terminology
2. **CDM Compliance** - Align with Microsoft CDM standard
3. **Governance** - Track mappings with status, owner, notes
4. **Reusability** - Share ontologies and mappings across projects
5. **Documentation** - Self-documenting semantic models
6. **Integration** - Enable CDM-aware tools and data products

## Testing

Run the comprehensive test suite:

```bash
pytest tests/cdm/ -v
```

Test coverage:
- Unit tests for all CDM components (63 tests)
- Integration tests with real semantic models
- Validation and error handling tests

## Future Extensions

- Support for FIBO (Financial Industry Business Ontology)
- Custom ontology support
- Automatic mapping suggestions using LLMs
- Visual ontology designer
- Integration with data catalogs and governance tools
