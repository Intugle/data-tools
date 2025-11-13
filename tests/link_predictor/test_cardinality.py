import pytest
from intugle.link_predictor.models import PredictedLink
from intugle.models.resources.relationship import RelationshipType


@pytest.mark.parametrize(
    "from_uniqueness, to_uniqueness, expected_type, expected_source_table, expected_target_table",
    [
        # Test case 1: One-to-One
        (
            0.95,
            0.98,
            RelationshipType.ONE_TO_ONE,
            "users",
            "profiles",
        ),
        # Test case 2: One-to-Many
        (
            1.0,
            0.3,
            RelationshipType.ONE_TO_MANY,
            "customers",
            "orders",
        ),
        # Test case 3: Many-to-One (should be swapped to One-to-Many)
        (
            0.4,
            1.0,
            RelationshipType.ONE_TO_MANY,
            "products",
            "order_items",
        ),
        # Test case 4: Many-to-Many
        (
            0.5,
            0.6,
            RelationshipType.MANY_TO_MANY,
            "tags",
            "posts",
        ),
        # Test case 5: Edge case - exactly on the threshold
        (
            0.8,
            0.79,
            RelationshipType.ONE_TO_MANY,
            "tableA",
            "tableB",
        ),
        # Test case 6: Edge case - both on the threshold
        (
            0.8,
            0.8,
            RelationshipType.ONE_TO_ONE,
            "tableC",
            "tableD",
        ),
    ],
)
def test_relationship_cardinality_determination(
    from_uniqueness,
    to_uniqueness,
    expected_type,
    expected_source_table,
    expected_target_table,
):
    """
    Tests that the relationship type is correctly determined based on uniqueness ratios.
    """
    # 1. Create a PredictedLink with the specified uniqueness ratios
    # The actual table names are based on the expected source/target for clarity
    from_table = (
        expected_source_table
        if expected_source_table != expected_target_table
        else "tableA"
    )
    to_table = (
        expected_target_table
        if expected_source_table != expected_target_table
        else "tableB"
    )

    if expected_type == RelationshipType.ONE_TO_MANY and from_uniqueness < to_uniqueness:
        # This is the M:1 case that should be swapped
        from_table, to_table = to_table, from_table

    link = PredictedLink(
        from_dataset=from_table,
        from_columns=["id"],
        to_dataset=to_table,
        to_columns=["foreign_id"],
        from_uniqueness_ratio=from_uniqueness,
        to_uniqueness_ratio=to_uniqueness,
    )

    # 2. Access the relationship property to trigger the logic
    relationship = link.relationship

    # 3. Assert the relationship type is correct
    assert (
        relationship.type == expected_type
    ), f"Expected {expected_type}, but got {relationship.type}"

    # 4. Assert that the source and target are correct (especially for the M:1 swap)
    assert (
        relationship.source.table == expected_source_table
    ), f"Expected source table {expected_source_table}, but got {relationship.source.table}"
    assert (
        relationship.target.table == expected_target_table
    ), f"Expected target table {expected_target_table}, but got {relationship.target.table}"
