import pytest

from intugle.link_predictor.models import RelationshipType, _determine_relationship_cardinality


@pytest.mark.parametrize(
    "from_uniqueness, to_uniqueness, expected_type, expected_source, expected_target",
    [
        (1.0, 1.0, RelationshipType.ONE_TO_ONE, "tableB", "tableA"),  # Equal uniqueness => swap (target becomes source)
        (0.9, 0.9, RelationshipType.ONE_TO_ONE, "tableB", "tableA"),  # Equal => swap
        (1.0, 0.9, RelationshipType.ONE_TO_ONE, "tableA", "tableB"),  # Source > Target => Keep source
        (1.0, 0.5, RelationshipType.ONE_TO_MANY, "tableA", "tableB"),
        (0.5, 1.0, RelationshipType.ONE_TO_MANY, "tableB", "tableA"),  # Swapped
        (0.5, 0.5, RelationshipType.MANY_TO_MANY, "tableA", "tableB"),
        (None, None, RelationshipType.MANY_TO_MANY, "tableA", "tableB"),
    ]
)
def test_determine_relationship_cardinality(from_uniqueness, to_uniqueness, expected_type, expected_source, expected_target):
    
    src_table = "tableA"
    tgt_table = "tableB"
    src_cols = ["colA"]
    tgt_cols = ["colB"]
    
    # Logic note: if swapping happens, columns should also swap.
    # We test simplified cases here.
    
    final_src_table, final_src_cols, final_tgt_table, final_tgt_cols, rel_type = _determine_relationship_cardinality(
        src_table, src_cols, tgt_table, tgt_cols, from_uniqueness, to_uniqueness
    )
    
    assert rel_type == expected_type
    assert final_src_table == expected_source
    assert final_tgt_table == expected_target
    
    if final_src_table == src_table:
        assert final_src_cols == src_cols
        assert final_tgt_cols == tgt_cols
    else:
        assert final_src_cols == tgt_cols
        assert final_tgt_cols == src_cols

