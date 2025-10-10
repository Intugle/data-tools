import pytest

from tests.adapters.base_adapter_tests import BaseAdapterTests
from intugle.adapters.types.duckdb.duckdb import DuckdbAdapter
from intugle.adapters.types.duckdb.models import DuckdbConfig
from intugle.analysis.models import DataSet


def get_healthcare_config(table_name: str) -> DuckdbConfig:
    """Helper function to create a DuckdbConfig for a healthcare CSV file."""
    return DuckdbConfig(
        path=f"sample_data/healthcare/{table_name}.csv",
        type="csv"
    )


class TestDuckdbAdapter(BaseAdapterTests):
    """Runs the shared adapter tests for the DuckdbAdapter."""

    @pytest.fixture
    def adapter_instance(self):
        return DuckdbAdapter()

    @pytest.fixture
    def test_data(self):
        """Provides a DuckdbConfig pointing to the allergies test CSV."""
        return get_healthcare_config("allergies")

    @pytest.fixture
    def table1_dataset(self) -> DataSet:
        """Provides the 'patients' dataset for intersection tests."""
        return DataSet(get_healthcare_config("patients"), name="patients")

    @pytest.fixture
    def table2_dataset(self) -> DataSet:
        """Provides the 'allergies' dataset for intersection tests."""
        return DataSet(get_healthcare_config("allergies"), name="allergies")
