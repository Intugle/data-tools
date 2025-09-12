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

    table_model = dataset.source_table_model
    assert table_model.profiling_metrics is not None
    assert table_model.profiling_metrics.count == 5
    assert len(table_model.columns) == 4
    assert {col.name for col in table_model.columns} == {"user_id", "product_name", "price", "purchase_date"}

    assert all(col.profiling_metrics is not None for col in table_model.columns)


def test_identify_datatypes(sample_dataframe):
    """Test the identify_datatypes convenience method."""
    dataset = DataSet(sample_dataframe, name="test_table")
    dataset.profile()
    dataset.identify_datatypes()

    table_model = dataset.source_table_model
    assert all(col.type is not None for col in table_model.columns)
    assert all(col.category is not None for col in table_model.columns)


def test_identify_keys(sample_dataframe):
    """Test the identify_keys method."""
    dataset = DataSet(sample_dataframe, name="test_table")
    dataset.profile()
    dataset.identify_datatypes()
    dataset.identify_keys()

    assert dataset.source_table_model.key is not None


def test_generate_glossary(sample_dataframe):
    """Test the generate_glossary method."""
    dataset = DataSet(sample_dataframe, name="test_table")
    dataset.profile()
    dataset.identify_datatypes()
    dataset.generate_glossary(domain="ecommerce")

    table_model = dataset.source_table_model
    assert table_model.description is not None
    assert all(col.description is not None for col in table_model.columns)


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
