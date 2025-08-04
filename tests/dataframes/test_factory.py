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

    # Before profiling, the attributes should be None
    assert dataframe.count is None
    assert dataframe.columns is None
    assert dataframe.dtypes is None

    profile = dataframe.profile()

    # After profiling, the attributes should be set
    assert dataframe.count == 2
    assert dataframe.columns == ["col1", "col2"]
    assert dataframe.dtypes == {"col1": "integer", "col2": "integer"}

    # The returned profile object should also have the correct data
    assert profile.count == 2
    assert profile.columns == ["col1", "col2"]
    assert profile.dtypes == {"col1": "integer", "col2": "integer"}