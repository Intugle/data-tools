import os

import pandas as pd
import pytest

from intugle.nosql.writer import ParquetTarget


@pytest.fixture
def output_dir(tmp_path):
    d = tmp_path / "parquet_output"
    d.mkdir()
    return str(d)


class TestParquetWriter:
    def test_write_parquet(self, output_dir):
        """Run the parser logic (simulate) and check if file exists."""
        writer = ParquetTarget(output_dir)
        df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
        tables = {"root": df}
        
        writer.write(tables)
        
        expected_file = os.path.join(output_dir, "root.parquet")
        assert os.path.exists(expected_file)

    def test_read_back(self, output_dir):
        """Read the parquet file with pandas and verify data matches."""
        writer = ParquetTarget(output_dir)
        df_original = pd.DataFrame({"id": [1, 2], "val": [10, 20]})
        tables = {"data": df_original}
        
        writer.write(tables)
        
        file_path = os.path.join(output_dir, "data.parquet")
        df_read = pd.read_parquet(file_path)
        
        pd.testing.assert_frame_equal(df_original, df_read)
    
    def test_empty_dataframe(self, output_dir):
        """Empty DataFrames should probably NOT ideally be written, or handle gracefully."""
        writer = ParquetTarget(output_dir)
        df_empty = pd.DataFrame()
        tables = {"empty": df_empty}
        
        writer.write(tables)
        
        # Current implementation skips writing empty dataframes
        expected_file = os.path.join(output_dir, "empty.parquet")
        assert not os.path.exists(expected_file)
