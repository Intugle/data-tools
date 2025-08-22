import pandas as pd

from intugle.analysis.pipeline import Pipeline
from intugle.analysis.steps import ColumnProfiler, DataTypeIdentifierL1, DataTypeIdentifierL2, TableProfiler

# --- Test Data ---
COMPLEX_DF = pd.DataFrame({
    'user_id': [101, 102, 103, 101, 104, 105, 101, None, 106, 107],
    'product_name': ['Laptop', 'Mouse', 'Keyboard', 'Laptop', 'Monitor', 'Webcam', 'Mouse', 'Keyboard', 'HDMI Cable', None],
    'price': [1200.50, 25.00, 75.99, 1200.50, 300.00, 55.50, 26.00, None, 15.00, 40.00],
})

DF_NAME = "complex_test_df"


def test_datatype_identification_l1_end_to_end():
    """
    Tests the DatatypeIdentifierL1 step in an end-to-end pipeline.
    """
    pipeline = Pipeline([
        TableProfiler(),
        ColumnProfiler(),
        DataTypeIdentifierL1(),
    ])

    analysis_results = pipeline.run(COMPLEX_DF, DF_NAME)

    # Check the final output of the L1 step
    datatype_l1_results = analysis_results.results.get("column_datatypes_l1")
    assert datatype_l1_results is not None
    assert len(datatype_l1_results) == 3

    # Create a dictionary for easy lookup
    results_map = {res.column_name: res for res in datatype_l1_results}

    # Assertions for 'user_id'
    assert 'user_id' in results_map
    assert results_map['user_id'].datatype_l1 == 'integer'

    # Assertions for 'product_name'
    assert 'product_name' in results_map
    assert results_map['product_name'].datatype_l1 == 'close_ended_text'

    # Assertions for 'price'
    assert 'price' in results_map
    assert results_map['price'].datatype_l1 == 'float'

    # Also check that the original column profiles were updated
    column_profiles = analysis_results.results.get("column_profiles")
    assert column_profiles['user_id'].datatype_l1 == 'integer'
    assert column_profiles['product_name'].datatype_l1 == 'close_ended_text'
    assert column_profiles['price'].datatype_l1 == 'float'


def test_datatype_identification_l2_end_to_end():
    """
    Tests the DatatypeIdentifierL1 step in an end-to-end pipeline.
    """
    pipeline = Pipeline([
        TableProfiler(),
        ColumnProfiler(),
        DataTypeIdentifierL1(),
        DataTypeIdentifierL2(),
    ])

    analysis_results = pipeline.run(COMPLEX_DF, DF_NAME)

    # Check the final output of the L1 step
    datatype_l2_results = analysis_results.results.get("column_datatypes_l2")
    assert datatype_l2_results is not None
    assert len(datatype_l2_results) == 3

    # Create a dictionary for easy lookup
    results_map = {res.column_name: res for res in datatype_l2_results}

    # Assertions for 'user_id'
    assert 'user_id' in results_map
    assert results_map['user_id'].datatype_l2 == 'dimension'

    # Assertions for 'product_name'
    assert 'product_name' in results_map
    assert results_map['product_name'].datatype_l2 == 'dimension'

    # Assertions for 'price'
    assert 'price' in results_map
    assert results_map['price'].datatype_l2 == 'measure'

    # Also check that the original column profiles were updated
    column_profiles = analysis_results.results.get("column_profiles")
    assert column_profiles['user_id'].datatype_l2 == 'dimension'
    assert column_profiles['product_name'].datatype_l2 == 'dimension'
    assert column_profiles['price'].datatype_l2 == 'measure'