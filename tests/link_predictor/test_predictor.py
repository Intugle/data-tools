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
                from_columns=["id"],
                to_dataset="orders",
                to_columns=["customer_id"],
                intersect_count=1,
                intersect_ratio_from_col=1.0,
                intersect_ratio_to_col=1.0,
                accuracy=1.0,
                from_uniqueness_ratio=1.0,
                to_uniqueness_ratio=0.75,
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
    assert predictor.datasets["customers"].source.table.key.columns == ["id"]

    # 4. Run prediction
    results = predictor.predict(force_recreate=True)

    # 5. Verify that the mocked prediction was called and results are correct
    assert mock_predict_for_pair.call_count == 1
    assert len(results.links) == 1
    assert results.links[0].from_dataset == "customers"
    assert results.links[0].from_uniqueness_ratio == 1.0
    assert results.links[0].to_uniqueness_ratio == 0.75


def test_predictor_with_list_input(mock_predict_for_pair):
    """
    Tests that the LinkPredictor can be initialized with a list of DataSet
    objects, some of which have not been fully analyzed.
    """
    # 1. Prepare a fully analyzed DataSet
    customers_df = pd.DataFrame({"id": [1, 2, 3]})
    processed_dataset = DataSet(customers_df, name="customers")
    # Manually run analysis to populate key
    processed_dataset.profile().identify_datatypes().identify_keys()

    # 2. Prepare a raw DataSet that needs analysis
    orders_df = pd.DataFrame({"order_id": [101, 102], "customer_id": [1, 3]})
    raw_dataset = DataSet(orders_df, name="orders")

    # 3. Initialize the predictor with the list
    predictor = LinkPredictor([processed_dataset, raw_dataset])

    # 4. Verify that both datasets are now fully processed
    assert "customers" in predictor.datasets
    assert "orders" in predictor.datasets
    assert predictor.datasets["customers"].source.table.key is not None
    assert predictor.datasets["orders"].source.table.key is not None
    assert predictor.datasets["orders"].source.table.key.columns == ["order_id"]

    # 5. Run prediction
    results = predictor.predict(force_recreate=True)

    # 6. Verify results
    assert mock_predict_for_pair.call_count == 1
    assert len(results.links) == 1
    assert results.links[0].from_uniqueness_ratio == 1.0
    assert results.links[0].to_uniqueness_ratio == 0.75

def test_predictor_raises_error_with_insufficient_datasets():
    """
    Tests that LinkPredictor raises a ValueError if initialized with fewer than two datasets.
    """
    with pytest.raises(ValueError, match="LinkPredictor requires at least two datasets"):
        LinkPredictor({"customers": pd.DataFrame({"id": [1]})})


def test_predictor_end_to_end_simple_link():
    """
    Tests the LinkPredictor end-to-end with simple dataframes and a single link,
    without mocking the LLM.
    """
    # 1. Prepare dummy dataframes
    customers_df = pd.DataFrame({
        "customer_id": [1, 2, 3, 4],
        "name": ["Alice", "Bob", "Charlie", "David"]
    })
    orders_df = pd.DataFrame({
        "order_id": [101, 102, 103, 104],
        "customer_id": [1, 3, 1, 4],
        "amount": [100, 200, 150, 300]
    })

    datasets = {
        "customers": customers_df,
        "orders": orders_df,
    }

    # 2. Initialize the predictor
    predictor = LinkPredictor(datasets)

    # 3. Run the prediction
    results = predictor.predict(force_recreate=True)

    # 4. Assert that the correct link was found
    assert len(results.links) == 1, f"Expected 1 link, but found {len(results.links)}"
    
    # Find the link regardless of direction
    link = None
    for l in results.links:
        if (
            {l.from_dataset, l.to_dataset} == {"customers", "orders"} and
            {tuple(l.from_columns), tuple(l.to_columns)} == {("customer_id",)}
        ):
            link = l
            break
    
    assert link is not None, "Expected link between customers.customer_id and orders.customer_id not found"

    # Verify that intersection metrics are populated and reasonable
    assert link.intersect_count is not None
    assert link.intersect_count > 0
    assert link.intersect_ratio_from_col is not None
    assert 0 <= link.intersect_ratio_from_col <= 1
    assert link.intersect_ratio_to_col is not None
    assert 0 <= link.intersect_ratio_to_col <= 1
    assert link.accuracy is not None
    assert 0 <= link.accuracy <= 1

    # Specific checks for this data
    assert link.intersect_count == 3
    
    # The ratios depend on the direction, so we check both possibilities
    if link.from_dataset == "customers":
        assert abs(link.intersect_ratio_from_col - 0.75) < 0.01
        assert abs(link.intersect_ratio_to_col - 1.0) < 0.01
        assert abs(link.accuracy - 1.0) < 0.01
        assert abs(link.from_uniqueness_ratio - 1.0) < 0.01
        assert abs(link.to_uniqueness_ratio - 0.75) < 0.01
    else: # from_dataset is "orders"
        assert abs(link.intersect_ratio_from_col - 1.0) < 0.01
        assert abs(link.intersect_ratio_to_col - 0.75) < 0.01
        assert abs(link.accuracy - 1.0) < 0.01
        assert abs(link.from_uniqueness_ratio - 0.75) < 0.01
        assert abs(link.to_uniqueness_ratio - 1.0) < 0.01


