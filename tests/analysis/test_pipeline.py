import numpy as np
import pandas as pd

from intugle.analysis.pipeline import Pipeline
from intugle.analysis.steps import ColumnProfiler, TableProfiler
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


def test_pipeline_with_complex_data():
    """
    Tests that the pipeline can run the TableProfiler step with complex data.
    """
    pipeline = Pipeline([TableProfiler()])
    analysis_results = pipeline.run(COMPLEX_DF, DF_NAME)
    table_model = analysis_results.source_table_model

    assert table_model.profiling_metrics is not None
    assert table_model.profiling_metrics.count == 10
    assert len(table_model.columns) == 5
    assert {col.name for col in table_model.columns} == {'user_id', 'product_name', 'price', 'purchase_date', 'is returned'}


def test_column_profiling_with_complex_data():
    """
    Tests the ColumnProfiler step with a more complex and realistic dataset.
    """
    pipeline = Pipeline([
        TableProfiler(),
        ColumnProfiler()
    ])
    analysis_results = pipeline.run(COMPLEX_DF, DF_NAME)
    columns_map = analysis_results._columns_map
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
