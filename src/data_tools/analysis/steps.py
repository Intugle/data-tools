from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from .models import DataSet

if TYPE_CHECKING:
    from data_tools.dataframes.models import ProfilingOutput


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
            stats = dataset.dataframe_wrapper.column_profile(dataset.raw_df, dataset.name, col_name)
            all_column_profiles[col_name] = stats
            
        dataset.results['column_profiles'] = all_column_profiles