def test_predictor_end_to_end_composite_key_link():
    """
    Tests the LinkPredictor end-to-end with composite keys,
    without mocking the LLM.
    """
    # 1. Prepare dummy dataframes with composite keys
    products_df = pd.DataFrame({
        "product_id": [1, 2, 3, 4],
        "category": ["Electronics", "Books", "Electronics", "Clothing"],
        "price": [100, 20, 150, 50]
    })

    # This table has a composite key (order_id, product_id)
    order_items_df = pd.DataFrame({
        "order_id": [101, 101, 102, 102, 103],
        "product_id": [1, 2, 1, 3, 4],
        "quantity": [1, 1, 2, 1, 1]
    })

    # Another table with a composite key (store_id, product_id)
    store_inventory_df = pd.DataFrame({
        "store_id": ["S1", "S1", "S2", "S2", "S3"],
        "product_id": [1, 2, 1, 3, 4],
        "stock": [10, 5, 12, 8, 3]
    })

    datasets = {
        "products": products_df,
        "order_items": order_items_df,
        "store_inventory": store_inventory_df,
    }

    # 2. Initialize the predictor
    predictor = LinkPredictor(datasets)

    # 3. Run the prediction
    results = predictor.predict(force_recreate=True)

    # 4. Assert that the correct links were found
    assert len(results.links) >= 2, f"Expected at least 2 links, but found {len(results.links)}"

    # Check for product_id link between products and order_items (direction-agnostic)
    link1_found = any(
        {link.from_dataset, link.to_dataset} == {"products", "order_items"} and
        {tuple(link.from_columns), tuple(link.to_columns)} == {("product_id",)}
        for link in results.links
    )
    assert link1_found, "Expected link between products.product_id and order_items.product_id not found"

    # Check for product_id link between products and store_inventory (direction-agnostic)
    link2_found = any(
        {link.from_dataset, link.to_dataset} == {"products", "store_inventory"} and
        {tuple(link.from_columns), tuple(link.to_columns)} == {("product_id",)}
        for link in results.links
    )
    assert link2_found, "Expected link between products.product_id and store_inventory.product_id not found"

    # Verify that intersection metrics are populated
    for link in results.links:
        assert link.intersect_count is not None
        assert link.intersect_count > 0
        assert link.intersect_ratio_from_col is not None
        assert 0 <= link.intersect_ratio_from_col <= 1
        assert link.intersect_ratio_to_col is not None
        assert 0 <= link.intersect_ratio_to_col <= 1
        assert link.accuracy is not None
        assert 0 <= link.accuracy <= 1
        assert link.from_uniqueness_ratio is not None
        assert 0 <= link.from_uniqueness_ratio <= 1
        assert link.to_uniqueness_ratio is not None
        assert 0 <= link.to_uniqueness_ratio <= 1


