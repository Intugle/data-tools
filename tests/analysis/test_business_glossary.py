import pandas as pd

from intugle.analysis.models import DataSet
from intugle.analysis.pipeline import Pipeline
from intugle.analysis.steps import (
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

    # 2. Run the pipeline
    dataset = pipeline.run(df, table_name)

    # 3. Assert the results
    assert dataset.source_table_model.description is not None
    assert len(dataset.source_table_model.description) > 0
    assert len(dataset.source_table_model.columns) == len(df.columns)

    # Check a specific column's glossary entry
    product_id_column = dataset.columns.get("product_id")
    assert product_id_column is not None
    assert product_id_column.description is not None
    assert len(product_id_column.description) > 0
    assert product_id_column.tags is not None
    assert len(product_id_column.tags) > 0
    dataset.save_yaml()
