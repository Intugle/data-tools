import json
import os
import uuid

from typing import Any, Dict, Optional, Self

import pandas as pd
import yaml

from intugle.adapters.factory import AdapterFactory
from intugle.adapters.models import (
    DataSetData,
    DataTypeIdentificationL1Output,
    DataTypeIdentificationL2Input,
    DataTypeIdentificationL2Output,
    KeyIdentificationOutput,
)
from intugle.common.exception import errors
from intugle.core import settings
from intugle.core.pipeline.business_glossary.bg import BusinessGlossary
from intugle.core.pipeline.datatype_identification.l2_model import L2Model
from intugle.core.pipeline.datatype_identification.pipeline import DataTypeIdentificationPipeline
from intugle.core.pipeline.key_identification.ki import KeyIdentificationLLM
from intugle.core.utilities.processing import string_standardization
from intugle.models.resources.model import Column, ColumnProfilingMetrics, ModelProfilingMetrics
from intugle.models.resources.source import Source, SourceTables


class DataSet:
    """
    A container for the dataframe and all its analysis results.
    This object is passed from one pipeline step to the next.
    """

    def __init__(self, data: DataSetData, name: str):
        # The original, raw dataframe object (e.g., a pandas DataFrame)
        self.id = uuid.uuid4()
        self.name = name
        self.data = data

        # The factory creates the correct wrapper for consistent API access
        self.adapter = AdapterFactory().create(data)

        # A dictionary to store the results of each analysis step
        self.source_table_model: SourceTables = SourceTables(name=name, description="")
        self._columns_map: Dict[str, Column] = {} # A convenience map for quick column lookup

        self.load()

    @property
    def sql_query(self):
        if "type" in self.data and self.data["type"] == "query":
            return self.data["path"]
        return None

    def load(self):
        try:
            self.adapter.load(self.data, self.name)
            print(f"{self.name} loaded")
        except Exception as e:
            print("eee", e)
            ...

    def profile_table(self) -> Self:
        """
        Profiles the table and stores the result in the 'results' dictionary.
        """
        table_profile = self.adapter.profile(self.data, self.name)
        if self.source_table_model.profiling_metrics is None:
            self.source_table_model.profiling_metrics = ModelProfilingMetrics()
        self.source_table_model.profiling_metrics.count = table_profile.count

        self.source_table_model.columns = [Column(name=col_name) for col_name in table_profile.columns]
        self._columns_map = {col.name: col for col in self.source_table_model.columns}
        return self

    def profile_columns(self) -> Self:
        """
        Profiles each column in the dataset and stores the results in the 'results' dictionary.
        This method relies on the 'table_profile' result to get the list of columns.
        """
        if not self.source_table_model.columns:
            raise RuntimeError("TableProfiler must be run before profiling columns.")

        count = self.source_table_model.profiling_metrics.count

        for column in self.source_table_model.columns:
            column_profile = self.adapter.column_profile(
                self.data, self.name, column.name, count, settings.UPSTREAM_SAMPLE_LIMIT
            )
            if column_profile:
                if column.profiling_metrics is None:
                    column.profiling_metrics = ColumnProfilingMetrics()

                column.profiling_metrics.count = column_profile.count
                column.profiling_metrics.null_count = column_profile.null_count
                column.profiling_metrics.distinct_count = column_profile.distinct_count
                column.profiling_metrics.sample_data = column_profile.sample_data
                column.profiling_metrics.dtype_sample = column_profile.dtype_sample
        return self

    def identify_datatypes_l1(self) -> "DataSet":
        """
        Identifies the data types at Level 1 for each column based on the column profiles.
        This method relies on the 'column_profiles' result.
        """
        if not self.source_table_model.columns or any(
            c.profiling_metrics is None for c in self.source_table_model.columns
        ):
            raise RuntimeError("TableProfiler and ColumnProfiler must be run before data type identification.")

        records = []
        for column in self.source_table_model.columns:
            records.append(
                {"table_name": self.name, "column_name": column.name, "values": column.profiling_metrics.dtype_sample}
            )

        l1_df = pd.DataFrame(records)
        di_pipeline = DataTypeIdentificationPipeline()
        l1_result = di_pipeline(sample_values_df=l1_df)

        column_datatypes_l1 = [DataTypeIdentificationL1Output(**row) for row in l1_result.to_dict(orient="records")]

        for col_l1 in column_datatypes_l1:
            self._columns_map[col_l1.column_name].type = col_l1.datatype_l1
        return self

    def identify_datatypes_l2(self) -> "DataSet":
        """
        Identifies the data types at Level 2 for each column based on the column profiles.
        This method relies on the 'column_profiles' result.
        """
        if not self.source_table_model.columns or any(c.type is None for c in self.source_table_model.columns):
            raise RuntimeError("TableProfiler and ColumnProfiler must be run before data type identification.")

        columns_with_samples = []
        for column in self.source_table_model.columns:
            columns_with_samples.append(
                DataTypeIdentificationL2Input(
                    column_name=column.name,
                    table_name=self.name,
                    sample_data=column.profiling_metrics.sample_data,
                    datatype_l1=column.type,
                )
            )

        column_values_df = pd.DataFrame([item.model_dump() for item in columns_with_samples])
        l2_model = L2Model()
        l2_result = l2_model(l1_pred=column_values_df)
        column_datatypes_l2 = [DataTypeIdentificationL2Output(**row) for row in l2_result.to_dict(orient="records")]

        for col_l2 in column_datatypes_l2:
            self._columns_map[col_l2.column_name].category = col_l2.datatype_l2
        return self

    def identify_keys(self) -> Self:
        """
        Identifies potential primary keys in the dataset based on column profiles.
        This method relies on the 'column_profiles' result.
        """
        if not self.source_table_model.columns or any(
            c.type is None or c.category is None for c in self.source_table_model.columns
        ):
            raise RuntimeError("DataTypeIdentifierL1 and L2 must be run before KeyIdentifier.")

        column_profiles_data = []
        for column in self.source_table_model.columns:
            metrics = column.profiling_metrics
            count = metrics.count if metrics.count is not None else 0
            null_count = metrics.null_count if metrics.null_count is not None else 0
            distinct_count = metrics.distinct_count if metrics.distinct_count is not None else 0
            column_profiles_data.append(
                {
                    "column_name": column.name,
                    "table_name": self.name,
                    "datatype_l1": column.type,
                    "datatype_l2": column.category,
                    "count": count,
                    "null_count": null_count,
                    "distinct_count": distinct_count,
                    "uniqueness": distinct_count / count if count > 0 else 0.0,
                    "completeness": (count - null_count) / count if count > 0 else 0.0,
                    "sample_data": metrics.sample_data,
                }
            )
        column_profiles_df = pd.DataFrame(column_profiles_data)

        ki_model = KeyIdentificationLLM(profiling_data=column_profiles_df)
        ki_result = ki_model()
        output = KeyIdentificationOutput(**ki_result)
        self.source_table_model.key = output.column_name
        return self

    def profile(self) -> Self:
        """
        Profiles the dataset including table and columns and stores the result in the 'results' dictionary.
        This is a convenience method to run profiling on the raw dataframe.
        """
        self.profile_table().profile_columns()
        return self

    def identify_datatypes(self) -> Self:
        """
        Identifies the data types for the dataset and stores the result in the 'results' dictionary.
        This is a convenience method to run data type identification on the raw dataframe.
        """
        self.identify_datatypes_l1().identify_datatypes_l2()
        return self

    def generate_glossary(self, domain: str = "") -> Self:
        """
        Generates a business glossary for the dataset and stores the result in the 'results' dictionary.
        This method relies on the 'column_datatypes_l1' results.
        """
        if not self.source_table_model.columns or any(c.type is None for c in self.source_table_model.columns):
            raise RuntimeError("DataTypeIdentifierL1  must be run before Business Glossary Generation.")

        column_profiles_data = []
        for column in self.source_table_model.columns:
            metrics = column.profiling_metrics
            count = metrics.count if metrics.count is not None else 0
            null_count = metrics.null_count if metrics.null_count is not None else 0
            distinct_count = metrics.distinct_count if metrics.distinct_count is not None else 0
            column_profiles_data.append(
                {
                    "column_name": column.name,
                    "table_name": self.name,
                    "datatype_l1": column.type,
                    "datatype_l2": column.category,
                    "count": count,
                    "null_count": null_count,
                    "distinct_count": distinct_count,
                    "uniqueness": distinct_count / count if count > 0 else 0.0,
                    "completeness": (count - null_count) / count if count > 0 else 0.0,
                    "sample_data": metrics.sample_data,
                }
            )
        column_profiles_df = pd.DataFrame(column_profiles_data)

        bg_model = BusinessGlossary(profiling_data=column_profiles_df)
        table_glossary, glossary_df = bg_model(table_name=self.name, domain=domain)

        self.source_table_model.description = table_glossary

        for _, row in glossary_df.iterrows():
            column = self._columns_map[row["column_name"]]
            column.description = row.get("business_glossary", "")
            column.tags = row.get("business_tags", [])
        return self

    def run(self, domain: str, save: bool = True) -> Self:
        """Run all stages"""

        self.profile().identify_datatypes().identify_keys().generate_glossary(domain=domain)

        if save:
            self.save_yaml()

        return self

    def save_yaml(self, file_path: Optional[str] = None) -> None:
        if file_path is None:
            file_path = f"{self.name}.yml"
        file_path = os.path.join(settings.PROJECT_BASE, file_path)

        details = self.adapter.get_details(self.data)
        self.source_table_model.details = details

        source = Source(
            name="healthcare",
            description=self.source_table_model.description,
            schema="public",
            database="",
            table=self.source_table_model,
        )

        sources = {"sources": [json.loads(source.model_dump_json())]}

        # Save the YAML representation of the sources
        with open(file_path, "w") as file:
            yaml.dump(sources, file, sort_keys=False, default_flow_style=False)

    def to_df(self):
        return self.adapter.to_df(self.data, self.name)

    def load_from_yaml(self, file_path: str) -> None:
        with open(file_path, "r") as file:
            data = yaml.safe_load(file)

        source = data.get("sources", [])[0]
        table = source.get("table", {})

        self.source_table_model = SourceTables.model_validate(table)
        self._columns_map = {col.name: col for col in self.source_table_model.columns}

    @property
    def profiling_df(self):
        if not self.source_table_model.columns:
            return "<p>No column profiles available.</p>"

        column_profiles_data = []
        for column in self.source_table_model.columns:
            metrics = column.profiling_metrics
            if metrics:
                count = metrics.count if metrics.count is not None else 0
                null_count = metrics.null_count if metrics.null_count is not None else 0
                distinct_count = metrics.distinct_count if metrics.distinct_count is not None else 0

                column_profiles_data.append(
                    {
                        "column_name": column.name,
                        "business_name": string_standardization(column.name),
                        "table_name": self.name,
                        "business_glossary": column.description,
                        "datatype_l1": column.type,
                        "datatype_l2": column.category,
                        "business_tags": column.tags,
                        "count": count,
                        "null_count": null_count,
                        "distinct_count": distinct_count,
                        "uniqueness": distinct_count / count if count > 0 else 0.0,
                        "completeness": (count - null_count) / count if count > 0 else 0.0,
                        "sample_data": metrics.sample_data,
                    }
                )
        df = pd.DataFrame(column_profiles_data)
        return df

    def _repr_html_(self):
        df = self.profiling_df.head()
        return df._repr_html_()
