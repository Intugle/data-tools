import json
import os
import time
import uuid

from typing import Any, Dict, Optional, Self

import pandas as pd
import yaml

from intugle.adapters.factory import AdapterFactory
from intugle.adapters.models import (
    BusinessGlossaryOutput,
    ColumnGlossary,
    ColumnProfile,
    DataSetData,
    DataTypeIdentificationL1Output,
    DataTypeIdentificationL2Input,
    DataTypeIdentificationL2Output,
    KeyIdentificationOutput,
    ProfilingOutput,
)
from intugle.common.exception import errors
from intugle.core import settings
from intugle.core.pipeline.business_glossary.bg import BusinessGlossary
from intugle.core.pipeline.datatype_identification.l2_model import L2Model
from intugle.core.pipeline.datatype_identification.pipeline import DataTypeIdentificationPipeline
from intugle.core.pipeline.key_identification.ki import KeyIdentificationLLM
from intugle.core.utilities.processing import string_standardization
from intugle.models.resources.model import Column, ColumnProfilingMetrics
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
        self.results: Dict[str, Any] = {}

        self.load()

    @property
    def sql_query(self):
        if 'type' in self.data and self.data['type'] == 'query':
            return self.data['path']
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
        self.results["table_profile"] = self.adapter.profile(self.data, self.name)
        return self

    def profile_columns(self) -> Self:
        """
        Profiles each column in the dataset and stores the results in the 'results' dictionary.
        This method relies on the 'table_profile' result to get the list of columns.
        """
        if "table_profile" not in self.results:
            raise RuntimeError("TableProfiler must be run before profiling columns.")

        table_profile: ProfilingOutput = ProfilingOutput.model_validate(self.results["table_profile"])
        self.results["column_profiles"] = {
            col_name: self.adapter.column_profile(
                self.data, self.name, col_name, table_profile.count, settings.UPSTREAM_SAMPLE_LIMIT
            )
            for col_name in table_profile.columns
        }
        return self

    def identify_datatypes_l1(self) -> "DataSet":
        """
        Identifies the data types at Level 1 for each column based on the column profiles.
        This method relies on the 'column_profiles' result.
        """
        if "column_profiles" not in self.results:
            raise RuntimeError("TableProfiler and ColumnProfiler must be run before data type identification.")

        column_profiles: dict[str, ColumnProfile] = self.results["column_profiles"]
        records = []
        for column_name, stats in column_profiles.items():
            records.append({"table_name": self.name, "column_name": column_name, "values": stats.dtype_sample})

        l1_df = pd.DataFrame(records)
        di_pipeline = DataTypeIdentificationPipeline()
        l1_result = di_pipeline(sample_values_df=l1_df)

        column_datatypes_l1 = [DataTypeIdentificationL1Output(**row) for row in l1_result.to_dict(orient="records")]

        for column in column_datatypes_l1:
            column_profiles[column.column_name].datatype_l1 = column.datatype_l1

        self.results["column_datatypes_l1"] = column_datatypes_l1
        return self

    def identify_datatypes_l2(self) -> "DataSet":
        """
        Identifies the data types at Level 2 for each column based on the column profiles.
        This method relies on the 'column_profiles' result.
        """
        if "column_profiles" not in self.results:
            raise RuntimeError("TableProfiler and ColumnProfiler must be run before data type identification.")

        column_profiles: dict[str, ColumnProfile] = self.results["column_profiles"]
        columns_with_samples = [DataTypeIdentificationL2Input(**col.model_dump()) for col in column_profiles.values()]

        column_values_df = pd.DataFrame([item.model_dump() for item in columns_with_samples])
        l2_model = L2Model()
        l2_result = l2_model(l1_pred=column_values_df)
        column_datatypes_l2 = [DataTypeIdentificationL2Output(**row) for row in l2_result.to_dict(orient="records")]

        for column in column_datatypes_l2:
            column_profiles[column.column_name].datatype_l2 = column.datatype_l2

        self.results["column_datatypes_l2"] = column_datatypes_l2
        return self

    def identify_keys(self) -> Self:
        """
        Identifies potential primary keys in the dataset based on column profiles.
        This method relies on the 'column_profiles' result.
        """
        if "column_datatypes_l1" not in self.results or "column_datatypes_l2" not in self.results:
            raise RuntimeError("DataTypeIdentifierL1 and L2 must be run before KeyIdentifier.")

        column_profiles: dict[str, ColumnProfile] = self.results["column_profiles"]
        column_profiles_df = pd.DataFrame([col.model_dump() for col in column_profiles.values()])

        ki_model = KeyIdentificationLLM(profiling_data=column_profiles_df)
        ki_result = ki_model()
        output = KeyIdentificationOutput(**ki_result)
        key = output.column_name

        if key is not None:
            self.results["key"] = key
        else:
            self.results['key'] = None
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
        if "column_datatypes_l1" not in self.results:
            raise RuntimeError("DataTypeIdentifierL1  must be run before Business Glossary Generation.")

        column_profiles: dict[str, ColumnProfile] = self.results["column_profiles"]
        column_profiles_df = pd.DataFrame([col.model_dump() for col in column_profiles.values()])

        bg_model = BusinessGlossary(profiling_data=column_profiles_df)
        table_glossary, glossary_df = bg_model(table_name=self.name, domain=domain)
        columns_glossary = []
        for _, row in glossary_df.iterrows():
            columns_glossary.append(
                ColumnGlossary(
                    column_name=row["column_name"],
                    business_glossary=row.get("business_glossary", ""),
                    business_tags=row.get("business_tags", []),
                )
            )
        glossary_output = BusinessGlossaryOutput(
            table_name=self.name, table_glossary=table_glossary, columns=columns_glossary
        )

        for column in glossary_output.columns:
            column_profiles[column.column_name].business_glossary = column.business_glossary
            column_profiles[column.column_name].business_tags = column.business_tags

        self.results["business_glossary_and_tags"] = glossary_output
        self.results["table_glossary"] = glossary_output.table_glossary
        return self

    def run(self, domain: str, save: bool = True) -> Self:
        """Run all stages"""

        self.profile().identify_datatypes().identify_keys().generate_glossary(domain=domain)

        if save:
            self.save_yaml()

        return self

    # FIXME - this is a temporary solution to save the results of the analysis
    # need to use model while executing the pipeline
    def save_yaml(self, file_path: Optional[str] = None) -> None:
        if file_path is None:
            file_path = f"{self.name}.yml"
        file_path = os.path.join(settings.PROJECT_BASE, file_path)

        column_profiles = self.results.get("column_profiles")
        key = self.results.get("key")

        table_description = self.results.get("table_glossary")
        table_tags = self.results.get("business_glossary_and_tags")

        if column_profiles is None or table_description is None or table_tags is None:
            raise errors.NotFoundError(
                "Column profiles not found in the dataset results. Ensure profiling steps were executed."
            )

        columns: list[Column] = []

        for column_profile in column_profiles.values():
            column_profile = ColumnProfile.model_validate(column_profile)
            column = Column(
                name=column_profile.column_name,
                description=column_profile.business_glossary,
                type=column_profile.datatype_l1,
                category=column_profile.datatype_l2,
                tags=column_profile.business_tags,
                profiling_metrics=ColumnProfilingMetrics(
                    count=column_profile.count,
                    null_count=column_profile.null_count,
                    distinct_count=column_profile.distinct_count,
                    sample_data=column_profile.sample_data,
                ),
            )
            columns.append(column)

        details = self.adapter.get_details(self.data)

        table = SourceTables(name=self.name, description=table_description, columns=columns, details=details, key=key)

        source = Source(name="healthcare", description=table_description, schema="public", database="", table=table)

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

        self.results["table_glossary"] = table.get("description")

        columns = table.get("columns", [])
        column_profiles = {}
        for col in columns:
            profiling_metrics = col.get("profiling_metrics", {})
            count = profiling_metrics.get("count", 0)
            null_count = profiling_metrics.get("null_count", 0)
            distinct_count = profiling_metrics.get("distinct_count", 0)

            column_profiles[col["name"]] = ColumnProfile(
                column_name=col["name"],
                business_name=string_standardization(col["name"]),
                table_name=self.name,
                business_glossary=col.get("description"),
                datatype_l1=col.get("type"),
                datatype_l2=col.get("category"),
                business_tags=col.get("tags"),
                count=count,
                null_count=null_count,
                distinct_count=distinct_count,
                uniqueness=distinct_count / count if count > 0 else 0.0,
                completeness=(count - null_count) / count if count > 0 else 0.0,
                sample_data=profiling_metrics.get("sample_data"),
                ts=time.time(),
            )
        self.results["column_profiles"] = column_profiles

        self.results["business_glossary_and_tags"] = BusinessGlossaryOutput(
            table_name=self.name,
            table_glossary=self.results["table_glossary"],
            columns=[
                ColumnGlossary(
                    column_name=col.column_name,
                    business_glossary=col.business_glossary,
                    business_tags=col.business_tags,
                )
                for col in column_profiles.values()
            ],
        )

        self.results["key"] = table.get('key')
    
    def to_df(self):
        return self.adapter.to_df(self.data, self.name)

    @property
    def profiling_df(self):
        column_profiles = self.results.get("column_profiles")
        if column_profiles is None:
            return "<p>No column profiles available.</p>"
        df = pd.DataFrame([col.model_dump() for col in column_profiles.values()])
        return df

    def _repr_html_(self):
        df = self.profiling_df.head()
        return df._repr_html_()
