"""Microsoft Common Data Model (CDM) support for intugle."""

from intugle.models.cdm.catalog import CDMCatalog
from intugle.models.cdm.entities import CDMAttribute, CDMEntity
from intugle.models.cdm.ontology import BusinessConcept, BusinessDomain, BusinessOntology
from intugle.models.cdm.mapper import AttributeMapping, EntityMapping, OntologyMapper

__all__ = [
    "CDMCatalog",
    "CDMEntity",
    "CDMAttribute",
    "BusinessDomain",
    "BusinessConcept",
    "BusinessOntology",
    "EntityMapping",
    "AttributeMapping",
    "OntologyMapper",
]
