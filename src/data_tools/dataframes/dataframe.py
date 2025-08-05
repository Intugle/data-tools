from abc import ABC, abstractmethod
from typing import Any

from .models import ProfilingOutput


class DataFrame(ABC):
    @abstractmethod
    def profile(self, df: Any) -> ProfilingOutput:
        pass

    @abstractmethod
    def column_profile(
        self, 
        df: Any,
        table_name: str,
        column_name: str, 
        sample_limit: int = 200
    ) -> ProfilingOutput:
        pass
