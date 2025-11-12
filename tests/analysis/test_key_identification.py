import pandas as pd

from intugle.analysis.models import DataSet

# --- Test Data for Single Primary Key ---
KEY_TEST_DF = pd.DataFrame(
    {
        "order_id": range(100),  # Perfect primary key
        "customer_id": [f"cust_{i % 10}" for i in range(100)],  # Low uniqueness
        "product_id": [101, 102, 103, 104, 105] * 20,  # Low uniqueness
        "notes": [None] * 100,  # All nulls
    }
)
DF_NAME = "key_test_df"

# --- Test Data for Composite Primary Key ---
COMPOSITE_KEY_TEST_DF = pd.DataFrame({
    "user_id": [1, 1, 2, 2, 3, 3],
    "product_id": [101, 102, 101, 103, 102, 103],
    "review": ["Great!", "Good", "Okay", "Bad", "Excellent", "So-so"],
})
COMPOSITE_DF_NAME = "composite_key_test_df"


def test_key_identification_end_to_end():
    """
    Tests the key identification convenience method on the DataSet for a single key.
    """
    dataset = DataSet(KEY_TEST_DF, DF_NAME)
    dataset.profile().identify_datatypes().identify_keys()

    # Check the final output of the KeyIdentifier step
    identified_key = dataset.source.table.key
    assert identified_key is not None
    assert identified_key == ["order_id"]


def test_composite_key_identification_end_to_end():
    """
    Tests the key identification for a composite key.
    """
    # This test is marked as expected to fail until the composite key logic is fully robust.
    # The underlying agent may sometimes fail to identify composite keys correctly.
    dataset = DataSet(COMPOSITE_KEY_TEST_DF, COMPOSITE_DF_NAME)
    dataset.profile().identify_datatypes().identify_keys()

    identified_key = dataset.source.table.key
    assert identified_key is not None
    # Sort for assertion consistency, as the order is not guaranteed
    assert sorted(identified_key) == ["product_id", "user_id"]