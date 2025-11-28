import pandas as pd
import pytest
import yaml

from intugle.analysis.models import DataSet


@pytest.fixture
def sample_dataframe():
    """Fixture to provide a sample DataFrame for testing."""
    return pd.DataFrame({
        "user_id": [1, 2, 3, 4, 5],
        "product_name": ["Laptop", "Mouse", "Keyboard", "Monitor", "Webcam"],
        "price": [1200.50, 25.00, 75.99, 300.00, 55.50],
        "purchase_date": pd.to_datetime(["2023-01-15", "2023-01-16", "2023-01-17", "2023-01-18", "2023-01-19"]),
    })


def test_profile(sample_dataframe):
    """Test the profile convenience method."""
    dataset = DataSet(sample_dataframe, name="test_table")
    dataset.profile()

    table_model = dataset.source.table
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

    table_model = dataset.source.table
    assert all(col.type is not None for col in table_model.columns)
    assert all(col.category is not None for col in table_model.columns)


def test_identify_keys(sample_dataframe):
    """Test the identify_keys method."""
    dataset = DataSet(sample_dataframe, name="test_table")
    dataset.profile()
    dataset.identify_datatypes()
    dataset.identify_keys()

    assert dataset.source.table.key is not None
    assert dataset.source.table.key.columns == ["user_id"]
    assert dataset.source.table.key.distinct_count == 5


def test_generate_glossary(sample_dataframe):
    """Test the generate_glossary method."""
    dataset = DataSet(sample_dataframe, name="test_table")
    dataset.profile()
    dataset.identify_datatypes()
    dataset.generate_glossary(domain="ecommerce")

    table_model = dataset.source.table
    assert table_model.description is not None
    assert all(col.description is not None for col in table_model.columns)


def test_save_yaml(sample_dataframe, tmp_path):
    """Test the save_yaml method."""
    dataset = DataSet(sample_dataframe, name="test_table")
    dataset.profile()
    dataset.identify_datatypes()
    dataset.identify_keys()
    dataset.generate_glossary(domain="ecommerce")

    file_path = tmp_path / "test_table.yml"
    dataset.save_yaml(file_path=str(file_path))

    assert file_path.exists()
    with open(file_path, "r") as file:
        content = yaml.safe_load(file)

    # Assertions for the loaded YAML content
    assert "sources" in content
    loaded_source = content["sources"][0]
    assert loaded_source["name"] == "my_pandas_source"
    assert loaded_source["database"] == ""
    assert loaded_source["schema_"] == ""
    assert loaded_source["table"]["name"] == "test_table"
    assert loaded_source["table"]["details"] is None

    # Test loading from YAML
    new_dataset = DataSet(sample_dataframe, name="test_table")
    new_dataset.load_from_yaml(file_path=str(file_path))

    assert new_dataset.source.name == "my_pandas_source"
    assert new_dataset.source.database == ""
    assert new_dataset.source.schema_ == ""
    assert new_dataset.source.table.name == "test_table"
    assert new_dataset.source.table.description == dataset.source.table.description
    assert new_dataset.source.table.key.columns == dataset.source.table.key.columns
    assert new_dataset.source.table.key.distinct_count == dataset.source.table.key.distinct_count
    assert new_dataset.source.table.details is None
