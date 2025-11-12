from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional

import pandas as pd

from intugle.adapters.models import (
    ColumnProfile,
    DataSetData,
    ProfilingOutput,
)

if TYPE_CHECKING:
    from intugle.analysis.models import DataSet
    from intugle.models.manifest import Manifest


class Adapter(ABC):
    @property
    @abstractmethod
    def database(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def schema(self) -> Optional[str]:
        pass

    @property
    @abstractmethod
    def source_name(self) -> Optional[str]:
        pass

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
    def load(self, data: Any, table_name: str):
        ...

    @abstractmethod
    def execute(self, query: str):
        raise NotImplementedError()

    @abstractmethod
    def to_df(self, data: DataSetData, table_name: str):
        raise NotImplementedError()

    @abstractmethod
    def to_df_from_query(self, query: str) -> pd.DataFrame:
        raise NotImplementedError()

    @abstractmethod
    def create_table_from_query(
        self, table_name: str, query: str, materialize: str = "view", **kwargs
    ) -> str:
        raise NotImplementedError()

    @abstractmethod
    def create_new_config_from_etl(self, etl_name: str) -> DataSetData:
        raise NotImplementedError()

    def deploy_semantic_model(self, manifest: "Manifest", **kwargs):
        """Deploys a semantic model to the target system."""
        raise NotImplementedError()

    def get_details(self, _: DataSetData):
        return None

    @abstractmethod
    def intersect_count(
        self, table1: "DataSet", column1_name: str, table2: "DataSet", column2_name: str
    ) -> int:
        raise NotImplementedError()

    @abstractmethod
    def get_composite_key_uniqueness(
        self, table_name: str, columns: list[str], dataset_data: DataSetData
    ) -> int:
        raise NotImplementedError()

    @abstractmethod
    def intersect_composite_keys_count(
        self,
        table1: "DataSet",
        columns1: list[str],
        table2: "DataSet",
        columns2: list[str],
    ) -> int:
        raise NotImplementedError()
