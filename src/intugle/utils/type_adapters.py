from typing import TypeVar

from pydantic import TypeAdapter

T = TypeVar("T")


def list_type_adapter(data: list, _typ: T) -> list[T]:
    return TypeAdapter(list[_typ]).validate_python([dict(d) for d in data])

