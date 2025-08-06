import numpy as np
import pandas as pd

from data_tools.analysis.pipeline import Pipeline
from data_tools.analysis.steps import ColumnProfiler, TableProfiler

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
    profile = analysis_results.results.get("table_profile")

    assert profile is not None
    assert profile.count == 10
    assert profile.columns == ['user_id', 'product_name', 'price', 'purchase_date', 'is returned']
    assert profile.dtypes == {
        'user_id': 'float',  # Floats because of NaN
        'product_name': 'string',
        'price': 'float',
        'purchase_date': 'date & time',
        'is returned': 'string'  # Objects (mixed types) are treated as strings
    }


def test_column_profiling_with_complex_data():
    """
    Tests the ColumnProfiler step with a more complex and realistic dataset.
    """
    pipeline = Pipeline([
        TableProfiler(),
        ColumnProfiler()
    ])
    analysis_results = pipeline.run(COMPLEX_DF, DF_NAME)
    column_profiles = analysis_results.results.get("column_profiles")
    assert column_profiles is not None
    assert len(column_profiles) == 5
    breakpoint()
    # --- Assertions for 'user_id' ---
    user_id_profile = column_profiles.get('user_id')
    assert user_id_profile is not None
    assert user_id_profile.name == 'user_id'
    assert user_id_profile.table_name == DF_NAME
    assert user_id_profile.profile.count == 10
    assert user_id_profile.profile.null_count == 1
    assert user_id_profile.profile.distinct_count == 7  # 101, 102, 103, 104, 105, 106, 107 -> 101 is repeated

    # --- Assertions for 'product_name' ---
    product_profile = column_profiles.get('product_name')
    assert product_profile is not None
    assert product_profile.profile.count == 10
    assert product_profile.profile.null_count == 1
    assert product_profile.profile.distinct_count == 6  # Laptop, Mouse, Keyboard, Monitor, Webcam, HDMI Cable

    # --- Assertions for 'price' ---
    price_profile = column_profiles.get('price')
    assert price_profile is not None
    assert price_profile.profile.count == 10
    assert price_profile.profile.null_count == 1
    assert price_profile.profile.distinct_count == 8  # 1200.50 is repeated

    # --- Assertions for 'is returned' ---
    returned_profile = column_profiles.get('is returned')
    assert returned_profile is not None
    assert returned_profile.profile.count == 10
    assert returned_profile.profile.null_count == 1
    assert returned_profile.profile.distinct_count == 2  # True, False
    assert returned_profile.business_name == "is_returned"