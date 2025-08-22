from data_tools.adapters.types.duckdb.models import DuckdbConfig
from data_tools.analysis.models import DataSet


def test_business_glossary_generator():
    """
    Tests the BusinessGlossaryGenerator analysis step.
    """
    # 1. Prepare dummy data
    data = DuckdbConfig.model_validate({
        "path": "/home/juhel-phanju/Documents/intugle/projects/data-tools/data-tools/sample_data/healthcare/allergies.csv",  # noqa: E501
        "type": "csv"
    })
    table_name = "allergies"

    # 2. Initialize DataSet
    dataset = DataSet(data, name=table_name)

    # 3. Run profiling
    dataset.profile_table()
    dataset.profile_columns()

