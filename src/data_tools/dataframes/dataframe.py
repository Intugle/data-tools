from abc import ABC, abstractmethod
from typing import Optional


class DataFrame(ABC):
    count: Optional[int] = None
    columns: Optional[list[str]] = None
    dtypes: Optional[dict[str, str]] = None

    @abstractmethod
    def profile(self):
        pass
