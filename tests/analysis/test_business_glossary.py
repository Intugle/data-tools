import pandas as pd
import pytest
from intugle.analysis.models import DataSet


@pytest.mark.skip(reason="Requires real LLM API key")
def test_business_glossary_generator():
    """
    Tests the business glossary generation convenience method on the DataSet.
    """
    # 1. Prepare dummy data
    df = pd.DataFrame({
        "product_id": [1, 2, 3],
        "product_name": ["Laptop", "Mouse", "Keyboard"],
        "price": [1200.00, 25.00, 75.00],
        "last_updated": pd.to_datetime(["2023-01-01", "2023-01-05", "2023-01-10"]),
    })
    table_name = "products"
    domain = "e-commerce"

    # 2. Run the analysis using DataSet convenience methods
    dataset = DataSet(df, table_name)
    dataset.profile()
    dataset.identify_datatypes()
    dataset.generate_glossary(domain=domain)

    # 3. Assert the results
    assert dataset.source.table.description is not None
    assert len(dataset.source.table.description) > 0
    assert len(dataset.source.table.columns) == len(df.columns)

    # Check a specific column's glossary entry
    product_id_column = dataset.columns.get("product_id")
    assert product_id_column is not None
    assert product_id_column.description is not None
    assert len(product_id_column.description) > 0
