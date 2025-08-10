from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from data_tools.core.settings import settings
from data_tools.dataframes.models import DataTypeIdentificationL2Input

from .models import DataSet

if TYPE_CHECKING:
    from data_tools.dataframes.models import ColumnProfileOutput, ProfilingOutput


class AnalysisStep(ABC):
    """Abstract base class for any step in our analysis pipeline."""

    @abstractmethod
    def analyze(self, dataset: DataSet) -> None:
        """
        Performs an analysis and stores its result in the dataset.
        """
        pass


class TableProfiler(AnalysisStep):
    def analyze(self, dataset: DataSet) -> None:
        """
        Performs table-level profiling and saves the result.
        """
        profile = dataset.dataframe_wrapper.profile(dataset.raw_df)
        dataset.results["table_profile"] = profile


class ColumnProfiler(AnalysisStep):
    def analyze(self, dataset: DataSet) -> None:
        """
        Performs column-level profiling for each column.
        This step depends on the 'table_profile' result.
        """
        
        # Dependency check
        if 'table_profile' not in dataset.results:
            raise RuntimeError("TableProfiler must be run before ColumnProfiler.")

        table_profile: ProfilingOutput = dataset.results['table_profile']
        all_column_profiles = {}

        for col_name in table_profile.columns:
            # We would add a method to our DataFrame wrapper to get stats for a single column
            stats = dataset.dataframe_wrapper.column_profile(dataset.raw_df, dataset.name, col_name, settings.UPSTREAM_SAMPLE_LIMIT)
            all_column_profiles[col_name] = stats
            
        dataset.results['column_profiles'] = all_column_profiles


class DataTypeIdentifierL1(AnalysisStep):
    def analyze(self, dataset: DataSet) -> None:
        """
        Performs datatype identification level 1 for each column.
        This step depends on the 'column_profiles' result.
        """
        
        # Dependency check
        if 'column_profiles' not in dataset.results:
            raise RuntimeError("TableProfiler and ColumnProfiler must be run before DatatypeIdentifierL1.")

        column_profiles: dict[str, ColumnProfileOutput] = dataset.results['column_profiles']

        column_datatypes_l1 = dataset.dataframe_wrapper.datatype_identification_l1(dataset.raw_df, dataset.name, column_profiles)

        for column in column_datatypes_l1:
            column_profiles[column.column_name].datatype_l1 = column.datatype_l1

        dataset.results['column_datatypes_l1'] = column_datatypes_l1


class DataTypeIdentifierL2(AnalysisStep):
    def analyze(self, dataset: DataSet) -> None:
        """
        Performs datatype identification level 2 for each column.
        This step depends on the 'column_datatypes_l1' result.
        """
        
        # Dependency check
        if 'column_profiles' not in dataset.results:
            raise RuntimeError("TableProfiler and ColumnProfiler  must be run before DatatypeIdentifierL2.")

        column_profiles: dict[str, ColumnProfileOutput] = dataset.results['column_profiles']
        columns_with_samples = [DataTypeIdentificationL2Input(**col.model_dump()) for col in column_profiles.values()]
        column_datatypes_l2 = dataset.dataframe_wrapper.datatype_identification_l2(dataset.raw_df, dataset.name, columns_with_samples)

        for column in column_datatypes_l2:
            column_profiles[column.column_name].datatype_l2 = column.datatype_l2

        dataset.results['column_datatypes_l2'] = column_datatypes_l2

