import pandas as pd
import pytest

from intugle.adapters.adapter import Adapter
from intugle.adapters.factory import AdapterFactory
from intugle.analysis.models import DataSet


class BaseAdapterTests:
    """
    A base class for testing any adapter that conforms to the Adapter contract.
    Subclasses must provide the 'adapter_instance' and 'test_data' fixtures.
    The assertions in this base class are written against the structure of
    the 'allergies.csv' file from the sample healthcare data.
    """

    @pytest.fixture
    def adapter_instance(self) -> Adapter:
        """This fixture must be overridden by subclasses to return a specific adapter instance."""
        pytest.fail("Subclass must implement this fixture")

    @pytest.fixture
    def test_data(self):
        """This fixture must be overridden by subclasses to provide the data for the adapter."""
        pytest.fail("Subclass must implement this fixture")

    @pytest.fixture
    def table1_dataset(self) -> DataSet:
        """This fixture must be overridden by subclasses to return the first DataSet for intersection."""
        pytest.fail("Subclass must implement this fixture")

    @pytest.fixture
    def table2_dataset(self) -> DataSet:
        """This fixture must be overridden by subclasses to return the second DataSet for intersection."""
        pytest.fail("Subclass must implement this fixture")

    def test_profile(self, adapter_instance: Adapter, test_data):
        """
        Tests the profile() method of an adapter.
        """
        # Act
        profile_output = adapter_instance.profile(test_data, "allergies")

        # Assert
        assert adapter_instance.source_name is not None
        assert adapter_instance.database is None or isinstance(adapter_instance.database, str)
        assert adapter_instance.schema is None or isinstance(adapter_instance.schema, str)

        # Note: These values are specific to the sample 'allergies.csv' file.
        assert profile_output.count > 0
        profile_columns_upper = [col.upper() for col in profile_output.columns]
        assert "PATIENT" in profile_columns_upper
        assert "REACTION2" in profile_columns_upper
        assert isinstance(profile_output.dtypes, dict)

    def test_column_profile(self, adapter_instance: Adapter, test_data):
        """
        Tests the column_profile() method of an adapter.
        """
        # First, get the total count from the profile method
        profile_output = adapter_instance.profile(test_data, "allergies")
        total_count = profile_output.count

        # Find the correct column name, ignoring case
        patient_column_name = next(
            (col for col in profile_output.columns if col.upper() == "PATIENT"), None
        )
        assert (
            patient_column_name is not None
        ), "Could not find a 'PATIENT' column (case-insensitive)."

        # Act
        column_profile = adapter_instance.column_profile(
            data=test_data,
            table_name="allergies",
            column_name=patient_column_name,
            total_count=total_count,
        )

        # Assert
        assert adapter_instance.source_name is not None
        assert adapter_instance.database is None or isinstance(adapter_instance.database, str)
        assert adapter_instance.schema is None or isinstance(adapter_instance.schema, str)

        assert column_profile.column_name.upper() == "PATIENT"
        assert column_profile.count == total_count
        assert column_profile.null_count is not None
        assert column_profile.distinct_count is not None
        assert column_profile.uniqueness is not None

    def test_intersect_count(
        self,
        adapter_instance: Adapter,
        table1_dataset: DataSet,
        table2_dataset: DataSet,
    ):
        """
        Tests the adapter-specific intersect_count method using the sample
        patients and allergies datasets.
        """
        # Act: Calculate the intersection between patients.Id and allergies.PATIENT
        intersect_count = adapter_instance.intersect_count(
            table1=table1_dataset,
            column1_name="Id",
            table2=table2_dataset,
            column2_name="PATIENT",
        )

        # Assert: Check that the intersection is greater than 0.
        assert table1_dataset.source.name is not None
        assert table1_dataset.source.database is None or isinstance(table1_dataset.source.database, str)
        assert table1_dataset.source.schema_ is None or isinstance(table1_dataset.source.schema_, str)
        assert table2_dataset.source.name is not None
        assert table2_dataset.source.database is None or isinstance(table2_dataset.source.database, str)
        assert table2_dataset.source.schema_ is None or isinstance(table2_dataset.source.schema_, str)

        assert intersect_count > 0

    def test_create_table_from_query(
        self, adapter_instance: Adapter, table2_dataset: DataSet
    ):
        """
        Tests that a new table/view can be created from a SQL query.
        """
        new_table_name = "sneezing_allergies"
        query = "SELECT * FROM allergies WHERE \"DESCRIPTION1\" = 'Sneezing'"

        adapter_instance.create_table_from_query(new_table_name, query)

        assert adapter_instance.source_name is not None
        assert adapter_instance.database is None or isinstance(adapter_instance.database, str)
        assert adapter_instance.schema is None or isinstance(adapter_instance.schema, str)

        result_df = adapter_instance.to_df_from_query(
            f"SELECT * FROM {new_table_name}"
        )
        assert not result_df.empty
        assert len(result_df) > 0

    def test_create_new_config_from_etl(self, adapter_instance: Adapter):
        """
        Tests that the adapter can create a new, valid config for a materialized ETL.
        """
        new_table_name = "my_new_data_product"

        new_config = adapter_instance.create_new_config_from_etl(new_table_name)

        assert adapter_instance.source_name is not None
        assert adapter_instance.database is None or isinstance(adapter_instance.database, str)
        assert adapter_instance.schema is None or isinstance(adapter_instance.schema, str)

        try:
            AdapterFactory().create(new_config)
        except ValueError:
            pytest.fail(
                f"AdapterFactory could not create an adapter from the new config: {new_config}"
            )

    def test_to_df_from_query(self, adapter_instance: Adapter, table2_dataset: DataSet):
        """
        Tests that the adapter can execute an arbitrary query and return a DataFrame.
        """
        df = adapter_instance.to_df_from_query("SELECT count(*) as count FROM allergies")

        assert adapter_instance.source_name is not None
        assert adapter_instance.database is None or isinstance(adapter_instance.database, str)
        assert adapter_instance.schema is None or isinstance(adapter_instance.schema, str)

        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "count" in df.columns
        assert df["count"][0] > 0
