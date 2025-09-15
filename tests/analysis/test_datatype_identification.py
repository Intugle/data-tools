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
    columns_map = analysis_results.columns
    assert columns_map['user_id'].type == 'integer'
    assert columns_map['product_name'].type == 'close_ended_text'
    assert columns_map['price'].type == 'float'


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

    # Check the final output of the L2 step
    columns_map = analysis_results.columns
    assert columns_map['user_id'].category == 'dimension'
    assert columns_map['product_name'].category == 'dimension'
    assert columns_map['price'].category == 'measure'
