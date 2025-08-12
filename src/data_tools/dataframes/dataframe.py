from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

from .models import (
    BusinessGlossaryOutput,
    ColumnProfile,
    DataTypeIdentificationL1Output,
    DataTypeIdentificationL2Input,
    DataTypeIdentificationL2Output,
    KeyIdentificationOutput,
    ProfilingOutput,
)


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
    ) -> ColumnProfile:
        pass

    @abstractmethod
    def datatype_identification_l1(
        df: Any, 
        table_name: str, 
        column_stats: dict[str, ColumnProfile],
    ) -> list[DataTypeIdentificationL1Output]:
        pass

    @abstractmethod
    def datatype_identification_l2(
        df: Any, 
        table_name: str, 
        column_stats: list[DataTypeIdentificationL2Input],
    ) -> list[DataTypeIdentificationL2Output]:
        pass

    @abstractmethod
    def key_identification(
        table_name: str, 
        column_stats: pd.DataFrame,
    ) -> KeyIdentificationOutput:
        pass

    @abstractmethod
    def generate_business_glossary(
        self,
        table_name: str,
        column_stats: pd.DataFrame,
        domain: str = "",
    ) -> BusinessGlossaryOutput:
        pass
