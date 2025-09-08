from typing import TYPE_CHECKING, Any, Dict, List

from intugle.analysis.models import DataSet
from intugle.link_predictor.predictor import LinkPredictor

if TYPE_CHECKING:
    from intugle.link_predictor.models import PredictedLink


class KnowledgeBuilder:

    def __init__(self, data_input: Dict[str, Any] | List[DataSet], domain: str = ""):

        self.datasets: Dict[str, DataSet] = {}
        self.links: list[PredictedLink] = []
        self.domain = domain

        if isinstance(data_input, dict):
            self._initialize_from_dict(data_input)
        elif isinstance(data_input, list):
            self._initialize_from_list(data_input)
        else:
            raise TypeError("Input must be a dictionary of named dataframes or a list of DataSet objects.")
        
    def _initialize_from_dict(self, data_dict: Dict[str, Any]):
        """Creates and processes DataSet objects from a dictionary of raw dataframes."""
        for name, df in data_dict.items():
            dataset = DataSet(df, name=name)
            self.datasets[name] = dataset

    def _initialize_from_list(self, data_list: List[DataSet]):
        """Processes a list of existing DataSet objects"""
        for dataset in data_list:
            if not dataset.name:
                raise ValueError("DataSet objects provided in a list must have a 'name' attribute.")
            self.datasets[dataset.name] = dataset

    def build(self):

        # run analysis on all datasets
        for dataset in self.datasets.values():
            dataset.run(domain=self.domain, save=True)

        # Initialize the predictor
        self.link_predictor = LinkPredictor(list(self.datasets.values()))

        # Run the prediction
        self.link_predictor.predict(save=True)
        self.links: list[PredictedLink] = self.link_predictor.links
        return self
    
    def visualize(self):
        return self.link_predictor.show_graph()
        
