import pandas as pd

from data_tools.adapters.models import BusinessGlossaryOutput, ColumnGlossary
from data_tools.analysis.models import DataSet
from data_tools.analysis.pipeline import Pipeline
from data_tools.analysis.steps import (
    BusinessGlossaryGenerator,
    ColumnProfiler,
    DataTypeIdentifierL1,
    DataTypeIdentifierL2,
    TableProfiler,
)


def test_business_glossary_generator():
    """
    Tests the BusinessGlossaryGenerator analysis step.
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

    pipeline = Pipeline([
        TableProfiler(),
        ColumnProfiler(),
        DataTypeIdentifierL1(),
        DataTypeIdentifierL2(),
        BusinessGlossaryGenerator(domain=domain),
    ])

    # 2. Initialize DataSet
    dataset = DataSet(df, name=table_name)

    # 3. Run prerequisite steps (TableProfiler, ColumnProfiler)
    dataset = pipeline.run(df, table_name)

    # 4. Assert the results
    assert "business_glossary_and_tags" in dataset.results
    assert "table_glossary" in dataset.results

    glossary_output = dataset.results["business_glossary_and_tags"]
    table_glossary_str = dataset.results["table_glossary"]

    assert isinstance(glossary_output, BusinessGlossaryOutput)
    assert glossary_output.table_name == table_name
    assert isinstance(table_glossary_str, str)
    assert len(table_glossary_str) > 0
    assert len(glossary_output.columns) == len(df.columns)

    # Check a specific column's glossary entry
    product_id_glossary = next((col for col in glossary_output.columns if col.column_name == "product_id"), None)
    assert product_id_glossary is not None
    assert isinstance(product_id_glossary, ColumnGlossary)
    assert isinstance(product_id_glossary.business_glossary, str)
    assert len(product_id_glossary.business_glossary) > 0
    assert len(product_id_glossary.business_tags) > 0

    # Verify that column profiles were updated
    assert dataset.results["column_profiles"]["product_id"].business_glossary is not None
    assert len(dataset.results["column_profiles"]["product_id"].business_tags) > 0
    dataset.save_yaml()
