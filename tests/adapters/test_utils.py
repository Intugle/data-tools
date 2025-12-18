"""
Unit tests for utility functions in src/intugle/adapters/utils.py
"""

import numpy as np
import pytest

from intugle.adapters.utils import convert_to_native


class TestConvertToNative:
    """Test suite for the convert_to_native function."""

    def test_convert_numpy_int64(self):
        """Test conversion of numpy int64 to native Python int."""
        result = convert_to_native(np.int64(42))
        assert result == 42
        assert isinstance(result, int)

    def test_convert_numpy_int32(self):
        """Test conversion of numpy int32 to native Python int."""
        result = convert_to_native(np.int32(100))
        assert result == 100
        assert isinstance(result, int)

    def test_convert_numpy_float64(self):
        """Test conversion of numpy float64 to native Python float."""
        result = convert_to_native(np.float64(3.14159))
        assert result == 3.14159
        assert isinstance(result, float)

    def test_convert_numpy_float32(self):
        """Test conversion of numpy float32 to native Python float."""
        result = convert_to_native(np.float32(2.718))
        assert abs(result - 2.718) < 0.001  # Use approximate comparison for float32
        assert isinstance(result, float)

    def test_convert_numpy_bool_true(self):
        """Test conversion of numpy bool True to native Python bool."""
        result = convert_to_native(np.bool_(True))
        assert result is True
        assert isinstance(result, bool)

    def test_convert_numpy_bool_false(self):
        """Test conversion of numpy bool False to native Python bool."""
        result = convert_to_native(np.bool_(False))
        assert result is False
        assert isinstance(result, bool)

    def test_convert_list_with_numpy_types(self):
        """Test conversion of list containing numpy types."""
        input_list = [np.int64(1), np.int64(2), np.int64(3)]
        result = convert_to_native(input_list)
        assert result == [1, 2, 3]
        assert all(isinstance(x, int) for x in result)

    def test_convert_tuple_with_numpy_types(self):
        """Test conversion of tuple containing numpy types."""
        input_tuple = (np.float64(1.5), np.float64(2.5), np.float64(3.5))
        result = convert_to_native(input_tuple)
        assert result == [1.5, 2.5, 3.5]  # Note: tuples are converted to lists
        assert all(isinstance(x, float) for x in result)

    def test_convert_mixed_list(self):
        """Test conversion of list with mixed numpy and native types."""
        input_list = [np.int64(10), 20, np.float64(3.14), "hello"]
        result = convert_to_native(input_list)
        assert result == [10, 20, 3.14, "hello"]
        assert isinstance(result[0], int)
        assert isinstance(result[1], int)
        assert isinstance(result[2], float)
        assert isinstance(result[3], str)

    def test_convert_nested_list(self):
        """Test conversion of nested list structures."""
        input_nested = [
            [np.int64(1), np.int64(2)],
            [np.float64(3.0), np.float64(4.0)]
        ]
        result = convert_to_native(input_nested)
        assert result == [[1, 2], [3.0, 4.0]]
        assert isinstance(result[0][0], int)
        assert isinstance(result[1][0], float)

    def test_convert_nested_tuple(self):
        """Test conversion of nested tuple structures."""
        input_nested = (
            (np.int64(5), np.int64(6)),
            (np.bool_(True), np.bool_(False))
        )
        result = convert_to_native(input_nested)
        assert result == [[5, 6], [True, False]]
        assert isinstance(result[0][0], int)
        assert isinstance(result[1][0], bool)

    def test_convert_deeply_nested_structure(self):
        """Test conversion of deeply nested structures."""
        input_deep = [
            [
                [np.int64(1), np.int64(2)],
                [np.float64(3.0)]
            ],
            [
                [np.bool_(True)]
            ]
        ]
        result = convert_to_native(input_deep)
        assert result == [[[1, 2], [3.0]], [[True]]]
        assert isinstance(result[0][0][0], int)
        assert isinstance(result[0][1][0], float)
        assert isinstance(result[1][0][0], bool)

    def test_convert_empty_list(self):
        """Test conversion of empty list."""
        result = convert_to_native([])
        assert result == []
        assert isinstance(result, list)

    def test_convert_empty_tuple(self):
        """Test conversion of empty tuple."""
        result = convert_to_native(())
        assert result == []
        assert isinstance(result, list)

    def test_convert_native_int(self):
        """Test that native Python int is returned unchanged."""
        result = convert_to_native(42)
        assert result == 42
        assert isinstance(result, int)

    def test_convert_native_float(self):
        """Test that native Python float is returned unchanged."""
        result = convert_to_native(3.14)
        assert result == 3.14
        assert isinstance(result, float)

    def test_convert_native_bool(self):
        """Test that native Python bool is returned unchanged."""
        result = convert_to_native(True)
        assert result is True
        assert isinstance(result, bool)

    def test_convert_native_string(self):
        """Test that native Python string is returned unchanged."""
        result = convert_to_native("hello world")
        assert result == "hello world"
        assert isinstance(result, str)

    def test_convert_none(self):
        """Test that None is returned unchanged."""
        result = convert_to_native(None)
        assert result is None

    def test_convert_numpy_array_scalar(self):
        """Test conversion of numpy array with single element (0-dimensional)."""
        # Note: np.array(42) creates a 0-d array, not a scalar
        # The function doesn't convert arrays, only numpy scalars
        result = convert_to_native(np.array(42))
        # Arrays are returned unchanged by convert_to_native
        assert np.array_equal(result, np.array(42))

    def test_convert_list_with_none(self):
        """Test conversion of list containing None values."""
        input_list = [np.int64(1), None, np.int64(3)]
        result = convert_to_native(input_list)
        assert result == [1, None, 3]

    def test_convert_complex_mixed_structure(self):
        """Test conversion of complex structure with various types."""
        input_complex = [
            np.int64(100),
            [np.float64(1.5), "text", None],
            (np.bool_(True), [np.int32(7), np.int32(8)]),
            {"key": "value"}  # Dict should pass through unchanged
        ]
        result = convert_to_native(input_complex)
        expected = [
            100,
            [1.5, "text", None],
            [True, [7, 8]],
            {"key": "value"}
        ]
        assert result == expected

    def test_convert_numpy_uint_types(self):
        """Test conversion of numpy unsigned integer types."""
        result_uint8 = convert_to_native(np.uint8(255))
        result_uint16 = convert_to_native(np.uint16(65535))
        result_uint32 = convert_to_native(np.uint32(4294967295))
        
        assert result_uint8 == 255
        assert result_uint16 == 65535
        assert result_uint32 == 4294967295
        assert all(isinstance(r, int) for r in [result_uint8, result_uint16, result_uint32])

    def test_convert_numpy_string(self):
        """Test conversion of numpy string types."""
        result = convert_to_native(np.str_("numpy string"))
        assert result == "numpy string"
        assert isinstance(result, str)
