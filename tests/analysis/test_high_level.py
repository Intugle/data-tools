import pandas as pd
import pytest

from intugle.analysis.models import DataSet


@pytest.fixture
def sample_dataframe():
    """Fixture to provide a sample DataFrame for testing."""
    return pd.DataFrame({
        "user_id": [1, 2, 3, 4, 5],
        "product_name": ["Laptop", "Mouse", "Keyboard", "Monitor", "Webcam"],
        "price": [1200.50, 25.00, 75.99, 300.00, 55.50],
        "purchase_date": pd.to_datetime([
            "2023-01-15", "2023-01-16", "2023-01-17", "2023-01-18", "2023-01-19"
        ]),
    })


def test_profile(sample_dataframe):
    """Test the profile convenience method."""
    dataset = DataSet(sample_dataframe, name="test_table")
    dataset.profile()

    assert "table_profile" in dataset.results
    table_profile = dataset.results["table_profile"]
    assert table_profile is not None
    assert table_profile.count == 5
    assert set(table_profile.columns) == {"user_id", "product_name", "price", "purchase_date"}

    assert "column_profiles" in dataset.results
    column_profiles = dataset.results["column_profiles"]
    assert column_profiles is not None
    assert len(column_profiles) == 4


def test_identify_datatypes(sample_dataframe):
    """Test the identify_datatypes convenience method."""
    dataset = DataSet(sample_dataframe, name="test_table")
    dataset.profile()
    dataset.identify_datatypes()

    assert "column_datatypes_l1" in dataset.results
    column_datatypes_l1 = dataset.results["column_datatypes_l1"]
    assert column_datatypes_l1 is not None
    assert len(column_datatypes_l1) == 4

    assert "column_datatypes_l2" in dataset.results
    column_datatypes_l2 = dataset.results["column_datatypes_l2"]
    assert column_datatypes_l2 is not None
    assert len(column_datatypes_l2) == 4


def test_identify_keys(sample_dataframe):
    """Test the identify_keys method."""
    dataset = DataSet(sample_dataframe, name="test_table")
    dataset.profile()
    dataset.identify_datatypes()
    dataset.identify_keys()

    assert "key" in dataset.results
    key = dataset.results["key"]
    assert key is not None


def test_generate_glossary(sample_dataframe):
    """Test the generate_glossary method."""
    dataset = DataSet(sample_dataframe, name="test_table")
    dataset.profile()
    dataset.identify_datatypes()
    dataset.generate_glossary(domain="ecommerce")

    assert "business_glossary_and_tags" in dataset.results
    glossary = dataset.results["business_glossary_and_tags"]
    assert glossary is not None
    assert "table_glossary" in dataset.results
    table_glossary = dataset.results["table_glossary"]
    assert table_glossary is not None


def test_save_yaml(sample_dataframe, tmp_path):
    """Test the save_yaml method."""
    dataset = DataSet(sample_dataframe, name="test_table")
    dataset.profile()
    dataset.identify_datatypes()
    dataset.generate_glossary(domain="ecommerce")

    file_path = tmp_path / "test_table.yml"
    dataset.save_yaml(file_path=str(file_path))

    assert file_path.exists()
    with open(file_path, "r") as file:
        content = file.read()
        assert "sources" in content
