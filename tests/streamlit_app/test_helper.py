"""Tests for streamlit_app/helper.py file reading functions."""

import io

from collections import namedtuple
from dataclasses import dataclass
from unittest.mock import Mock

import pandas as pd
import pytest

from src.intugle.streamlit_app.helper import (
    _read_bytes_to_df_core,
    clean_table_name,
    link_to_dict,
    normalize_col_name,
    predicted_links_to_df,
    read_bytes_to_df,
    read_file_to_df,
    sizeof_mb,
    standardize_columns,
    standardize_table_name,
)


class TestReadBytesToDfCore:
    """Test the core helper function _read_bytes_to_df_core."""

    def test_read_csv_utf8(self):
        """Test reading a CSV file with UTF-8 encoding."""
        csv_data = b"name,age,city\nAlice,30,NYC\nBob,25,LA"
        df, note = _read_bytes_to_df_core("test.csv", csv_data)

        assert note == ""
        assert len(df) == 2
        assert list(df.columns) == ["name", "age", "city"]
        assert df.iloc[0]["name"] == "Alice"
        assert df.iloc[0]["age"] == 30
        assert df.iloc[1]["name"] == "Bob"

    def test_read_csv_latin1_fallback(self):
        """Test reading a CSV file that requires latin-1 encoding."""
        # CSV with latin-1 character (café)
        csv_content = "name,beverage\nJohn,café\n"
        csv_data = csv_content.encode("latin-1")
        df, note = _read_bytes_to_df_core("test.csv", csv_data)

        assert "latin-1" in note
        assert len(df) == 1

    def test_read_excel_xlsx(self):
        """Test reading an Excel .xlsx file."""
        # Create a simple Excel file in memory
        df_original = pd.DataFrame({"name": ["Alice", "Bob"], "age": [30, 25]})
        excel_buffer = io.BytesIO()
        df_original.to_excel(excel_buffer, index=False, sheet_name="Sheet1")
        excel_data = excel_buffer.getvalue()

        df, note = _read_bytes_to_df_core("test.xlsx", excel_data)

        assert "Sheet1" in note
        assert len(df) == 2
        assert list(df.columns) == ["name", "age"]
        assert df.iloc[0]["name"] == "Alice"

    def test_read_excel_xls(self):
        """Test reading an Excel .xls file (uses same logic as xlsx)."""
        # Create Excel file
        df_original = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        excel_buffer = io.BytesIO()
        df_original.to_excel(excel_buffer, index=False, engine="openpyxl")
        excel_data = excel_buffer.getvalue()

        df, note = _read_bytes_to_df_core("test.xls", excel_data)

        assert "Sheet" in note
        assert len(df) == 2

    def test_unsupported_extension_raises_error(self):
        """Test handling of unsupported file extensions."""
        with pytest.raises(ValueError, match="Unsupported file type"):
            _read_bytes_to_df_core("test.txt", b"some text")

    def test_unsupported_extension_json(self):
        """Test that JSON files raise an error."""
        with pytest.raises(ValueError, match="Unsupported file type"):
            _read_bytes_to_df_core("data.json", b'{"key": "value"}')


class TestReadBytesToDf:
    """Test the read_bytes_to_df function."""

    def test_delegates_to_core_csv(self):
        """Test that read_bytes_to_df properly delegates to the core function."""
        csv_data = b"name,age\nAlice,30"
        df, note = read_bytes_to_df("test.csv", csv_data)

        assert note == ""
        assert len(df) == 1
        assert df.iloc[0]["name"] == "Alice"
        assert df.iloc[0]["age"] == 30

    def test_delegates_to_core_excel(self):
        """Test delegation with Excel file."""
        df_original = pd.DataFrame({"x": [1, 2, 3]})
        excel_buffer = io.BytesIO()
        df_original.to_excel(excel_buffer, index=False)
        excel_data = excel_buffer.getvalue()

        df, note = read_bytes_to_df("data.xlsx", excel_data)

        assert len(df) == 3
        assert "Sheet" in note

    def test_maintains_same_behavior_as_before(self):
        """Ensure backward compatibility with original function."""
        csv_data = b"col1,col2,col3\n1,2,3\n4,5,6"
        df, note = read_bytes_to_df("test.csv", csv_data)

        assert isinstance(df, pd.DataFrame)
        assert isinstance(note, str)
        assert len(df) == 2
        assert len(df.columns) == 3


