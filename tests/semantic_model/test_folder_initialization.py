import pandas as pd
import pytest

from intugle.semantic_model import SemanticModel


def test_initialize_from_folder_loads_supported_files(tmp_path):
    """
    Verify that passing a folder path correctly loads supported files.
    """
    csv_file = tmp_path / "users.csv"
    parquet_file = tmp_path / "orders.parquet"

    pd.DataFrame({"id": [1, 2]}).to_csv(csv_file, index=False)
    pd.DataFrame({"id": [10, 20]}).to_parquet(parquet_file)

    sm = SemanticModel(str(tmp_path))

    assert "users" in sm.datasets
    assert "orders" in sm.datasets
    assert len(sm.datasets) == 2


def test_initialize_from_folder_ignores_unsupported_files(tmp_path):
    """
    Verify that unsupported files are ignored.
    """
    (tmp_path / "readme.txt").write_text("ignore me")

    csv_file = tmp_path / "data.csv"
    pd.DataFrame({"x": [1]}).to_csv(csv_file, index=False)

    sm = SemanticModel(str(tmp_path))

    assert "data" in sm.datasets
    assert len(sm.datasets) == 1


def test_initialize_from_folder_extension_mapping(tmp_path):
    """
    Verify correct mapping of file extensions to DuckDB types.
    """
    csv_file = tmp_path / "a.csv"
    parquet_file = tmp_path / "b.parquet"

    pd.DataFrame({"x": [1]}).to_csv(csv_file, index=False)
    pd.DataFrame({"y": [2]}).to_parquet(parquet_file)

    sm = SemanticModel(str(tmp_path))

    csv_dataset = sm.datasets["a"]
    parquet_dataset = sm.datasets["b"]

    assert csv_dataset.data["type"] == "csv"
    assert parquet_dataset.data["type"] == "parquet"


def test_initialize_from_folder_empty_directory_raises(tmp_path):
    """
    Verify that an empty directory raises a clear error.
    """
    with pytest.raises(ValueError):
        SemanticModel(str(tmp_path))
