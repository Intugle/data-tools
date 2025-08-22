from typing import Iterable, Iterator, List, MutableSet, Optional, Sequence, TypeVar, overload

SLICE_ALL = slice(None)
_T = TypeVar("_T")


class OrderedSet(MutableSet[_T], Sequence[_T]):
    def __init__(self, initalize: Optional[List[_T]] = None):
        if initalize is None:
            initalize = []
        self.items = initalize

    def add(self, element: _T) -> None:
        if element not in self.items:
            self.items.append(element)

    append = add

    def remove(self, element: _T) -> None:
        if element in self.items:
            self.items.remove(element)

    discard = remove

    def __iter__(self) -> Iterator[_T]:
        return iter(self.items)

    def __len__(self) -> int:
        """
        Returns the number of unique elements in the ordered set

        Example:
            >>> len(OrderedSet([]))
            0
            >>> len(OrderedSet([1, 2]))
            2
        """
        return len(self.items)

    @overload
    def __getitem__(self, index: slice) -> "OrderedSet[_T]": ...

    @overload
    def __getitem__(self, index: Sequence[int]) -> List[_T]: ...

    @overload
    def __getitem__(self, index: int) -> _T: ...

    # concrete implementation
    def __getitem__(self, index):
        """
        Get the item at a given index.

        If `index` is a slice, you will get back that slice of items, as a
        new OrderedSet.

        If `index` is a list or a similar iterable, you'll get a list of
        items corresponding to those indices. This is similar to NumPy's
        "fancy indexing". The result is not an OrderedSet because you may ask
        for duplicate indices, and the number of elements returned should be
        the number of elements asked for.

        Example:
            >>> oset = OrderedSet([1, 2, 3])
            >>> oset[1]
            2
        """
        if isinstance(index, slice) and index == SLICE_ALL:
            return self.copy()
        elif isinstance(index, Iterable):
            return [self.items[i] for i in index]
        elif isinstance(index, slice) or hasattr(index, "__index__"):
            result = self.items[index]
            if isinstance(result, list):
                return self.__class__(result)
            else:
                return result
        else:
            raise TypeError("Don't know how to index an OrderedSet by %r" % index)

    def __repr__(self) -> str:
        if not self:
            return f"{self.__class__.__name__}()"
        return f"{self.__class__.__name__}({list(self)!r})"

    def copy(self) -> "OrderedSet[_T]":
        """
        Return a shallow copy of this object.

        Example:
            >>> this = OrderedSet([1, 2, 3])
            >>> other = this.copy()
            >>> this == other
            True
            >>> this is other
            False
        """
        return self.__class__(self)
