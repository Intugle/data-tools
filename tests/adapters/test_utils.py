import numpy as np
from intugle.adapters.utils import convert_to_native
import pytest

def test_numpy_scalar_int():
    value = np.int64(10)
    result = convert_to_native(value)
    assert isinstance(result, int)
    assert result == 10


def test_numpy_scalar_float():
    value = np.float32(3.14)
    result = convert_to_native(value)
    assert isinstance(result, float)
    assert result == pytest.approx(3.14)


def test_numpy_scalar_bool():
    value = np.bool_(True)
    result = convert_to_native(value)
    assert isinstance(result, bool)
    assert result is True


def test_list_with_numpy_scalars():
    value = [np.int64(1), np.float32(2.5)]
    result = convert_to_native(value)
    assert result == [1, 2.5]
    assert all(not isinstance(v, np.generic) for v in result)


def test_tuple_with_numpy_scalars():
    value = (np.int64(1), np.bool_(False))
    result = convert_to_native(value)
    assert result == [1, False]  # tuple converted to list
    assert isinstance(result, list)


def test_nested_structures():
    value = [[np.int64(1)], (np.float32(2.2),)]
    result = convert_to_native(value)
    assert result[0] == [1]
    assert result[1][0] == pytest.approx(2.2)


def test_empty_list():
    value = []
    result = convert_to_native(value)
    assert result == []


def test_already_native_type():
    value = "hello"
    result = convert_to_native(value)
    assert result == "hello"
