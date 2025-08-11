from typing import Any, List

from .models import DataSet
from .steps import AnalysisStep


class Pipeline:
    def __init__(self, steps: List[AnalysisStep]):
        self.steps = steps

    def run(self, df: Any, name: str) -> DataSet:
        """
        Executes all analysis steps in order and returns the final dataset.
        """
        dataset = DataSet(df, name)
        for step in self.steps:
            step.analyze(dataset)
        return dataset
