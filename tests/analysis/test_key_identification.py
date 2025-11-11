
import pandas as pd

from intugle.analysis.models import DataSet

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
    Tests the key identification convenience method on the DataSet.
    """
    dataset = DataSet(KEY_TEST_DF, DF_NAME)
    dataset.profile().identify_datatypes().identify_keys()

    # Check the final output of the KeyIdentifier step
    identified_key = dataset.source.table.key
    assert identified_key is not None
    assert identified_key == "order_id"
