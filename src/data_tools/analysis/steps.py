from abc import ABC, abstractmethod

from .models import DataSet


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
        dataset.profile_table()


class ColumnProfiler(AnalysisStep):
    def analyze(self, dataset: DataSet) -> None:
        """
        Performs column-level profiling for each column.
        This step depends on the 'table_profile' result.
        """
        dataset.profile_columns()


class DataTypeIdentifierL1(AnalysisStep):
    def analyze(self, dataset: DataSet) -> None:
        """
        Performs datatype identification level 1 for each column.
        This step depends on the 'column_profiles' result.
        """
        dataset.identify_datatypes_l1()


class DataTypeIdentifierL2(AnalysisStep):
    def analyze(self, dataset: DataSet) -> None:
        """
        Performs datatype identification level 2 for each column.
        This step depends on the 'column_datatypes_l1' result.
        """
        dataset.identify_datatypes_l2()


class KeyIdentifier(AnalysisStep):
    def analyze(self, dataset: DataSet) -> None:
        """
        Performs key identification for the dataset.
        This step depends on the datatype identification results.
        """
        dataset.identify_keys()


class BusinessGlossaryGenerator(AnalysisStep):
    def __init__(self, domain: str):
        """
        Initializes the BusinessGlossaryGenerator with optional additional context.
        :param domain: The industry domain to which the dataset belongs.
        """
        self.domain = domain

    def analyze(self, dataset: DataSet) -> None:
        """
        Generates business glossary terms and tags for each column in the dataset.
        """
        dataset.generate_glossary(self.domain)
