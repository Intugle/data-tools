import itertools
import json
import logging
import os

from typing import Any, Dict, List

import pandas as pd
import yaml

from intugle.analysis.models import DataSet
from intugle.analysis.pipeline import Pipeline
from intugle.analysis.steps import (
    ColumnProfiler,
    DataTypeIdentifierL1,
    DataTypeIdentifierL2,
    KeyIdentifier,
    TableProfiler,
)
from intugle.core import settings
from intugle.core.console import console, warning_style
from intugle.core.pipeline.link_prediction.lp import LinkPredictionAgentic
from intugle.libs.smart_query_generator.utils.join import Join
from intugle.models.resources.relationship import (
    Relationship,
    RelationshipTable,
    RelationshipType,
)

from .models import LinkPredictionResult, PredictedLink

log = logging.getLogger(__name__)


class NoLinksFoundError(Exception):
    """Custom exception raised when no links are found to save."""
    pass


class LinkPredictor:
    """
    Analyzes a collection of datasets to predict column links between all
    possible pairs, ensuring that key identification has been performed on
    each dataset first.
    """

    def __init__(self, data_input: Dict[str, Any] | List[DataSet]):
        """
        Initializes the LinkPredictor with either a dictionary of raw dataframes
        or a list of pre-initialized DataSet objects.

        Args:
            data_input: Either a dictionary of {name: dataframe} or a list
                        of DataSet objects.
        """
        self.datasets: Dict[str, DataSet] = {}
        self._prerequisite_pipeline = Pipeline([
            TableProfiler(),
            ColumnProfiler(),
            DataTypeIdentifierL1(),
            DataTypeIdentifierL2(),
            KeyIdentifier(),
        ])
        self.links: list[PredictedLink] = []

        if isinstance(data_input, dict):
            self._initialize_from_dict(data_input)
        elif isinstance(data_input, list):
            self._initialize_from_list(data_input)
        else:
            raise TypeError("Input must be a dictionary of named dataframes or a list of DataSet objects.")

        if len(self.datasets) < 2:
            raise ValueError("LinkPredictor requires at least two datasets to compare.")

        print(f"LinkPredictor initialized with datasets: {list(self.datasets.keys())}")

        self.already_executed_combo = set()

    def _run_prerequisites(self, dataset: DataSet):
        """Runs the prerequisite analysis steps on a given DataSet."""
        for step in self._prerequisite_pipeline.steps:
            step.analyze(dataset)

    def _initialize_from_dict(self, data_dict: Dict[str, Any]):
        """Creates and processes DataSet objects from a dictionary of raw dataframes."""
        for name, df in data_dict.items():
            dataset = DataSet(df, name=name)
            print(f"Running prerequisite analysis for new dataset: '{name}'...")
            self._run_prerequisites(dataset)
            self.datasets[name] = dataset

    def _initialize_from_list(self, data_list: List[DataSet]):
        """Processes a list of existing DataSet objects, running analysis if needed."""
        for dataset in data_list:
            if not dataset.name:
                raise ValueError("DataSet objects provided in a list must have a 'name' attribute.")
            if dataset.source_table_model.key is None:
                print(f"Dataset '{dataset.name}' is missing key identification. Running prerequisite analysis...")
                self._run_prerequisites(dataset)
            else:
                print(f"Dataset '{dataset.name}' already processed. Skipping analysis.")
            self.datasets[dataset.name] = dataset

    def _create_table_combination_id(self, table_a: str, table_b: str) -> str:
        assets = [table_a, table_b]
        assets.sort()
        return f"{assets[0]}--{assets[1]}"

    def _predict_for_pair(
        self,
        name_a: str,
        dataset_a: DataSet,
        name_b: str,
        dataset_b: DataSet,
    ) -> List[PredictedLink]:
        """
        Contains the core logic for finding links between TWO dataframes.
        This method can now safely assume that key identification has been run.
        """
        table_combination = self._create_table_combination_id(name_a, name_b)
        if table_combination in self.already_executed_combo:
            log.warning(f"[!] Skipping already executed combination: {table_combination}")
            return []

        dataset_a_column_profiles = dataset_a.profiling_df
        dataset_b_column_profiles = dataset_b.profiling_df
        profiling_data = pd.concat(
            [dataset_a_column_profiles, dataset_b_column_profiles], ignore_index=True
        )

        primary_keys = []
        if dataset_a.source_table_model.key:
            primary_keys.append((name_a, dataset_a.source_table_model.key))
        if dataset_b.source_table_model.key:
            primary_keys.append((name_b, dataset_b.source_table_model.key))

        pipeline = LinkPredictionAgentic(
            profiling_data=profiling_data,
            primary_keys=primary_keys,
        )

        llm_result, raw_llm_result = pipeline([(dataset_a, dataset_b)])

        pair_links: List[PredictedLink] = [
            PredictedLink(
                from_dataset=row["table1_name"],
                from_column=row["column1_name"],
                to_dataset=row["table2_name"],
                to_column=row["column2_name"],
                intersect_count=row.get("intersect_count"),
                intersect_ratio_from_col=row.get("intersect_ratio_from_col"),
                intersect_ratio_to_col=row.get("intersect_ratio_to_col"),
                accuracy=row.get("accuracy"),
            )
            for _, row in llm_result.iterrows()
        ]
        return pair_links

    def predict(self, filename='__relationships__.yml', save: bool = False, force_recreate: bool = False) -> 'LinkPredictor':
        """
        Iterates through all unique pairs of datasets, predicts the links for
        each pair, and returns the aggregated results.
        """
        relationships_file = os.path.join(settings.PROJECT_BASE, filename)

        if not force_recreate and os.path.exists(relationships_file):
            is_stale = False
            relationships_mtime = os.path.getmtime(relationships_file)
            for dataset in self.datasets.values():
                dataset_yml = os.path.join(settings.PROJECT_BASE, f"{dataset.name}.yml")
                if os.path.exists(dataset_yml) and os.path.getmtime(dataset_yml) > relationships_mtime:
                    is_stale = True
                    break
            
            if not is_stale:
                console.print("Link predictions are up-to-date. Loading from cache.", style="green")
                self.load_from_yaml(relationships_file)
                return self

        all_links: List[PredictedLink] = []
        dataset_names = list(self.datasets.keys())

        for name_a, name_b in itertools.combinations(dataset_names, 2):
            print(f"\n--- Comparing '{name_a}' <=> '{name_b}' ---")
            dataset_a = self.datasets[name_a]
            dataset_b = self.datasets[name_b]

            links_for_pair = self._predict_for_pair(name_a, dataset_a, name_b, dataset_b)

            if links_for_pair:
                print(f"Found {len(links_for_pair)} potential link(s).")
                all_links.extend(links_for_pair)
            else:
                print("No links found for this pair.")

        self.links = all_links

        if len(self.links) == 0:
            console.print("No links found between any datasets.", style=warning_style)
            return self

        if save:
            self.save_yaml(file_path=filename)

        return self
    
    def get_links_df(self) -> pd.DataFrame:
        """Returns the predicted links as a pandas DataFrame."""
        if not self.links:
            return pd.DataFrame()
        return pd.DataFrame([link.model_dump() for link in self.links])
    
    def show_graph(self):
        links = [link.relationship.link for link in self.links]
        join = Join(links, [])
        assets = {dataset.name for dataset in self.datasets.values()}

        graph = join.generate_graph(list(assets), only_connected=False)

        join.plot_graph(graph)

    def save_yaml(self, file_path: str) -> None:
        file_path = os.path.join(settings.PROJECT_BASE, file_path)

        if len(self.links) == 0:
            raise NoLinksFoundError("No links found to save.")

        relationships = {"relationships": [json.loads(link.relationship.model_dump_json()) for link in self.links]}

        # Save the relationships to a YAML file
        with open(file_path, "w") as file:
            yaml.dump(relationships, file, sort_keys=False, default_flow_style=False)

    def load_from_yaml(self, file_path: str) -> None:
        """Loads link predictions from a YAML file."""
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
        
        relationships = data.get("relationships", [])
        loaded_links = []
        for rel in relationships:
            metrics = rel.get("profiling_metrics", {}) or {}
            link = PredictedLink(
                from_dataset=rel["source"]["table"],
                from_column=rel["source"]["column"],
                to_dataset=rel["target"]["table"],
                to_column=rel["target"]["column"],
                intersect_count=metrics.get("intersect_count"),
                intersect_ratio_from_col=metrics.get("intersect_ratio_from_col"),
                intersect_ratio_to_col=metrics.get("intersect_ratio_to_col"),
                accuracy=metrics.get("accuracy"),
            )
            loaded_links.append(link)
        self.links = loaded_links


class LinkPredictionSaver:
    @classmethod
    def save_yaml(cls, result: LinkPredictionResult, file_path: str) -> None:
        file_path = os.path.join(settings.PROJECT_BASE, file_path)

        links = result.links

        if len(links) == 0:
            raise ValueError("No links found to save.")

        relationships: list[Relationship] = []
        for link in links:
            source = RelationshipTable(table=link.from_dataset, column=link.from_column)
            target = RelationshipTable(table=link.to_dataset, column=link.to_column)
            relationship = Relationship(
                name=f"{link.from_dataset}-{link.to_dataset}",
                description="",
                source=source,
                target=target,
                type=RelationshipType.ONE_TO_MANY,
            )

            relationships.append(relationship)

        relationships = {"relationships": [json.loads(r.model_dump_json()) for r in relationships]}

        # Save the relationships to a YAML file
        with open(file_path, "w") as file:
            yaml.dump(relationships, file, sort_keys=False, default_flow_style=False)