class TestReadFileToDf:
    """Test the read_file_to_df function."""

    def test_valid_uploaded_csv_file(self):
        """Test reading a valid uploaded CSV file object."""
        # Mock Streamlit UploadedFile
        mock_file = Mock()
        mock_file.name = "test.csv"
        mock_file.read.return_value = b"name,age\nAlice,30"

        df, note = read_file_to_df(mock_file)

        assert note == ""
        assert len(df) == 1
        assert df.iloc[0]["name"] == "Alice"
        assert df.iloc[0]["age"] == 30

    def test_valid_uploaded_excel_file(self):
        """Test reading a valid uploaded Excel file object."""
        # Create Excel data
        df_original = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        excel_buffer = io.BytesIO()
        df_original.to_excel(excel_buffer, index=False)
        excel_data = excel_buffer.getvalue()

        # Mock file
        mock_file = Mock()
        mock_file.name = "data.xlsx"
        mock_file.read.return_value = excel_data

        df, note = read_file_to_df(mock_file)

        assert len(df) == 2
        assert "Sheet" in note

    def test_invalid_uploaded_file_none(self):
        """Test handling of None as uploaded file."""
        with pytest.raises(ValueError, match="Invalid uploaded file object"):
            read_file_to_df(None)

    def test_invalid_uploaded_file_missing_name(self):
        """Test handling of file object missing 'name' attribute."""
        mock_file = Mock()
        del mock_file.name
        mock_file.read.return_value = b"data"

        with pytest.raises(ValueError, match="Invalid uploaded file object"):
            read_file_to_df(mock_file)

    def test_invalid_uploaded_file_missing_read(self):
        """Test handling of file object missing 'read' method."""
        mock_file = Mock()
        mock_file.name = "test.csv"
        del mock_file.read

        with pytest.raises(ValueError, match="Invalid uploaded file object"):
            read_file_to_df(mock_file)

    def test_file_with_latin1_encoding(self):
        """Test that latin-1 encoding fallback works through read_file_to_df."""
        csv_content = "name,item\nPierre,café\n"
        csv_data = csv_content.encode("latin-1")

        mock_file = Mock()
        mock_file.name = "test.csv"
        mock_file.read.return_value = csv_data

        df, note = read_file_to_df(mock_file)

        assert "latin-1" in note
        assert len(df) == 1


