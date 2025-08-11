import itertools

from typing import Any, Dict, List

from data_tools.dataframes.dataframe import DataFrame
from data_tools.dataframes.factory import DataFrameFactory

from .models import LinkPredictionResult, PredictedLink


class LinkPredictor:
    """
    Analyzes a collection of named datasets to predict column links
    between all possible pairs.
    """
    def __init__(self, datasets: Dict[str, Any]):
        """
        Initializes the LinkPredictor with a dictionary of named dataframes.

        Args:
            datasets: A dictionary where keys are unique dataset names (str)
                      and values are the dataframe objects (e.g., pandas DataFrame).
        """
        factory = DataFrameFactory()
        self.datasets: Dict[str, DataFrame] = {
            name: factory.create(df) for name, df in datasets.items()
        }
        if len(self.datasets) < 2:
            raise ValueError("LinkPredictor requires at least two datasets to compare.")
        print(f"LinkPredictor initialized with datasets: {list(self.datasets.keys())}")

    def _predict_for_pair(self, name_a: str, ds_a: DataFrame, name_b: str, ds_b: DataFrame) -> List[PredictedLink]:
        """
        Contains the core logic for finding links between TWO dataframes.
        This is the method where you will add your custom implementation.
        """
        ds_a.profile()
        ds_b.profile()

        # =================================================================
        # TODO: USER IMPLEMENTATION
        #
        # Your custom logic to compare profile_a and profile_b goes here.
        # You would compare column names, dtypes, value distributions, etc.
        # =================================================================

        # This is a placeholder. Your logic will populate this list.
        pair_links: List[PredictedLink] = []
        
        # Example of what your logic might produce:
        # if 'id' in profile_a.columns and 'customer_id' in profile_b.columns:
        #     pair_links.append(
        #         PredictedLink(
        #             from_dataset=name_a, from_column='id',
        #             to_dataset=name_b, to_column='customer_id',
        #             confidence=0.95, notes="High name similarity"
        #         )
        #     )
        return pair_links

    def predict(self) -> LinkPredictionResult:
        """
        Iterates through all unique pairs of datasets, predicts the links for
        each pair, and returns the aggregated results.

        Returns:
            A LinkPredictionResult object containing all links found.
        """
        all_links: List[PredictedLink] = []
        dataset_names = list(self.datasets.keys())

        # Generate all unique pairs of dataset names to compare
        for name_a, name_b in itertools.combinations(dataset_names, 2):
            print(f"\n--- Comparing '{name_a}' <=> '{name_b}' ---")
            ds_a = self.datasets[name_a]
            ds_b = self.datasets[name_b]

            # Run the prediction logic for the current pair
            links_for_pair = self._predict_for_pair(name_a, ds_a, name_b, ds_b)

            if links_for_pair:
                print(f"Found {len(links_for_pair)} potential link(s).")
                all_links.extend(links_for_pair)
            else:
                print("No links found for this pair.")

        return LinkPredictionResult(links=all_links)
