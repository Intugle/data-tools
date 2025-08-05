from typing import Any, Dict

from data_tools.dataframes.factory import DataFrameFactory


class DataSet:
    """
    A container for the dataframe and all its analysis results.
    This object is passed from one pipeline step to the next.
    """

    def __init__(self, df: Any, name: str):
        # The original, raw dataframe object (e.g., a pandas DataFrame)
        self.name = name
        self.raw_df = df

        # The factory creates the correct wrapper for consistent API access
        self.dataframe_wrapper = DataFrameFactory().create(df)

        # A dictionary to store the results of each analysis step
        self.results: Dict[str, Any] = {}