class TestIntegration:
    """Integration tests to ensure both functions work identically."""

    def test_both_functions_produce_same_result_csv(self):
        """Test that both functions produce identical results for CSV."""
        csv_data = b"name,age,city\nAlice,30,NYC\nBob,25,LA\nCharlie,35,SF"

        # Test read_bytes_to_df
        df1, msg1 = read_bytes_to_df("test.csv", csv_data)

        # Test read_file_to_df with mock
        mock_file = Mock()
        mock_file.name = "test.csv"
        mock_file.read.return_value = csv_data
        df2, msg2 = read_file_to_df(mock_file)

        # Both should produce identical results
        assert msg1 == msg2 == ""
        assert df1.equals(df2)
        assert len(df1) == 3
        assert list(df1.columns) == ["name", "age", "city"]

    def test_both_functions_produce_same_result_excel(self):
        """Test that both functions produce identical results for Excel."""
        df_original = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        excel_buffer = io.BytesIO()
        df_original.to_excel(excel_buffer, index=False, sheet_name="Data")
        excel_data = excel_buffer.getvalue()

        # Test read_bytes_to_df
        df1, msg1 = read_bytes_to_df("file.xlsx", excel_data)

        # Test read_file_to_df with mock
        mock_file = Mock()
        mock_file.name = "file.xlsx"
        mock_file.read.return_value = excel_data
        df2, msg2 = read_file_to_df(mock_file)

        # Both should produce identical results
        assert msg1 == msg2
        assert "Data" in msg1
        assert df1.equals(df2)
        assert len(df1) == 3

    def test_error_handling_consistency(self):
        """Test that error handling is consistent between functions."""
        # Test with unsupported file type
        bad_data = b"random bytes"

        # read_bytes_to_df should raise error
        with pytest.raises(ValueError, match="Unsupported file type"):
            read_bytes_to_df("file.pdf", bad_data)

        # read_file_to_df should raise same error
        mock_file = Mock()
        mock_file.name = "file.pdf"
        mock_file.read.return_value = bad_data

        with pytest.raises(ValueError, match="Unsupported file type"):
            read_file_to_df(mock_file)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_csv_file(self):
        """Test reading an empty CSV file."""
        csv_data = b"col1,col2\n"
        df, note = read_bytes_to_df("empty.csv", csv_data)

        assert len(df) == 0
        assert list(df.columns) == ["col1", "col2"]

    def test_csv_with_special_characters_in_filename(self):
        """Test that filename with special chars works."""
        csv_data = b"a,b\n1,2"
        df, note = read_bytes_to_df("my-file_2024.CSV", csv_data)

        assert len(df) == 1

    def test_case_insensitive_file_extension(self):
        """Test that file extensions are case-insensitive."""
        csv_data = b"x,y\n1,2"

        df1, _ = read_bytes_to_df("file.CSV", csv_data)
        df2, _ = read_bytes_to_df("file.csv", csv_data)
        df3, _ = read_bytes_to_df("file.Csv", csv_data)

        assert df1.equals(df2)
        assert df2.equals(df3)


