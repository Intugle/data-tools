from unittest.mock import patch

import pytest

from intugle.data_product import DataProduct
from intugle.libs.smart_query_generator.models.models import (
    ETLModel,
    FieldsModel,
    FilterModel,
    SelectionModel,
    SortByModel,
)
from intugle.models.manifest import Manifest
from intugle.models.resources.model import Column
from intugle.models.resources.relationship import (
    Relationship,
    RelationshipTable,
    RelationshipType,
)
from intugle.models.resources.source import Source, SourceTables


@pytest.fixture
def mock_manifest() -> Manifest:
    """
    Creates an in-memory Manifest object for testing, containing all necessary
    sources, columns, and relationships to build a sample query.
    """
    manifest = Manifest()

    # Define a dummy config that the adapter factory can recognize
    dummy_details = {"path": "dummy.csv", "type": "csv"}

    # Define sources and columns
    patients_source = Source(
        name="patients",
        description="Patients table",
        schema="public",
        database="db",
        table=SourceTables(
            name="patients",
            description="Patients table",
            columns=[
                Column(name="id", type="integer"),
                Column(name="first", type="string"),
            ],
            details=dummy_details,
        ),
    )

    encounters_source = Source(
        name="encounters",
        description="Encounters table",
        schema="public",
        database="db",
        table=SourceTables(
            name="encounters",
            description="Encounters table",
            columns=[
                Column(name="patient", type="integer"),
                Column(name="code", type="string"),
            ],
            details=dummy_details,
        ),
    )

    claims_transactions_source = Source(
        name="claims_transactions",
        description="Claims transactions table",
        schema="public",
        database="db",
        table=SourceTables(
            name="claims_transactions",
            description="Claims transactions table",
            columns=[
                Column(name="patientid", type="integer"),
                Column(name="amount", type="float"),
            ],
            details=dummy_details,
        ),
    )

    manifest.sources = {
        "patients": patients_source,
        "encounters": encounters_source,
        "claims_transactions": claims_transactions_source,
    }

    # Define relationships for joins
    rel1 = Relationship(
        name="encounters_to_patients",
        description="Join between encounters and patients",
        source=RelationshipTable(table="encounters", columns=["patient"]),
        target=RelationshipTable(table="patients", columns=["id"]),
        type=RelationshipType.MANY_TO_ONE,
    )
    rel2 = Relationship(
        name="claims_to_patients",
        description="Join between claims and patients",
        source=RelationshipTable(table="claims_transactions", columns=["patientid"]),
        target=RelationshipTable(table="patients", columns=["id"]),
        type=RelationshipType.MANY_TO_ONE,
    )

    manifest.relationships = {
        "encounters_to_patients": rel1,
        "claims_to_patients": rel2,
    }
    return manifest


@patch("intugle.analysis.models.DataSet.load", return_value=None)
def test_query_generator_is_isolated(mock_load, mock_manifest):
    """
    Tests that the query generator works correctly in isolation by using a
    mocked manifest and not relying on the filesystem.
    """
    # 1. Define the ETL model for the query
    etl_model = ETLModel(
        name="test_etl",
        fields=[
            FieldsModel(
                id="claims_transactions.amount",
                name="claim_amount",
                category="measure",
                measure_func="sum",
            ),
        ],
        filter=FilterModel(
            selections=[SelectionModel(id="patients.first", values=["aaa", "bbb"])],
            sort_by=[SortByModel(id="encounters.code", direction="desc")],
        ),
    )

    # 2. Patch the ManifestLoader to use our mock manifest
    with patch("intugle.data_product.ManifestLoader") as MockManifestLoader:
        # Configure the mock instance that will be created inside DataProduct
        mock_instance = MockManifestLoader.return_value
        mock_instance.manifest = mock_manifest

        # 3. Initialize DataProduct. The project_base path is now irrelevant.
        sql_generator = DataProduct(models_dir_path="/dummy/path")
        generated_query = sql_generator.generate_query(etl_model)

    # 4. Define the expected query and assert the result
    # This query now matches the actual, unquoted output of the generator.
    expected_query = (
        'SELECT sum("claims_transactions"."amount") as claim_amount '
        'FROM encounters '
        'LEFT JOIN patients ON "encounters"."patient" = "patients"."id" '
        'LEFT JOIN claims_transactions ON "claims_transactions"."patientid" = "patients"."id" '
        "WHERE (\"patients\".\"first\" IN ('aaa', 'bbb')) "
        'ORDER BY encounters.code DESC'
    )

    # A simple way to compare SQL strings is to normalize whitespace
    normalized_generated = " ".join(generated_query.split())
    normalized_expected = " ".join(expected_query.split())

    assert normalized_generated == normalized_expected
