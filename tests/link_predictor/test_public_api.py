"""Tests for link_predictor public API exports in __init__.py."""


def test_public_api_imports_from_package():
    """Users can import main classes directly from intugle.link_predictor."""
    from intugle.link_predictor import (
        LinkPredictionResult,
        LinkPredictionSaver,
        LinkPredictor,
        NoLinksFoundError,
        PredictedLink,
    )

    assert LinkPredictor is not None
    assert LinkPredictionSaver is not None
    assert PredictedLink is not None
    assert LinkPredictionResult is not None
    assert NoLinksFoundError is not None


def test_all_exports_match_public_api():
    """__all__ should expose exactly the documented public API."""
    import intugle.link_predictor as link_predictor

    expected = {
        "LinkPredictor",
        "LinkPredictionSaver",
        "PredictedLink",
        "LinkPredictionResult",
        "NoLinksFoundError",
    }
    assert set(link_predictor.__all__) == expected
