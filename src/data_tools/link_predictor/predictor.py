import itertools

from typing import Any, Dict, List

from data_tools.analysis.models import DataSet
from data_tools.analysis.pipeline import Pipeline
from data_tools.analysis.steps import (
    ColumnProfiler,
    DataTypeIdentifierL1,
    DataTypeIdentifierL2,
    KeyIdentifier,
    TableProfiler,
)

from .models import LinkPredictionResult, PredictedLink


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

    def _predict_for_pair(self, name_a: str, ds_a: DataSet, name_b: str, ds_b: DataSet) -> List[PredictedLink]:
        """
        Contains the core logic for finding links between TWO dataframes.
        This method can now safely assume that key identification has been run.
        """
        ds_a.results.get("key")
        ds_b.results.get("key")

        # =================================================================
        # TODO: USER IMPLEMENTATION
        # Your logic here can now use the identified keys.
        # e.g., if key_a.column_name == key_b.column_name:
        #           return [PredictedLink(...)]
        # =================================================================

        pair_links: List[PredictedLink] = []
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
            ds_a = self.datasets[name_a]
            ds_b = self.datasets[name_b]

            links_for_pair = self._predict_for_pair(name_a, ds_a, name_b, ds_b)

            if links_for_pair:
                print(f"Found {len(links_for_pair)} potential link(s).")
                all_links.extend(links_for_pair)
            else:
                print("No links found for this pair.")

        return LinkPredictionResult(links=all_links)