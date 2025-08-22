from abc import ABC, abstractmethod
from typing import Any

from intugle.adapters.models import (
    ColumnProfile,
    ProfilingOutput,
)


class Adapter(ABC):
    @abstractmethod
    def profile(self, data: Any) -> ProfilingOutput:
        pass

    @abstractmethod
    def column_profile(
        self,
        data: Any,
        table_name: str,
        column_name: str,
        total_count: int,
        sample_limit: int = 10,
        dtype_sample_limit: int = 10000,
    ) -> ColumnProfile:
        pass
    
    @abstractmethod
    def load():
        ...

    @abstractmethod
    def execute():
        raise NotImplementedError()
