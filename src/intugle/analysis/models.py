import json
import logging
import os
import uuid

from typing import Dict, Optional

import pandas as pd
import yaml

from intugle.adapters.factory import AdapterFactory
from intugle.adapters.models import (
    DataSetData,
    DataTypeIdentificationL1Output,
    DataTypeIdentificationL2Input,
    DataTypeIdentificationL2Output,
)
from intugle.core import settings
from intugle.core.console import console, warning_style
from intugle.core.pipeline.business_glossary.bg import BusinessGlossary
from intugle.core.pipeline.datatype_identification.l2_model import L2Model
from intugle.core.pipeline.datatype_identification.pipeline import DataTypeIdentificationPipeline
from intugle.core.pipeline.key_identification.agent import KeyIdentificationAgent
from intugle.core.utilities.processing import string_standardization
from intugle.models.resources.model import Column, ColumnProfilingMetrics, ModelProfilingMetrics, PrimaryKey
from intugle.models.resources.source import Source, SourceTables

log = logging.getLogger(__name__)


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
        self._sql_query: Optional[str] = None

        # The factory creates the correct wrapper for consistent API access
        self.adapter = AdapterFactory().create(data)
        self.source: Source = Source(
            name=self.adapter.source_name or "",
            description="",
            schema=self.adapter.schema or "",
            database=self.adapter.database or "",
            table=SourceTables(name=name, description=""),
        )
        # A convenience map for quick column lookup
        self.columns: Dict[str, Column] = {}

        # Check if a YAML file exists and load it
        file_path = os.path.join(settings.MODELS_DIR, f"{self.name}.yml")
        if os.path.exists(file_path):
            print(f"Found existing YAML for '{self.name}'. Checking for staleness.")
            self.load_from_yaml(file_path)

        self.load()

    # It checks if Data isn't empty and displays the name and the data
    def __str__(self) -> str:
        """Human-Friendly summary"""
        data_str = str(self.data) if self.data is not None else "No Data"
        return (
            f"DataSet(name='{self.name}', "
            f"data={data_str})"
        )

    # Avoids errors if id isn't present
    def __repr__(self) -> str:
        """Developer-friendly"""
        return (
            f"DataSet(name={self.name!r},"
            f"id={getattr(self, 'id', None)!r}, "
            f"data={self.data!r})"
        )

    def _is_yaml_stale(self, yaml_data: dict) -> bool:
        """Determine whether a cached YAML file is stale compared to data sources.

    This method checks modification timestamps to decide whether the YAML cache
    should be considered out-of-date. YAML files are considered *stale* when
    any of the source files they were derived from (e.g., dataset files,
    configuration files, or model output files) have a modification time later
    than the YAML file's modification time.

    Parameters
    ----------
    yaml_path : str
        Filesystem path to the YAML cache file.
    source_paths : list[str]
        List of filesystem paths for the source files that contribute to the
        cached content (these are compared against `yaml_path`'s mtime).

    Returns
    -------
    bool
        `True` if the YAML file is stale (i.e., at least one source file is
        newer than the YAML file), otherwise `False`.

    Notes
    -----
    * If `yaml_path` does not exist, this method should return `True`.
    * This check uses filesystem modification times (mtime) and therefore can
      be sensitive to clock skew between filesystems or inadequate timestamp
      resolution on some platforms.

    Examples
    --------
    >>> _is_yaml_stale("/tmp/ds.yaml", ["/data/table1.csv"])
    True
    """
        if not isinstance(self.data, dict) or "path" not in self.data or not os.path.exists(self.data["path"]):
            # Not a file-based source, so we cannot check for staleness.
            return False

        try:
            source = yaml_data.get("sources", [])[0]
            table = source.get("table", {})
            source_last_modified = table.get("source_last_modified")

            if source_last_modified:
                current_mtime = os.path.getmtime(self.data["path"])
                if current_mtime > source_last_modified:
                    console.print(
                        f"Warning: Source file for '{self.name}' has been modified since the last analysis.",
                        style=warning_style,
                    )
                    return True
            return False
        except (IndexError, KeyError, TypeError):
            # If YAML is malformed, treat it as stale.
            console.print(f"Warning: Could not parse existing YAML for '{self.name}'. Treating as stale.", style=warning_style)
            return True

    def _populate_from_yaml(self, yaml_data: dict):
        """Populate the DataSet object from YAML cached data.

    Reads the YAML file at `yaml_path` and updates the DataSet instance's
    in-memory attributes (for example: profiles, classifications, relationships,
    metadata) with the values found in the YAML. This method is used to restore
    previously computed semantic model results so expensive recomputation can be
    avoided.

    Parameters
    ----------
    yaml_path : str
        Filesystem path to the YAML file to load.

    Side effects
    ------------
    * Mutates `self` by setting attributes corresponding to the YAML's contents.
    * May create or update internal caches used by subsequent DataSet methods.

    YAML format expectations
    ------------------------
    The method expects a mapping at the top level. Typical keys include:
    - 'profiles' : mapping of table/column profiling results
    - 'classifications' : classification metadata
    - 'relationships' : inferred link definitions
    - 'generated_at' : ISO-8601 timestamp of when the YAML was produced

    Implementations should validate the presence and shape of critical keys and
    raise a descriptive error if the YAML structure is not as expected.

    Examples
    --------
    >>> _populate_from_yaml("/tmp/ds.yaml")
    # After call, self.profiles and self.relationships are set from YAML.
    """
        source = yaml_data.get("sources", [])[0]
        self.source = Source.model_validate(source)
        self.columns = {col.name: col for col in self.source.table.columns}

    @property
    def sql_query(self):
        return self._sql_query

    @sql_query.setter
    def sql_query(self, value: str):
        self._sql_query = value

    def load(self):
        try:
            self.adapter.load(self.data, self.name)
            print(f"{self.name} loaded")
        except Exception as e:
            log.error(e)
            ...

    def profile_table(self) -> 'DataSet':
        """
        Profiles the table and stores the result in the 'results' dictionary.
        """
        table_profile = self.adapter.profile(self.data, self.name)
        if self.source.table.profiling_metrics is None:
            self.source.table.profiling_metrics = ModelProfilingMetrics()
        self.source.table.profiling_metrics.count = table_profile.count

        self.source.table.columns = [Column(name=col_name) for col_name in table_profile.columns]
        self.columns = {col.name: col for col in self.source.table.columns}
        return self

    def profile_columns(self) -> 'DataSet':
        """
        Profiles each column in the dataset and stores the results in the 'results' dictionary.
        This method relies on the 'table_profile' result to get the list of columns.
        """
        if not self.source.table.columns:
            raise RuntimeError("TableProfiler must be run before profiling columns.")

        count = self.source.table.profiling_metrics.count

        for column in self.source.table.columns:
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
        if not self.source.table.columns or any(
            c.profiling_metrics is None for c in self.source.table.columns
        ):
            raise RuntimeError("TableProfiler and ColumnProfiler must be run before data type identification.")

        records = []
        for column in self.source.table.columns:
            records.append(
                {"table_name": self.name, "column_name": column.name, "values": column.profiling_metrics.dtype_sample}
            )

        l1_df = pd.DataFrame(records)
        di_pipeline = DataTypeIdentificationPipeline()
        l1_result = di_pipeline(sample_values_df=l1_df)

        column_datatypes_l1 = [DataTypeIdentificationL1Output(**row) for row in l1_result.to_dict(orient="records")]

        for col_l1 in column_datatypes_l1:
            self.columns[col_l1.column_name].type = col_l1.datatype_l1
        return self

    def identify_datatypes_l2(self) -> "DataSet":
        """
        Identifies the data types at Level 2 for each column based on the column profiles.
        This method relies on the 'column_profiles' result.
        """
        if not self.source.table.columns or any(c.type is None for c in self.source.table.columns):
            raise RuntimeError("TableProfiler and ColumnProfiler must be run before data type identification.")

        columns_with_samples = []
        for column in self.source.table.columns:
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
            self.columns[col_l2.column_name].category = col_l2.datatype_l2
        return self

    def identify_keys(self, save: bool = False) -> 'DataSet':
        """
        Identifies potential primary keys in the dataset based on column profiles.
        This method relies on the 'column_profiles' result.
        """
        if not self.source.table.columns or any(
            c.type is None or c.category is None for c in self.source.table.columns
        ):
            raise RuntimeError("DataTypeIdentifierL1 and L2 must be run before KeyIdentifier.")

        column_profiles_data = []
        for column in self.source.table.columns:
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

        ki_agent = KeyIdentificationAgent(
            profiling_data=column_profiles_df, adapter=self.adapter, dataset_data=self.data
        )
        ki_result = ki_agent()

        if ki_result:
            self.source.table.key = PrimaryKey(**ki_result)

        if save:
            self.save_yaml()
        return self

    def profile(self, save: bool = False) -> 'DataSet':
        """
        Profiles the dataset including table and columns and stores the result in the 'results' dictionary.
        This is a convenience method to run profiling on the raw dataframe.
        """
        self.profile_table().profile_columns()
        if save:
            self.save_yaml()
        return self

    def identify_datatypes(self, save: bool = False) -> 'DataSet':
        """
        Identifies the data types for the dataset and stores the result in the 'results' dictionary.
        This is a convenience method to run data type identification on the raw dataframe.
        """
        self.identify_datatypes_l1().identify_datatypes_l2()
        if save:
            self.save_yaml()
        return self

    def generate_glossary(self, domain: str = "", save: bool = False) -> 'DataSet':
        """
        Generates a business glossary for the dataset and stores the result in the 'results' dictionary.
        This method relies on the 'column_datatypes_l1' results.
        """
        if not self.source.table.columns or any(c.type is None for c in self.source.table.columns):
            raise RuntimeError("DataTypeIdentifierL1  must be run before Business Glossary Generation.")

        column_profiles_data = []
        for column in self.source.table.columns:
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

        self.source.table.description = table_glossary

        for _, row in glossary_df.iterrows():
            column = self.columns[row["column_name"]]
            column.description = row.get("business_glossary", "")
            column.tags = row.get("business_tags", [])

        if save:
            self.save_yaml()
        return self

    def run(self, domain: str, save: bool = True) -> 'DataSet':
        """Run all stages"""

        self.profile().identify_datatypes().identify_keys().generate_glossary(domain=domain)

        if save:
            self.save_yaml()

        return self

    def save_yaml(self, file_path: Optional[str] = None) -> None:
        if file_path is None:
            file_path = f"{self.name}.yml"

        # Ensure the models directory exists
        os.makedirs(settings.MODELS_DIR, exist_ok=True)
        file_path = os.path.join(settings.MODELS_DIR, file_path)

        details = self.adapter.get_details(self.data)
        self.source.table.details = details

        # Store the source's last modification time
        if isinstance(self.data, dict) and "path" in self.data and os.path.exists(self.data["path"]):
            self.source.table.source_last_modified = os.path.getmtime(self.data["path"])

        sources = {"sources": [json.loads(self.source.model_dump_json())]}

        # Save the YAML representation of the sources
        with open(file_path, "w") as file:
            yaml.dump(sources, file, sort_keys=False, default_flow_style=False)

    def to_df(self):
        return self.adapter.to_df(self.data, self.name)

    def load_from_yaml(self, file_path: str) -> None:
        """Loads the dataset from a YAML file, checking for staleness."""
        with open(file_path, "r") as f:
            yaml_data = yaml.safe_load(f)
        if not self._is_yaml_stale(yaml_data):
            self._populate_from_yaml(yaml_data)

    def reload_from_yaml(self, file_path: Optional[str] = None) -> None:
        """Force a reload of dataset state from a YAML cache file.

    This method bypasses staleness checks (or enforces reloading depending on
    the `force` parameter) and ensures the DataSet instance is populated from
    the provided YAML file. It is useful for debugging, forcing a refresh when
    an external process updated the YAML, or when the caller explicitly wants
    to override the normal cache logic.

    Parameters
    ----------
    yaml_path : str
        Filesystem path to the YAML cache file to load.
    force : bool, optional
        When `True` (default), the method will load the YAML even if the file
        appears stale or out-of-sync with the internal state. When `False`, it
        behaves like a normal load operation (respecting staleness checks).

    Returns
    -------
    None

    Use cases
    ---------
    * Debugging: quickly load saved model state for inspection.
    * Forced refresh: apply a YAML created/edited outside the normal pipeline.
    * Recovering from a partial failure: rehydrate object state after crash.

    Examples
    --------
    >>> reload_from_yaml("/tmp/ds.yaml", force=True)
    # DataSet state is overwritten with YAML contents.
    """
        if file_path is None:
            file_path = f"{self.name}.yml"
        file_path = os.path.join(settings.MODELS_DIR, file_path)

        with open(file_path, "r") as f:
            yaml_data = yaml.safe_load(f)
        self._populate_from_yaml(yaml_data)

    @property
    def profiling_df(self):
        if not self.source.table.columns:
            return "<p>No column profiles available.</p>"

        column_profiles_data = []
        for column in self.source.table.columns:
            metrics = column.profiling_metrics
            if metrics:
                count = metrics.count if metrics.count is not None else 0
                null_count = metrics.null_count if metrics.null_count is not None else 0
                distinct_count = metrics.distinct_count if metrics.distinct_count is not None else 0

                column_profiles_data.append(
                    {
                        "column_name": column.name,
                        "table_name": self.name,
                        "business_name": string_standardization(column.name),
                        "datatype_l1": column.type,
                        "datatype_l2": column.category,
                        "business_glossary": column.description,
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
