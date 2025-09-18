---
sidebar_position: 3
title: DataSet
---

# DataSet

The `DataSet` class is the heart of the analysis pipeline. It acts as a powerful, in-memory container for a single data source, holding the raw data and all the rich metadata the `KnowledgeBuilder`'s workflow generates about it.

## Overview

Think of a `DataSet` as a "unit of work" that gets progressively enriched as it moves through the analysis stages. Its key responsibilities are:

1.  **Data Abstraction**: It provides a consistent way to interact with data, regardless of its source.
2.  **Metadata Storage**: It serves as the central object for storing all analysis results.
3.  **Intelligent Caching**: It automatically persists and loads its own state, making the entire process efficient and resilient.

## Key features

### Data abstraction

The `DataSet` uses a system of **Adapters** under the hood to connect to different data backends. When you initialize a `DataSet` with a file-based source, it uses the appropriate adapter to handle the specific implementation details.

Currently, the library supports `csv`, `parquet`, and `excel` files. More integrations are on the way. This design makes the system extensible to support new data sources.

### Centralized metadata

All analysis results for a data source are stored within the `dataset.source_table_model` attribute. This attribute is a structured Pydantic model that makes accessing metadata predictable and easy. For more convenient access to column-level data, the `DataSet` also provides a `columns` dictionary.

#### Metadata structure and access

The library organizes metadata using Pydantic models, but you can access it through the `DataSet`'s attributes.

-   **Table-Level Metadata**: Accessed via `dataset.source_table_model`.
    -   `.name: str`
    -   `.description: str`
    -   `.key: Optional[str]`
-   **Column-Level Metadata**: Accessed via the `dataset.columns` dictionary, where keys are column names.
    -   `[column_name].description: Optional[str]`
    -   `[column_name].type: Optional[str]` (for example, 'integer', 'date')
    -   `[column_name].category: Literal["dimension", "measure"]`
    -   `[column_name].tags: Optional[List[str]]`
    -   `[column_name].profiling_metrics: Optional[ColumnProfilingMetrics]`
-   **`ColumnProfilingMetrics`**: Detailed statistics for a column.
    -   `.count: Optional[int]`
    -   `.null_count: Optional[int]`
    -   `.distinct_count: Optional[int]`
    -   `.sample_data: Optional[List[Any]]`
    -   `.uniqueness: Optional[float]` (Read-only property)
    -   `.completeness: Optional[float]` (Read-only property)

#### Example of accessing metadata

```python
# Assuming 'kb' is a built KnowledgeBuilder instance
customers_dataset = kb.datasets['customers']

# Access table-level metadata
print(f"Table Name: {customers_dataset.source_table_model.name}")
print(f"Primary Key: {customers_dataset.source_table_model.key}")

# Access column-level metadata using the 'columns' dictionary
email_column = customers_dataset.columns['email']
print(f"Column Name: {email_column.name}")
print(f"Column Description: {email_column.description}")

# Access profiling metrics for that column
metrics = email_column.profiling_metrics
if metrics:
    print(f"Distinct Count: {metrics.distinct_count}")
    print(f"Uniqueness: {metrics.uniqueness}")
    print(f"Completeness: {metrics.completeness}")
```

### Automatic caching

The `DataSet` object avoids redundant work. When you initialize a `DataSet`, it automatically checks for a corresponding `.yml` file. If it finds one, it validates that the source data file hasn't changed since the last run. If the data is fresh, it loads the saved metadata, saving significant processing time.

### Analysis stage functions

You can run the analysis pipeline step-by-step for more granular control. Each of these methods includes a `save=True` option to persist the results of that specific stage.

:::caution Naming Convention
The `name` you assign to a `DataSet` is used as a key and file name throughout the system. To avoid errors, **dataset names cannot contain whitespaces**. Use underscores (`_`) instead.
:::

```python
from intugle.analysis.models import DataSet

# Initialize the dataset
data_source = {"path": "path/to/my_data.csv", "type": "csv"}
dataset = DataSet(data_source, name="my_data")

# Run each stage individually and save progress
print("Step 1: Profiling...")
dataset.profile(save=True)

print("Step 2: Identifying Datatypes...")
dataset.identify_datatypes(save=True)

print("Step 3: Identifying Keys...")
dataset.identify_keys(save=True)

print("Step 4: Generating Glossary...")
dataset.generate_glossary(domain="my_domain", save=True)
```

### Other useful methods and properties

#### `save_yaml()`

Manually trigger a save of the dataset's current state to its `.yml` file.

```python
dataset.save_yaml()
```

#### `reload_from_yaml()`

Force a reload from the YAML file, bypassing the staleness check. This can be useful if you manually edit the YAML and want to load your changes.

```python
file_path = "path/to/my_data.yml"
dataset.reload_from_yaml(file_path)
```

#### `profiling_df`

Access a Pandas DataFrame containing the complete profiling results for all columns in the dataset. This is useful for exploration and validation in a notebook environment.

```python
# Get a comprehensive DataFrame of all column profiles
profiles = dataset.profiling_df

# Display the first 5 rows
print(profiles.head())
```