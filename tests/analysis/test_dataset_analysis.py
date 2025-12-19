import numpy as np
import pandas as pd

from intugle.analysis.models import DataSet
from intugle.core.utilities.processing import string_standardization

# --- Test Data ---
# A more complex and realistic DataFrame for testing.
COMPLEX_DF = pd.DataFrame({
    'user_id': [101, 102, 103, 101, 104, 105, 101, np.nan, 106, 107],
    'product_name': ['Laptop', 'Mouse', 'Keyboard', 'Laptop', 'Monitor', 'Webcam', 'Mouse', 'Keyboard', 'HDMI Cable', None],
    'price': [1200.50, 25.00, 75.99, 1200.50, 300.00, 55.50, 26.00, np.nan, 15.00, 40.00],
    'purchase_date': pd.to_datetime([
        '2023-01-15', '2023-01-15', '2023-01-16', '2023-01-17', '2023-01-18',
        '2023-01-18', '2023-01-19', '2023-01-20', '2023-01-20', '2023-01-21'
    ]),
    'is returned': [False, False, True, False, False, True, False, False, True, np.nan]
})

DF_NAME = "complex_test_df"


def test_table_profiling_with_complex_data():
    """
    Tests table-level profiling on a DataSet with complex data.
    """
    dataset = DataSet(COMPLEX_DF, DF_NAME)
    dataset.profile_table()

    table_model = dataset.source.table
    assert table_model.profiling_metrics is not None
    assert table_model.profiling_metrics.count == 10
    assert len(table_model.columns) == 5
    assert {col.name for col in table_model.columns} == {'user_id', 'product_name', 'price', 'purchase_date', 'is returned'}


def test_column_profiling_with_complex_data():
    """
    Tests column-level profiling on a DataSet with a more complex and realistic dataset.
    """
    dataset = DataSet(COMPLEX_DF, DF_NAME)
    dataset.profile()  # Runs table and column profiling
    columns_map = dataset.columns
    assert len(columns_map) == 5

    # --- Assertions for 'user_id' ---
    user_id_profile = columns_map.get('user_id').profiling_metrics
    assert user_id_profile is not None
    assert user_id_profile.count == 10
    assert user_id_profile.null_count == 1
    assert user_id_profile.distinct_count == 7  # 101, 102, 103, 104, 105, 106, 107 -> 101 is repeated

    # --- Assertions for 'product_name' ---
    product_profile = columns_map.get('product_name').profiling_metrics
    assert product_profile is not None
    assert product_profile.count == 10
    assert product_profile.null_count == 1
    assert product_profile.distinct_count == 6  # Laptop, Mouse, Keyboard, Monitor, Webcam, HDMI Cable

    # --- Assertions for 'price' ---
    price_profile = columns_map.get('price').profiling_metrics
    assert price_profile is not None
    assert price_profile.count == 10
    assert price_profile.null_count == 1
    assert price_profile.distinct_count == 8  # 1200.50 is repeated

    # --- Assertions for 'is returned' ---
    returned_profile = columns_map.get('is returned').profiling_metrics
    assert returned_profile is not None
    assert returned_profile.count == 10
    assert returned_profile.null_count == 1
    assert returned_profile.distinct_count == 2  # True, False
    assert string_standardization("is returned") == "is_returned"


def test_profiling_empty_dataframe():
    """Tests that profiling an empty DataFrame does not raise an error."""
    empty_df = pd.DataFrame({'col1': [], 'col2': []})
    dataset = DataSet(empty_df, "empty_df")
    dataset.profile()

    assert dataset.source.table.profiling_metrics.count == 0
    assert len(dataset.columns) == 2
    
    col1_profile = dataset.columns['col1'].profiling_metrics
    assert col1_profile.count == 0
    assert col1_profile.null_count == 0
    assert col1_profile.distinct_count == 0


def test_profiling_column_with_all_nulls():
    """Tests that a column with all nulls is profiled correctly."""
    df = pd.DataFrame({'id': [1, 2, 3], 'notes': [None, np.nan, None]})
    dataset = DataSet(df, "all_nulls_df")
    dataset.profile()

    notes_profile = dataset.columns['notes'].profiling_metrics
    assert notes_profile.count == 3
    assert notes_profile.null_count == 3
    assert notes_profile.distinct_count == 0
    assert notes_profile.uniqueness == 0.0
    assert notes_profile.completeness == 0.0


def test_is_yaml_stale_missing_source_last_modified(tmp_path):
    """
    Tests that _is_yaml_stale returns True when source_last_modified is missing.
    
    When the YAML metadata lacks a source_last_modified timestamp, the cache
    freshness cannot be verified, so it should be treated as stale.
    """
    # Create a temporary CSV file to act as the source
    csv_file = tmp_path / "test_data.csv"
    csv_file.write_text("col1,col2\n1,a\n2,b\n")

    # Create a dataset with a DataFrame, then modify self.data to simulate file-based source
    df = pd.DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})
    dataset = DataSet(df, "test_dataset")
    # Override self.data to simulate a file-based source for the _is_yaml_stale check
    dataset.data = {"path": str(csv_file)}

    # YAML data without source_last_modified field
    yaml_data_missing_timestamp = {
        "sources": [
            {
                "table": {
                    "name": "test_data",
                    # source_last_modified is intentionally missing
                }
            }
        ]
    }

    # Should return True (stale) because source_last_modified is missing
    assert dataset._is_yaml_stale(yaml_data_missing_timestamp) is True


def test_is_yaml_stale_with_none_source_last_modified(tmp_path):
    """
    Tests that _is_yaml_stale returns True when source_last_modified is explicitly None.
    """
    # Create a temporary CSV file to act as the source
    csv_file = tmp_path / "test_data.csv"
    csv_file.write_text("col1,col2\n1,a\n2,b\n")

    # Create a dataset with a DataFrame, then modify self.data to simulate file-based source
    df = pd.DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})
    dataset = DataSet(df, "test_dataset")
    # Override self.data to simulate a file-based source for the _is_yaml_stale check
    dataset.data = {"path": str(csv_file)}

    # YAML data with source_last_modified explicitly set to None
    yaml_data_none_timestamp = {
        "sources": [
            {
                "table": {
                    "name": "test_data",
                    "source_last_modified": None
                }
            }
        ]
    }

    # Should return True (stale) because source_last_modified is None
    assert dataset._is_yaml_stale(yaml_data_none_timestamp) is True


def test_is_yaml_stale_with_valid_source_last_modified(tmp_path):
    """
    Tests that _is_yaml_stale returns False when source_last_modified is valid and current.
    """
    import os

    # Create a temporary CSV file to act as the source
    csv_file = tmp_path / "test_data.csv"
    csv_file.write_text("col1,col2\n1,a\n2,b\n")

    # Get the current modification time
    current_mtime = os.path.getmtime(str(csv_file))

    # Create a dataset with a DataFrame, then modify self.data to simulate file-based source
    df = pd.DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})
    dataset = DataSet(df, "test_dataset")
    # Override self.data to simulate a file-based source for the _is_yaml_stale check
    dataset.data = {"path": str(csv_file)}

    # YAML data with source_last_modified set to current or future time
    yaml_data_valid_timestamp = {
        "sources": [
            {
                "table": {
                    "name": "test_data",
                    "source_last_modified": current_mtime + 1000  # Future timestamp
                }
            }
        ]
    }

    # Should return False (not stale) because source hasn't been modified since YAML was created
    assert dataset._is_yaml_stale(yaml_data_valid_timestamp) is False
