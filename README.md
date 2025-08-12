# Data Tools: Automated Data Understanding and Integration

Data Tools is a Python library designed to automate the complex process of understanding and connecting siloed datasets. In modern data environments, tables are often disconnected and poorly documented. This library tackles that challenge head-on by providing two primary capabilities:

1.  **Automated Link Prediction**: Its flagship feature, the `LinkPredictor`, analyzes multiple datasets, identifies primary keys, and automatically predicts relationships (foreign key links) between them.
2.  **In-Depth Data Profiling**: A flexible, multi-step analysis pipeline that creates a rich profile for each dataset, including data types, column statistics, and generating a business glossary.

By combining these features, Data Tools helps you move from a collection of separate tables to a fully documented and interconnected data model, ready for integration or analysis.

## Core Features

- **Automated Link Prediction**: Intelligently discovers potential foreign key relationships across multiple datasets.
- **In-Depth Data Profiling**: A multi-step pipeline that identifies keys, profiles columns, and determines data types.
- **Business Glossary Generation**: Automatically generates business-friendly descriptions and tags for columns and tables based on a provided domain.
- **Extensible Pipeline Architecture**: Easily add custom analysis steps to the pipeline.
- **DataFrame Agnostic**: Uses a factory pattern to seamlessly handle different dataframe types (e.g., pandas).

## Usage Examples

### Example 1: Automated Link Prediction (Primary Use Case)

This is the most direct way to use the library. Provide a dictionary of named dataframes, and the `LinkPredictor` will automatically run all prerequisite analysis steps and predict the links.

```python
import pandas as pd
from data_tools.link_predictor.predictor import LinkPredictor

# 1. Prepare your collection of dataframes
customers_df = pd.DataFrame({"id": [1, 2, 3], "name": ["A", "B", "C"]})
orders_df = pd.DataFrame({"order_id": [101, 102], "customer_id": [1, 3]})

datasets = {
    "customers": customers_df,
    "orders": orders_df
}

# 2. Initialize the predictor
# This automatically runs profiling, key identification, etc., for you.
link_predictor = LinkPredictor(datasets)

# 3. Predict the links
# (This example assumes you have implemented the logic in _predict_for_pair)
prediction_results = link_predictor.predict()

# 4. Review the results
print(prediction_results.model_dump_json(indent=2))
```

### Example 2: In-Depth Analysis with the Pipeline

If you want to perform a deep analysis on a single dataset, you can use the pipeline directly. This gives you fine-grained control over the analysis steps.

```python
import pandas as pd
from data_tools.analysis.pipeline import Pipeline
from data_tools.analysis.steps import (
    TableProfiler,
    KeyIdentifier,
    BusinessGlossaryGenerator
)

# 1. Define your analysis pipeline
pipeline = Pipeline([
    TableProfiler(),
    KeyIdentifier(),
    BusinessGlossaryGenerator(domain="e-commerce") # Provide context for the glossary
])

# 2. Prepare your dataframe
products_df = pd.DataFrame({
    "product_id": [10, 20, 30],
    "name": ["Laptop", "Mouse", "Keyboard"],
    "unit_price": [1200, 25, 75]
})

# 3. Run the pipeline
# The pipeline creates and returns a DataSet object
product_dataset = pipeline.run(df=products_df, name="products")

# 4. Access the rich analysis results
print(f"Identified Key: {product_dataset.results['key'].column_name}")
print("\n--- Table Glossary ---")
print(product_dataset.results['table_glossary'])
```

## Available Analysis Steps

You can construct a custom `Pipeline` using any combination of the following steps:

- `TableProfiler`: Gathers basic table-level statistics (row count, column names).
- `ColumnProfiler`: Runs detailed profiling for each column (null counts, distinct counts, samples).
- `DataTypeIdentifierL1` & `L2`: Determines the logical data type for each column through multiple levels of analysis.
- `KeyIdentifier`: Analyzes the profiled data to predict the primary key of the dataset.
- `BusinessGlossaryGenerator(domain: str)`: Generates business-friendly descriptions and tags for all columns and the table itself, using the provided `domain` for context.

## Running Tests

To run the test suite, first install the testing dependencies and then execute `pytest` via `uv`.

```bash
# Install testing library
uv pip install pytest

# Run tests
uv run pytest
```

## License

This project is licensed under the terms of the LICENSE file.
