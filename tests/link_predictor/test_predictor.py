import logging

from unittest.mock import patch

import pandas as pd
import pytest

from intugle.analysis.models import DataSet
from intugle.link_predictor.models import PredictedLink
from intugle.link_predictor.predictor import LinkPredictor

logging.basicConfig(level=logging.INFO)


@pytest.fixture
def mock_predict_for_pair():
    """Mocks the _predict_for_pair method to avoid running actual prediction logic."""
    with patch(
        "intugle.link_predictor.predictor.LinkPredictor._predict_for_pair",
        return_value=[
            PredictedLink(
                from_dataset="customers",
                from_column="id",
                to_dataset="orders",
                to_column="customer_id",
                confidence=0.99,
                notes="Mocked link",
            )
        ],
    ) as mock:
        yield mock


def test_predictor_with_dict_input(mock_predict_for_pair):
    """
    Tests that the LinkPredictor can be initialized with a dictionary of raw
    pandas DataFrames and that the prerequisite analysis is run.
    """
    # 1. Prepare dummy dataframes
    customers_df = pd.DataFrame({"id": [1, 2, 3], "name": ["A", "B", "C"]})
    orders_df = pd.DataFrame({"order_id": [101, 102], "customer_id": [1, 3]})
    datasets = {"customers": customers_df, "orders": orders_df}

    # 2. Initialize the predictor
    predictor = LinkPredictor(datasets)

    # 3. Verify that datasets were processed
    assert "customers" in predictor.datasets
    assert "orders" in predictor.datasets
    assert isinstance(predictor.datasets["customers"], DataSet)
    # Check that the prerequisite step was completed
    assert "key" in predictor.datasets["customers"].results
    assert predictor.datasets["customers"].results["key"] == "id"

    # 4. Run prediction
    results = predictor.predict()

    # 5. Verify that the mocked prediction was called and results are correct
    assert mock_predict_for_pair.call_count == 1
    assert len(results.links) == 1
    assert results.links[0].from_dataset == "customers"


def test_predictor_with_list_input(mock_predict_for_pair):
    """
    Tests that the LinkPredictor can be initialized with a list of DataSet
    objects, some of which have not been fully analyzed.
    """
    # 1. Prepare a fully analyzed DataSet
    customers_df = pd.DataFrame({"id": [1, 2, 3]})
    processed_dataset = DataSet(customers_df, name="customers")
    # Manually add the key to simulate it being pre-analyzed
    processed_dataset.results["key"] = "id"

    # 2. Prepare a raw DataSet that needs analysis
    orders_df = pd.DataFrame({"order_id": [101, 102], "customer_id": [1, 3]})
    raw_dataset = DataSet(orders_df, name="orders")

    # 3. Initialize the predictor with the list
    predictor = LinkPredictor([processed_dataset, raw_dataset])

    # 4. Verify that both datasets are now fully processed
    assert "customers" in predictor.datasets
    assert "orders" in predictor.datasets
    assert "key" in predictor.datasets["customers"].results
    assert "key" in predictor.datasets["orders"].results
    assert predictor.datasets["orders"].results["key"] == "order_id"

    # 5. Run prediction
    results = predictor.predict()

    # 6. Verify results
    assert mock_predict_for_pair.call_count == 1
    assert len(results.links) == 1

    # 7. Save yml
    results.save_yaml("__re__.yml")


def test_predictor_end_to_end_complex():
    """
    Tests the LinkPredictor end-to-end with more complex dataframes,
    including datetime columns and multiple potential links.
    """
    # 1. Prepare more complex dummy dataframes
    customers_df = pd.DataFrame({
        "id": [101, 102, 103],
        "email": ["alice@example.com", "bob@example.com", "charlie@example.com"],
        "created_at": pd.to_datetime(["2023-01-15", "2023-02-20", "2023-03-10"]),
        "country": ["USA", "UK", "USA"]
    })

    orders_df = pd.DataFrame({
        "order_id": [1, 2, 3, 4],
        "customer_id": [101, 102, 101, 103],
        "order_date": pd.to_datetime(["2023-01-20", "2023-02-22", "2023-01-25", "2023-03-12"]),
        "amount": [100.50, 50.00, 75.25, 120.00]
    })

    events_df = pd.DataFrame({
        "event_id": [1, 2, 3],
        "user_id": [101, 103, 102],
        "event_timestamp": pd.to_datetime(["2023-01-20 10:00", "2023-03-12 11:00", "2023-02-22 12:00"]),
        "event_type": ["purchase", "page_view", "purchase"]
    })

    datasets = {
        "customers": customers_df,
        "orders": orders_df,
        "events": events_df,
    }

    # 2. Initialize the predictor
    predictor = LinkPredictor(datasets)

    # 3. Run the prediction
    results = predictor.predict()

    # 4. Assert that the correct links were found
    assert len(results.links) >= 2, "Expected at least two links to be found"

    # Check for the link between customers and orders
    link1_found = any(
        link.from_dataset == "customers" and link.from_column == "id" and
        link.to_dataset == "orders" and link.to_column == "customer_id"
        for link in results.links
    )
    assert link1_found, "Expected link between customers.id and orders.customer_id not found"

    # Check for the link between customers and events
    link2_found = any(
        link.from_dataset == "customers" and link.from_column == "id" and
        link.to_dataset == "events" and link.to_column == "user_id"
        for link in results.links
    )
    assert link2_found, "Expected link between customers.id and events.user_id not found"
