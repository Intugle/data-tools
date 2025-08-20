from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import pandas as pd

from data_tools.core.settings import settings
from data_tools.dataframes.models import DataTypeIdentificationL2Input

from .models import DataSet

if TYPE_CHECKING:
    from data_tools.dataframes.models import ColumnProfile, ProfilingOutput


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
        if "table_profile" not in dataset.results:
            raise RuntimeError("TableProfiler must be run before ColumnProfiler.")

        table_profile: ProfilingOutput = dataset.results["table_profile"]
        all_column_profiles = {}

        for col_name in table_profile.columns:
            # We would add a method to our DataFrame wrapper to get stats for a single column
            stats = dataset.dataframe_wrapper.column_profile(
                dataset.raw_df, dataset.name, col_name, settings.UPSTREAM_SAMPLE_LIMIT
            )
            all_column_profiles[col_name] = stats

        dataset.results["column_profiles"] = all_column_profiles


class DataTypeIdentifierL1(AnalysisStep):
    def analyze(self, dataset: DataSet) -> None:
        """
        Performs datatype identification level 1 for each column.
        This step depends on the 'column_profiles' result.
        """

        # Dependency check
        if "column_profiles" not in dataset.results:
            raise RuntimeError("TableProfiler and ColumnProfiler must be run before DatatypeIdentifierL1.")

        column_profiles: dict[str, ColumnProfile] = dataset.results["column_profiles"]

        column_datatypes_l1 = dataset.dataframe_wrapper.datatype_identification_l1(
            dataset.raw_df, dataset.name, column_profiles
        )

        for column in column_datatypes_l1:
            column_profiles[column.column_name].datatype_l1 = column.datatype_l1

        dataset.results["column_datatypes_l1"] = column_datatypes_l1


class DataTypeIdentifierL2(AnalysisStep):
    def analyze(self, dataset: DataSet) -> None:
        """
        Performs datatype identification level 2 for each column.
        This step depends on the 'column_datatypes_l1' result.
        """

        # Dependency check
        if "column_profiles" not in dataset.results:
            raise RuntimeError("TableProfiler and ColumnProfiler  must be run before DatatypeIdentifierL2.")

        column_profiles: dict[str, ColumnProfile] = dataset.results["column_profiles"]
        columns_with_samples = [DataTypeIdentificationL2Input(**col.model_dump()) for col in column_profiles.values()]
        column_datatypes_l2 = dataset.dataframe_wrapper.datatype_identification_l2(
            dataset.raw_df, dataset.name, columns_with_samples
        )

        for column in column_datatypes_l2:
            column_profiles[column.column_name].datatype_l2 = column.datatype_l2

        dataset.results["column_datatypes_l2"] = column_datatypes_l2


class KeyIdentifier(AnalysisStep):
    def analyze(self, dataset: DataSet) -> None:
        """
        Performs key identification for the dataset.
        This step depends on the datatype identification results.
        """
        if "column_datatypes_l1" not in dataset.results or "column_datatypes_l2" not in dataset.results:
            raise RuntimeError("DataTypeIdentifierL1 and L2 must be run before KeyIdentifier.")

        column_profiles: dict[str, ColumnProfile] = dataset.results["column_profiles"]
        column_profiles_df = pd.DataFrame([col.model_dump() for col in column_profiles.values()])

        key = dataset.dataframe_wrapper.key_identification(dataset.name, column_profiles_df)
        if key is not None:
            dataset.results["key"] = key


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
        if "column_datatypes_l1" not in dataset.results:
            raise RuntimeError("DataTypeIdentifierL1  must be run before Business Glossary Generation.")

        column_profiles: dict[str, ColumnProfile] = dataset.results["column_profiles"]
        column_profiles_df = pd.DataFrame([col.model_dump() for col in column_profiles.values()])

        glossary_output = dataset.dataframe_wrapper.generate_business_glossary(
            dataset.name, column_profiles_df, domain=self.domain
        )

        for column in glossary_output.columns:
            column_profiles[column.column_name].business_glossary = column.business_glossary
            column_profiles[column.column_name].business_tags = column.business_tags

        dataset.results["business_glossary_and_tags"] = glossary_output
        dataset.results["table_glossary"] = glossary_output.table_glossary
