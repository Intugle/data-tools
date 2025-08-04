
import pandas as pd

from data_tools.dataframes.factory import DataFrameFactory


def test_create_pandas_dataframe():
    """
    Tests that the DataFrameFactory can create a PandasDF instance
    and that the profile method returns the expected output.
    """
    factory = DataFrameFactory()

    data = {"col1": [1, 2], "col2": [3, 4]}
    df = pd.DataFrame(data=data)

    dataframe = factory.create(df)

    profile = dataframe.profile()

    assert profile.count == 2
    assert profile.columns == ["col1", "col2"]
    assert profile.dtypes == {"col1": "integer", "col2": "integer"}
