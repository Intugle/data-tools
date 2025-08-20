
import pandas as pd

from data_tools.analysis.pipeline import Pipeline
from data_tools.analysis.steps import (
    ColumnProfiler,
    DataTypeIdentifierL1,
    DataTypeIdentifierL2,
    KeyIdentifier,
    TableProfiler,
)

# --- Test Data ---
KEY_TEST_DF = pd.DataFrame(
    {
        "order_id": range(100),  # Perfect primary key
        "customer_id": [f"cust_{i % 10}" for i in range(100)],  # Low uniqueness
        "product_id": [101, 102, 103, 104, 105] * 20,  # Low uniqueness
        "notes": [None] * 100,  # All nulls
    }
)

DF_NAME = "key_test_df"


def test_key_identification_end_to_end():
    """
    Tests the KeyIdentifier step in an end-to-end pipeline.
    """
    pipeline = Pipeline(
        [
            TableProfiler(),
            ColumnProfiler(),
            DataTypeIdentifierL1(),
            DataTypeIdentifierL2(),
            KeyIdentifier(),
        ]
    )

    analysis_results = pipeline.run(KEY_TEST_DF, DF_NAME)

    # Check the final output of the KeyIdentifier step
    identified_key = analysis_results.results.get("key")
    assert identified_key is not None

    # The result should identify 'order_id' as the primary key.
    # Based on the implementation, the output is a KeyIdentificationOutput object
    # which contains the identified key information.
    # We expect one identified key.

    assert identified_key == "order_id"
