from abc import ABC, abstractmethod
from typing import Any

from .models import ColumnProfileOutput, DataTypeIdentificationL1Output, ProfilingOutput


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
        sample_limit: int = 200,
    ) -> ColumnProfileOutput:
        pass

    @abstractmethod
    def datatype_identification_l1(
        df: Any, 
        table_name: str, 
        column_stats: dict[str, ColumnProfileOutput],
    ) -> list[DataTypeIdentificationL1Output]:
        pass
    
