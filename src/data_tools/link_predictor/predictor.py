import itertools
import logging

from typing import Any, Dict, List

import pandas as pd

from data_tools.analysis.models import DataSet
from data_tools.analysis.pipeline import Pipeline
from data_tools.analysis.steps import (
    ColumnProfiler,
    DataTypeIdentifierL1,
    DataTypeIdentifierL2,
    KeyIdentifier,
    TableProfiler,
)
from data_tools.core.pipeline.link_prediction.lp import LinkPredictionAgentic

from .models import LinkPredictionResult, PredictedLink

log = logging.getLogger(__name__)


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
            dataset = DataSet(df=df, name=name)
            print(f"Running prerequisite analysis for new dataset: '{name}'...")
            self._run_prerequisites(dataset)
            self.datasets[name] = dataset

    def _initialize_from_list(self, data_list: List[DataSet]):
        """Processes a list of existing DataSet objects, running analysis if needed."""
        for dataset in data_list:
            if not dataset.name:
                raise ValueError("DataSet objects provided in a list must have a 'name' attribute.")
            if "key" not in dataset.results:
                print(f"Dataset '{dataset.name}' is missing key identification. Running prerequisite analysis...")
                self._run_prerequisites(dataset)
            else:
                print(f"Dataset '{dataset.name}' already processed. Skipping analysis.")
            self.datasets[dataset.name] = dataset

    def _create_table_combination_id(self, table_a: str, table_b: str) -> str:
        assets = [table_a, table_b]
        assets.sort()
        return f"{assets[0]}--{assets[1]}"

    def _predict_for_pair(self, name_a: str, dataset_a: DataSet, name_b: str, dataset_b: DataSet) -> List[PredictedLink]:
        """
        Contains the core logic for finding links between TWO dataframes.
        This method can now safely assume that key identification has been run.
        """
        table_combination = self._create_table_combination_id(name_a, name_b)
        if table_combination in self.already_executed_combo:
            log.warning(f"[!] Skipping already executed combination: {table_combination}")
            return
        
        dataset_a_column_profiles = [col.model_dump() for col in dataset_a.results['column_profiles'].values()]
        dataset_b_column_profiles = [col.model_dump() for col in dataset_b.results['column_profiles'].values()]
        profiling_data = pd.concat([pd.DataFrame(dataset_a_column_profiles), pd.DataFrame(dataset_b_column_profiles)], ignore_index=True)
        pipeline = LinkPredictionAgentic(
            profiling_data=profiling_data,
            primary_keys=[(name_a, dataset_a.results['key'].column_name), 
                            (name_b, dataset_b.results['key'].column_name)],
        )
        
        llm_result, raw_llm_result = pipeline([(dataset_a, dataset_b)])

        pair_links: List[PredictedLink] = [PredictedLink(
            from_dataset=row['table1_name'],
            from_column=row['column1_name'],
            to_dataset=row['table2_name'],
            to_column=row['column2_name'],
        ) for _, row in llm_result.iterrows()]
        return pair_links

    def predict(self) -> LinkPredictionResult:
        """
        Iterates through all unique pairs of datasets, predicts the links for
        each pair, and returns the aggregated results.
        """
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

        return LinkPredictionResult(links=all_links)