def test_predictor_end_to_end_complex():
    """
    Tests the LinkPredictor end-to-end with more complex dataframes,
    including datetime columns and multiple potential links.
    This test now runs without mocking the LLM.
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

    # Check for the link between customers and orders (direction-agnostic)
    link1_found = any(
        {link.from_dataset, link.to_dataset} == {"customers", "orders"} and
        {tuple(link.from_columns), tuple(link.to_columns)} == {("id",), ("customer_id",)}
        for link in results.links
    )
    assert link1_found, "Expected link between customers.id and orders.customer_id not found"

    # Check for the link between customers and events (direction-agnostic)
    link2_found = any(
        {link.from_dataset, link.to_dataset} == {"customers", "events"} and
        {tuple(link.from_columns), tuple(link.to_columns)} == {("id",), ("user_id",)}
        for link in results.links
    )
    assert link2_found, "Expected link between customers.id and events.user_id not found"
    
    # Verify that intersection metrics are populated
    for link in results.links:
        assert link.intersect_count is not None
        assert link.intersect_count > 0
        assert link.intersect_ratio_from_col is not None
        assert 0 <= link.intersect_ratio_from_col <= 1
        assert link.intersect_ratio_to_col is not None
        assert 0 <= link.intersect_ratio_to_col <= 1
        assert link.accuracy is not None
        assert 0 <= link.accuracy <= 1
        assert link.from_uniqueness_ratio is not None
        assert 0 <= link.from_uniqueness_ratio <= 1
        assert link.to_uniqueness_ratio is not None
        assert 0 <= link.to_uniqueness_ratio <= 1

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
            from_columns=["id"],
            to_dataset="orders",
            to_columns=["customer_id"],
            intersect_count=2,
            intersect_ratio_from_col=0.66,
            intersect_ratio_to_col=1.0,
            accuracy=1.0,
            from_uniqueness_ratio=1.0,
            to_uniqueness_ratio=0.75,
        ),
        PredictedLink(
            from_dataset="users",
            from_columns=["user_id"],
            to_dataset="events",
            to_columns=["user_id"],
            intersect_count=100,
            intersect_ratio_from_col=0.9,
            intersect_ratio_to_col=0.85,
            accuracy=0.9,
            from_uniqueness_ratio=0.95,
            to_uniqueness_ratio=0.80,
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


def test_predictor_end_to_end_composite_key_multiple_links():
    """
    Tests the LinkPredictor end-to-end with composite keys and multiple links
    from one table to another, without mocking the LLM.
    Scenario:
    - Player table: PK = (name, class)
    - Game table: FK1 = (winner_name, winner_class) -> Player (name, class)
                  FK2 = (loser_name, loser_class) -> Player (name, class)
    """
    # 1. Prepare dummy dataframes
    players_df = pd.DataFrame({
        "player_name": ["Alice", "Bob", "Alice", "Charlie"],
        "player_class": ["Warrior", "Mage", "Rogue", "Warrior"],
        "level": [10, 12, 8, None]
    })

    games_df = pd.DataFrame({
        "game_id": [1, 2, 3, 4],
        "winner_name": ["Alice", "Charlie", "Bob", "Alice"],
        "winner_class": ["Warrior", "Warrior", "Mage", "Rogue"],
        "loser_name": ["Bob", "Alice", "Charlie", "Bob"],
        "loser_class": ["Mage", "Rogue", "Warrior", "Mage"],
        "duration_minutes": [15, 20, 10, 18]
    })

    datasets = {
        "players": players_df,
        "games": games_df,
    }

    # 2. Initialize the predictor
    predictor = LinkPredictor(datasets)

    # 3. Run the prediction
    results = predictor.predict(force_recreate=True)

    # 4. Assert that the correct links were found
    assert len(results.links) == 2, f"Expected 2 links, but found {len(results.links)}"

    # Define expected composite keys for easier comparison
    player_pk = ("player_name", "player_class")
    game_winner_fk = ("winner_name", "winner_class")
    game_loser_fk = ("loser_name", "loser_class")

    # Check for the winner link
    winner_link_found = any(
        {link.from_dataset, link.to_dataset} == {"players", "games"} and
        (tuple(link.from_columns) == player_pk and tuple(link.to_columns) == game_winner_fk) or
        (tuple(link.from_columns) == game_winner_fk and tuple(link.to_columns) == player_pk)
        for link in results.links
    )
    assert winner_link_found, "Expected link between players PK and games winner FK not found"

    # Check for the loser link
    loser_link_found = any(
        {link.from_dataset, link.to_dataset} == {"players", "games"} and
        (tuple(link.from_columns) == player_pk and tuple(link.to_columns) == game_loser_fk) or
        (tuple(link.from_columns) == game_loser_fk and tuple(link.to_columns) == player_pk)
        for link in results.links
    )
    assert loser_link_found, "Expected link between players PK and games loser FK not found"

    # Verify that intersection metrics are populated for all links
    for link in results.links:
        assert link.intersect_count is not None
        assert link.intersect_count > 0
        assert link.intersect_ratio_from_col is not None
        assert 0 <= link.intersect_ratio_from_col <= 1
        assert link.intersect_ratio_to_col is not None
        assert 0 <= link.intersect_ratio_to_col <= 1
        assert link.accuracy is not None
        assert 0 <= link.accuracy <= 1
        assert link.from_uniqueness_ratio is not None
        assert 0 <= link.from_uniqueness_ratio <= 1
        assert link.to_uniqueness_ratio is not None
        assert 0 <= link.to_uniqueness_ratio <= 1