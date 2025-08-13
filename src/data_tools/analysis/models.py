import json
import os
import uuid

from typing import Any, Dict, Optional

import yaml

from data_tools.common.exception import errors
from data_tools.core import settings
from data_tools.dataframes.factory import DataFrameFactory
from data_tools.dataframes.models import ColumnProfile
from data_tools.models.resources.model import Column, ColumnProfilingMetrics
from data_tools.models.resources.source import Source, SourceTables


class DataSet:
    """
    A container for the dataframe and all its analysis results.
    This object is passed from one pipeline step to the next.
    """

    def __init__(self, df: Any, name: str):
        # The original, raw dataframe object (e.g., a pandas DataFrame)
        self.id = uuid.uuid4()
        self.name = name
        self.raw_df = df

        # The factory creates the correct wrapper for consistent API access
        self.dataframe_wrapper = DataFrameFactory().create(df)

        # A dictionary to store the results of each analysis step
        self.results: Dict[str, Any] = {}
    
    # FIXME - this is a temporary solution to save the results of the analysis
    # need to use model while executing the pipeline
    def save_yaml(self, file_path: Optional[str] = None) -> None:
        if file_path is None:
            file_path = f"{self.name}.yml"
        file_path = os.path.join(settings.PROJECT_BASE, file_path)

        column_profiles = self.results.get("column_profiles")

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

        table = SourceTables(name=self.name, description=table_description, columns=columns)

        source = Source(name="healthcare", description=table_description, schema="public", database="", table=table)

        sources = {"sources": [json.loads(source.model_dump_json())]}

        # Save the YAML representation of the sources
        with open(file_path, "w") as file:
            yaml.dump(sources, file, sort_keys=False, default_flow_style=False)