class TestHelperUtilities:
    """Unit tests for helper utilities we recently annotated."""

    def test_standardize_columns_basic(self):
        df = pd.DataFrame({" Name ": [1], "AGE": [2], "name": [3], "first name": [4], "": [5]})
        out = standardize_columns(df)
        assert list(out.columns) == ["name", "age", "name_1", "first_name", "col"]
        # Values preserved in the corresponding columns
        assert out["name"].iloc[0] == 1
        assert out["age"].iloc[0] == 2
        assert out["name_1"].iloc[0] == 3

    def test_standardize_columns_empty_and_nonstring(self):
        # Columns can be None, numeric, or special chars
        df = pd.DataFrame({None: [1], 123: [2], "!!!": [3]})
        out = standardize_columns(df)
        # None -> 'none', 123 -> '123', '!!!' -> becomes blank -> 'col'
        assert list(out.columns) == ["none", "123", "col"]

    def test_standardize_columns_many_duplicates(self):
        # Many duplicates should get incrementing suffixes
        # Use explicit columns list to allow duplicate column names
        df = pd.DataFrame([[1, 2, 3, 4, 5]], columns=["X", "x", " X ", "x", "X"])
        out = standardize_columns(df)
        # Normalized base is 'x'; expect unique increments
        assert list(out.columns) == ["x", "x_1", "x_2", "x_3", "x_4"]

    def test_normalize_col_name_with_various_types(self):
        assert normalize_col_name("None") == "none"
        assert normalize_col_name("123") == "123"
        assert normalize_col_name("First Name!") == "first_name"

    def test_standardize_table_name(self):
        assert standardize_table_name("  My Table!  ") == "my_table"
        assert standardize_table_name("Simple.Name-123") == "simple_name_123"

    def test_clean_table_name(self):
        assert clean_table_name("  My File.csv") == "My_File"
        # It should preserve case and only remove extension
        assert clean_table_name("Some Folder/Another file.TXT") == "Some Folder/Another_file"

    def test_sizeof_mb_int_and_float(self):
        assert sizeof_mb(1048576) == 1.0
        assert sizeof_mb(1572864.0) == 1.5

    def test_predicted_links_to_df_basic_and_composite(self):
        links = [
            {
                "from_dataset": "A",
                "from_column": "col1",
                "to_dataset": "B",
                "to_column": "col2",
                "intersect_count": 5,
                "accuracy": 0.9,
            },
            {
                "from_dataset": "A",
                "from_columns": ["col1", "col3"],
                "to_dataset": "B",
                "to_columns": ["col2", "col4"],
                "intersect_count": 2,
                "accuracy": 0.95,
            },
            {
                "from_dataset": "C",
                "from_column": "dcol",
                "to_dataset": "D",
                "to_column": "ecol",
                "intersect_count": 1,
                "accuracy": 0.5,
            },
        ]
        df = predicted_links_to_df(links)
        assert "from_columns" in df.columns
        assert "to_columns" in df.columns
        # from_column should be a single-value display for non-composite and parentheses for composite
        assert df.loc[0, "from_column"] == "col1"
        assert df.loc[1, "from_column"] == "(col1, col3)"
        # is_composite flag for the second row should be True
        assert df.loc[1, "is_composite"] is True
        # subtype columns are preserved
        assert int(df.loc[0, "intersect_count"]) == 5

    def test_predicted_links_to_df_numeric_and_mixed_types(self):
        links = [
            {
                "from_dataset": "X",
                "from_columns": [1, 2],
                "to_dataset": "Y",
                "to_columns": [3, 4],
                "intersect_count": 7,
            },
            {"from_dataset": "X", "from_column": 5, "to_dataset": "Y", "to_column": 6},
            {"from_dataset": "Z", "to_column": "c"},
        ]
        df = predicted_links_to_df(links)
        # from_columns should be lists of strings
        assert isinstance(df.loc[0, "from_columns"], list)
        assert df.loc[0, "from_columns"] == ["1", "2"]
        # single numeric legacy column should be coerced to str and display properly
        assert df.loc[1, "from_columns"] == ["5"]
        assert df.loc[1, "from_column"] == "5"
        # missing values should result in empty list and empty display string
        assert df.loc[2, "from_columns"] == []
        assert df.loc[2, "from_column"] == ""

    def test_predicted_links_to_df_prefer_list_over_legacy(self):
        # Provide both list and legacy scalar; list should take precedence
        links = [
            {"from_dataset": "A", "from_columns": ["a", "b"], "from_column": "a", "to_dataset": "B", "to_column": "c"},
            {"from_dataset": "A", "from_columns": [], "from_column": "x", "to_dataset": "B", "to_column": "c"},
        ]
        df = predicted_links_to_df(links)
        assert df.loc[0, "from_columns"] == ["a", "b"]
        # If list is empty but legacy scalar is present, we should convert legacy to list
        assert df.loc[1, "from_columns"] == ["x"]

    def test_link_to_dict_various_inputs(self):

        @dataclass
        class Person:
            name: str
            age: int

        p = Person("Alice", 30)
        out = link_to_dict(p)
        assert out == {"name": "Alice", "age": 30}

        Point = namedtuple("Point", "x y")
        pt = Point(1, 2)
        out2 = link_to_dict(pt)
        assert out2 == {"x": 1, "y": 2}

        class Obj:
            def __init__(self):
                self.a = 1
                self._b = 2

        o = Obj()
        out3 = link_to_dict(o)
        assert out3 == {"a": 1}

        # fallback: builtin function or object without vars should return a 'value' string
        out4 = link_to_dict(len)  # builtin type object without accessible vars
        assert "value" in out4
        assert isinstance(out4["value"], str)

    def test_link_to_dict_filters_private_keys_in_mapping(self):
        d = {"a": 1, "_b": 2, "c": 3}
        out = link_to_dict(d)
        assert out == {"a": 1, "c": 3}
