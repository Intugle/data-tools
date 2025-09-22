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
                intersect_count=1,
                intersect_ratio_col1=1.0,
                intersect_ratio_col2=1.0,
                accuracy=1.0,
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
    assert predictor.datasets["customers"].source_table_model.key == "id"

    # 4. Run prediction
    results = predictor.predict(force_recreate=True)

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
    processed_dataset.source_table_model.key = "id"

    # 2. Prepare a raw DataSet that needs analysis
    orders_df = pd.DataFrame({"order_id": [101, 102], "customer_id": [1, 3]})
    raw_dataset = DataSet(orders_df, name="orders")

    # 3. Initialize the predictor with the list
    predictor = LinkPredictor([processed_dataset, raw_dataset])

    # 4. Verify that both datasets are now fully processed
    assert "customers" in predictor.datasets
    assert "orders" in predictor.datasets
    assert predictor.datasets["customers"].source_table_model.key is not None
    assert predictor.datasets["orders"].source_table_model.key is not None
    assert predictor.datasets["orders"].source_table_model.key == "order_id"

    # 5. Run prediction
    results = predictor.predict(force_recreate=True)

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
    results = predictor.predict(force_recreate=True)

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

    # Verify that intersection metrics are populated
    for link in results.links:
        assert link.intersect_count is not None
        assert link.intersect_count > 0
        assert link.intersect_ratio_col1 is not None
        assert 0 <= link.intersect_ratio_col1 <= 1
        assert link.intersect_ratio_col2 is not None
        assert 0 <= link.intersect_ratio_col2 <= 1
        assert link.accuracy is not None
        assert 0 <= link.accuracy <= 1


def test_predictor_save_and_load_yaml(tmp_path):
    """
    Tests that the LinkPredictor can correctly save its predicted links to a YAML
    file and then load them back, preserving all data including intersection metrics.
    """
    # 1. Prepare a LinkPredictor with some dummy data and predicted links
    customers_df = pd.DataFrame({"id": [1, 2, 3]})
    orders_df = pd.DataFrame({"order_id": [101, 102], "customer_id": [1, 3]})
    predictor = LinkPredictor({"customers": customers_df, "orders": orders_df})

    original_links = [
        PredictedLink(
            from_dataset="customers",
            from_column="id",
            to_dataset="orders",
            to_column="customer_id",
            intersect_count=2,
            intersect_ratio_col1=0.66,
            intersect_ratio_col2=1.0,
            accuracy=1.0,
        ),
        PredictedLink(
            from_dataset="users",
            from_column="user_id",
            to_dataset="events",
            to_column="user_id",
            intersect_count=100,
            intersect_ratio_col1=0.9,
            intersect_ratio_col2=0.85,
            accuracy=0.9,
        ),
    ]
    predictor.links = original_links

    # 2. Save the links to a temporary YAML file
    temp_yaml_file = tmp_path / "relationships.yml"
    predictor.save_yaml(temp_yaml_file)

    # 3. Create a new predictor and load the links from the file
    new_predictor = LinkPredictor({"customers": customers_df, "orders": orders_df})
    new_predictor.load_from_yaml(temp_yaml_file)

    # 4. Assert that the loaded links are identical to the original ones
    assert len(new_predictor.links) == len(original_links)
    for original, loaded in zip(original_links, new_predictor.links):
        assert original == loaded


def test_predictor_end_to_end_duckdb():
    """
    Tests the LinkPredictor end-to-end with the DuckDB adapter,
    using remote CSV files as data sources.
    """
    def generate_config(table_name: str) -> str:
        """Append the base URL to the table name."""
        return {
            "path": f"https://raw.githubusercontent.com/Intugle/data-tools/refs/heads/main/sample_data/healthcare/{table_name}.csv",
            "type": "csv",
        }

    table_names = [
        "allergies",
        "patients",
        "claims",
    ]

    datasets = {table: generate_config(table) for table in table_names}

    # 2. Initialize the predictor
    predictor = LinkPredictor(datasets)

    # 3. Run the prediction
    results = predictor.predict(force_recreate=True)

    # 4. Assert that the correct links were found
    assert len(results.links) >= 2, "Expected at least three links to be found"

    # Check for the link between patients and allergies
    link1_found = any(
        link.from_dataset == "patients" and link.from_column == "id" and
        link.to_dataset == "allergies" and link.to_column == "patient"
        for link in results.links
    ) or any(
        link.to_dataset == "patients" and link.to_column == "id" and
        link.from_dataset == "allergies" and link.from_column == "patient"
        for link in results.links
    ) 
    
    assert link1_found, "Expected link between patients.id and allergies.patient not found"

    # Check for the link between patients and claims
    link3_found = any(
        link.from_dataset == "patients" and link.from_column == "id" and
        link.to_dataset == "claims" and link.to_column == "patientid"
        for link in results.links
    ) or any(
        link.to_dataset == "patients" and link.to_column == "id" and
        link.from_dataset == "claims" and link.from_column == "patientid"
        for link in results.links
    )
    assert link3_found, "Expected link between patients.id and claims.patientid not found"

    # Verify that intersection metrics are populated
    for link in results.links:
        assert link.intersect_count is not None
        assert link.intersect_count > 0
        assert link.intersect_ratio_col1 is not None
        assert 0 <= link.intersect_ratio_col1 <= 1
        assert link.intersect_ratio_col2 is not None
        assert 0 <= link.intersect_ratio_col2 <= 1
        assert link.accuracy is not None
        assert 0 <= link.accuracy <= 1
