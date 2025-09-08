from intugle.adapters.types.duckdb.models import DuckdbConfig
from intugle.analysis.models import DataSet


def test_profile():
    """
    Tests the profile analysis step.
    """
    # 1. Prepare dummy data
    data = DuckdbConfig.model_validate({
        "path": "https://raw.githubusercontent.com/Intugle/data-tools/refs/heads/main/sample_data/healthcare/allergies.csv",  # noqa: E501
        "type": "csv"
    })
    table_name = "allergies"

    # 2. Initialize DataSet
    dataset = DataSet(data, name=table_name)

    # 3. Run profiling
    dataset.profile_table()
    dataset.profile_columns()

