# -*- coding: utf-8 -*-
"""
Real-World Example: Healthcare Data Mapping to Microsoft CDM

This example demonstrates mapping healthcare data to CDM entities,
showing a practical use case with patient, encounter, and medication data.
"""

import sys
import io
import pandas as pd
from datetime import datetime

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


def create_healthcare_data():
    """Create sample healthcare data."""
    
    # Patient data
    patients = pd.DataFrame({
        "patient_id": ["P001", "P002", "P003", "P004", "P005"],
        "ssn": ["123-45-6789", "234-56-7890", "345-67-8901", "456-78-9012", "567-89-0123"],
        "first_name": ["John", "Jane", "Michael", "Sarah", "David"],
        "last_name": ["Doe", "Smith", "Johnson", "Williams", "Brown"],
        "date_of_birth": pd.to_datetime([
            "1980-05-15", "1975-08-22", "1990-03-10", "1985-11-30", "1978-07-18"
        ]),
        "gender": ["M", "F", "M", "F", "M"],
        "phone": ["555-0101", "555-0102", "555-0103", "555-0104", "555-0105"],
        "email": ["john.doe@email.com", "jane.smith@email.com", 
                  "michael.j@email.com", "sarah.w@email.com", "david.b@email.com"]
    })
    
    # Encounter/visit data
    encounters = pd.DataFrame({
        "encounter_id": ["E001", "E002", "E003", "E004", "E005"],
        "patient_id": ["P001", "P002", "P001", "P003", "P004"],
        "encounter_date": pd.to_datetime([
            "2024-01-15", "2024-01-16", "2024-01-20", "2024-01-22", "2024-01-25"
        ]),
        "encounter_type": ["Outpatient", "Emergency", "Outpatient", "Inpatient", "Outpatient"],
        "chief_complaint": ["Fever", "Chest Pain", "Follow-up", "Surgery", "Headache"],
        "provider_id": ["DOC001", "DOC002", "DOC001", "DOC003", "DOC002"]
    })
    
    # Medication data
    medications = pd.DataFrame({
        "medication_id": ["M001", "M002", "M003", "M004", "M005"],
        "patient_id": ["P001", "P001", "P002", "P003", "P004"],
        "encounter_id": ["E001", "E003", "E002", "E004", "E005"],
        "medication_name": ["Amoxicillin", "Ibuprofen", "Aspirin", "Morphine", "Acetaminophen"],
        "dosage": ["500mg", "200mg", "81mg", "10mg", "325mg"],
        "frequency": ["3x daily", "as needed", "daily", "every 4h", "every 6h"],
        "start_date": pd.to_datetime([
            "2024-01-15", "2024-01-20", "2024-01-16", "2024-01-22", "2024-01-25"
        ]),
        "prescribing_doctor": ["DOC001", "DOC001", "DOC002", "DOC003", "DOC002"]
    })
    
    # Diagnosis data
    diagnoses = pd.DataFrame({
        "diagnosis_id": ["D001", "D002", "D003", "D004", "D005"],
        "encounter_id": ["E001", "E002", "E003", "E004", "E005"],
        "icd_code": ["J06.9", "I20.0", "Z09", "K40.90", "R51"],
        "diagnosis_desc": ["Upper respiratory infection", "Angina pectoris", 
                          "Follow-up examination", "Inguinal hernia", "Headache"],
        "diagnosis_date": pd.to_datetime([
            "2024-01-15", "2024-01-16", "2024-01-20", "2024-01-22", "2024-01-25"
        ])
    })
    
    return {
        "patients": patients,
        "encounters": encounters,
        "medications": medications,
        "diagnoses": diagnoses
    }


