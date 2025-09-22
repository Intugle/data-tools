from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

from intugle.adapters.models import (
    ColumnProfile,
    DataSetData,
    ProfilingOutput,
)

if TYPE_CHECKING:
    from intugle.analysis.models import DataSet


class Adapter(ABC):
    @abstractmethod
    def profile(self, data: Any, table_name: str) -> ProfilingOutput:
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
    def execute(self, query: str):
        raise NotImplementedError()
    
    @abstractmethod
    def to_df(self: DataSetData, date, table_name: str):
        raise NotImplementedError()
    
    def get_details(self, _: DataSetData):
        return None

    @abstractmethod
    def intersect_count(self, table1: "DataSet", column1_name: str, table2: "DataSet", column2_name: str) -> int:
        raise NotImplementedError()
