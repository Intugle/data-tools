from unittest.mock import patch

import pandas as pd
import pytest

from data_tools.analysis.models import DataSet
from data_tools.link_predictor.models import PredictedLink
from data_tools.link_predictor.predictor import LinkPredictor


@pytest.fixture
def mock_predict_for_pair():
    """Mocks the _predict_for_pair method to avoid running actual prediction logic."""
    with patch(
        "data_tools.link_predictor.predictor.LinkPredictor._predict_for_pair",
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
    assert predictor.datasets["customers"].results["key"].column_name == "id"

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
    processed_dataset = DataSet(df=customers_df, name="customers")
    # Manually add the key to simulate it being pre-analyzed
    processed_dataset.results["key"] = "id"

    # 2. Prepare a raw DataSet that needs analysis
    orders_df = pd.DataFrame({"order_id": [101, 102], "customer_id": [1, 3]})
    raw_dataset = DataSet(df=orders_df, name="orders")

    # 3. Initialize the predictor with the list
    predictor = LinkPredictor([processed_dataset, raw_dataset])

    # 4. Verify that both datasets are now fully processed
    assert "customers" in predictor.datasets
    assert "orders" in predictor.datasets
    assert "key" in predictor.datasets["customers"].results
    assert "key" in predictor.datasets["orders"].results
    assert predictor.datasets["orders"].results["key"].column_name == "order_id"

    # 5. Run prediction
    results = predictor.predict()

    # 6. Verify results
    assert mock_predict_for_pair.call_count == 1
    assert len(results.links) == 1