def main():
    print("=" * 80)
    print("Healthcare Data Mapping to Microsoft CDM - Real World Example")
    print("=" * 80)
    print()
    
    # Step 1: Create semantic model from healthcare data
    print("Step 1: Loading healthcare data...")
    healthcare_data = create_healthcare_data()
    semantic_model = SemanticModel(healthcare_data, domain="Healthcare")
    
    print(f"✓ Created semantic model with {len(semantic_model.datasets)} datasets:")
    for name, dataset in semantic_model.datasets.items():
        row_count = len(dataset.data) if hasattr(dataset.data, '__len__') else "N/A"
        print(f"  - {name}: {row_count} records")
    print()
    
    # Step 2: Load CDM catalogs
    print("Step 2: Loading Microsoft CDM catalogs...")
    cdm_core = CDMCatalog.load_builtin("cdm_core")
    print(f"✓ Loaded CDM Core: {', '.join(cdm_core.list_entities()[:3])}...")
    print()
    
    # Step 3: Create healthcare business ontology
    print("Step 3: Creating healthcare business ontology...")
    ontology = BusinessOntology(
        name="Healthcare Enterprise Ontology (CDM)",
        description="Healthcare data ontology aligned with Microsoft CDM",
        version="1.0"
    )
    
    # Define domains
    ontology.add_domain(
        name="PatientDomain",
        description="Patient demographics and identification",
        domain_type=DomainType.CUSTOMER,
        owner="Patient Services Department"
    )
    
    ontology.add_domain(
        name="ClinicalDomain",
        description="Clinical encounters, diagnoses, and procedures",
        domain_type=DomainType.SERVICE,
        owner="Clinical Operations"
    )
    
    print(f"✓ Created {len(ontology.domains)} business domains")
    print()
    
    # Step 4: Define business concepts
    print("Step 4: Mapping healthcare entities to CDM concepts...")
    
    # Patient → CDM Contact
    patient_concept = ontology.add_concept(
        name="Patient",
        domain="PatientDomain",
        cdm_entity=cdm_core.get_entity("Contact"),
        description="Patient demographics and contact information",
        status=ConceptStatus.APPROVED,
        owner="patient_services@hospital.org",
        tags=["PHI", "demographics", "core"]
    )
    print(f"✓ Mapped Patient -> CDM:{patient_concept.cdm_entity_name}")
    
    # Encounter → CDM Case (using service catalog)
    cdm_service = CDMCatalog.load_builtin("cdm_service")
    encounter_concept = ontology.add_concept(
        name="Encounter",
        domain="ClinicalDomain",
        cdm_entity=cdm_service.get_entity("Case"),
        description="Clinical encounters and visits",
        status=ConceptStatus.APPROVED,
        owner="clinical_ops@hospital.org",
        tags=["clinical", "encounter"]
    )
    print(f"✓ Mapped Encounter -> CDM:{encounter_concept.cdm_entity_name}")
    
    # Medication and Diagnosis (using Contact as placeholder since we don't have medical-specific CDM)
    medication_concept = ontology.add_concept(
        name="Medication",
        domain="ClinicalDomain",
        description="Prescribed medications",
        status=ConceptStatus.IN_REVIEW,
        owner="pharmacy@hospital.org",
        tags=["clinical", "pharmacy"]
    )
    print(f"✓ Created Medication concept (pending CDM mapping)")
    
    diagnosis_concept = ontology.add_concept(
        name="Diagnosis",
        domain="ClinicalDomain",
        description="Clinical diagnoses",
        status=ConceptStatus.IN_REVIEW,
        owner="clinical_ops@hospital.org",
        tags=["clinical", "diagnosis"]
    )
    print(f"✓ Created Diagnosis concept (pending CDM mapping)")
    print()
    
    # Step 5: Create detailed mappings
    print("Step 5: Creating entity and attribute mappings...")
    mapper = OntologyMapper(semantic_model, ontology, cdm_core)
    
    # Map patients table
    patient_mapping = mapper.map_entity(
        semantic_entity="patients",
        concept="Patient",
        status="approved",
        confidence=0.95,
        owner="data_governance@hospital.org",
        notes="Approved mapping for patient demographics to CDM Contact",
        attribute_map={
            "patient_id": "Contact.ContactId",
            "first_name": "Contact.FirstName",
            "last_name": "Contact.LastName",
            "email": "Contact.Email",
            "phone": "Contact.PhoneNumber"
        }
    )
    print(f"✓ Mapped patients table with {len(patient_mapping.attribute_mappings)} attributes")
    
    # Map encounters table
    encounter_mapping = mapper.map_entity(
        semantic_entity="encounters",
        concept="Encounter",
        status="approved",
        confidence=0.90,
        owner="clinical_ops@hospital.org",
        notes="Encounter mapped to CDM Case entity",
        attribute_map={
            "encounter_id": "Case.CaseId",
            "encounter_date": "Case.CreatedOn",
            "encounter_type": "Case.CaseType",
            "chief_complaint": "Case.Title",
            "patient_id": "Case.CustomerId"
        }
    )
    print(f"✓ Mapped encounters table with {len(encounter_mapping.attribute_mappings)} attributes")
    
    # Map medications (no CDM entity yet, so no CDM attributes)
    medication_mapping = mapper.map_entity(
        semantic_entity="medications",
        concept="Medication",
        status="in_review",
        confidence=0.70,
        owner="pharmacy@hospital.org",
        notes="Awaiting healthcare-specific CDM extension"
    )
    print(f"✓ Mapped medications table (pending CDM alignment)")
    
    # Map diagnoses
    diagnosis_mapping = mapper.map_entity(
        semantic_entity="diagnoses",
        concept="Diagnosis",
        status="in_review",
        confidence=0.70,
        owner="clinical_ops@hospital.org",
        notes="Awaiting healthcare-specific CDM extension"
    )
    print(f"✓ Mapped diagnoses table (pending CDM alignment)")
    print()
    
    # Step 6: Analyze mappings
    print("=" * 80)
    print("Mapping Analysis")
    print("=" * 80)
    print()
    
    summary = mapper.get_mapping_summary()
    print(f"Total mappings created: {summary['total_mappings']}")
    print(f"Unmapped semantic entities: {summary['unmapped_semantic_entities']}")
    print()
    
    print("Mappings by status:")
    for status, count in summary['mappings_by_status'].items():
        print(f"  - {status}: {count}")
    print()
    
    print("Query: Which semantic entities map to CDM Contact?")
    contact_mappings = mapper.get_mappings_by_cdm_entity("Contact")
    for mapping in contact_mappings:
        print(f"  - {', '.join(mapping.semantic_entities)} -> {mapping.concept_name}")
    print()
    
    print("Query: All concepts in PatientDomain:")
    patient_concepts = ontology.get_concepts_by_domain("PatientDomain")
    for concept in patient_concepts:
        cdm_ref = f" (CDM: {concept.cdm_entity_name})" if concept.cdm_entity_name else ""
        print(f"  - {concept.name}{cdm_ref}")
    print()
    
    print("Query: All concepts in ClinicalDomain:")
    clinical_concepts = ontology.get_concepts_by_domain("ClinicalDomain")
    for concept in clinical_concepts:
        cdm_ref = f" (CDM: {concept.cdm_entity_name})" if concept.cdm_entity_name else ""
        status_str = f" [{concept.status}]"
        print(f"  - {concept.name}{cdm_ref}{status_str}")
    print()
    
    # Step 7: Validation
    print("=" * 80)
    print("Validation")
    print("=" * 80)
    print()
    
    issues = mapper.validate_mappings()
    if issues:
        print("⚠ Validation issues found:")
        for issue_type, issue_list in issues.items():
            print(f"\n{issue_type}:")
            for issue in issue_list:
                print(f"  - {issue}")
    else:
        print("✓ All mappings validated successfully!")
    print()
    
    # Step 8: Save artifacts
    print("=" * 80)
    print("Persisting Ontology and Mappings")
    print("=" * 80)
    print()
    
    ontology_file = "healthcare_ontology_cdm.json"
    mappings_file = "healthcare_semantic_to_cdm_mappings.json"
    
    ontology.save(ontology_file)
    print(f"✓ Saved ontology to: {ontology_file}")
    
    mapper.export_mappings(mappings_file)
    print(f"✓ Saved mappings to: {mappings_file}")
    print()
    
    # Step 9: Summary
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print()
    print("Healthcare Data CDM Alignment Complete!")
    print()
    print("Key Achievements:")
    print(f"  ✓ Mapped {len(healthcare_data)} healthcare datasets to business concepts")
    print(f"  ✓ Created {len(ontology.concepts)} business concepts")
    print(f"  ✓ Aligned {summary['mappings_by_status'].get('approved', 0)} concepts to CDM entities")
    print(f"  ✓ {summary['mappings_by_status'].get('in_review', 0)} concepts pending review")
    print()
    print("Business Value:")
    print("  • Patient data aligned with CDM Contact for CRM integration")
    print("  • Clinical encounters aligned with CDM Case for service tracking")
    print("  • Clear governance with ownership and approval workflows")
    print("  • Foundation for healthcare analytics and reporting")
    print()
    print("Next Steps:")
    print("  • Extend CDM catalog with healthcare-specific entities")
    print("  • Complete medication and diagnosis CDM alignments")
    print("  • Integrate with Power Platform for analytics")
    print("  • Deploy to production data products")
    print()


if __name__ == "__main__":
    main()
