---
sidebar_position: 1
title: Semantic Model
---

# Semantic Model

The `SemanticModel` is the primary orchestrator of the data intelligence pipeline. It's the main user-facing class that manages many data sources and runs the end-to-end process of transforming them from raw, disconnected tables into a fully enriched and interconnected semantic layer.

## Overview

At a high level, the `SemanticModel` is responsible for:

1.  **Initializing and Managing Datasets**: It takes your raw data sources (for example, file paths) and wraps each one in a `DataSet` object.
2.  **Executing the Semantic Model Pipeline**: It runs a series of analysis stages in a specific, logical order to build up a rich understanding of your data.
3.  **Ensuring Resilience**: The pipeline avoids redundant work. It automatically saves its progress after each major stage, letting you resume an interrupted run without losing completed work.

## Initialization

You can initialize the `SemanticModel` in two ways:

1.  **With a Dictionary of File-Based Sources**: This is the most common method. You give a dictionary where keys are the desired names for your datasets and values are dictionary configurations pointing to your data. The `path` can be a local file path or a remote URL (e.g., over HTTPS). Currently, `csv`, `parquet`, and `excel` file formats are supported.

    ```python
    from intugle import SemanticModel

    data_sources = {
        "customers": {"path": "path/to/customers.csv", "type": "csv"},
        "orders": {"path": "https://example.com/orders.csv", "type": "csv"},
    }

    sm = SemanticModel(data_input=data_sources, domain="e-commerce")
    ```

2.  **With a List of `DataSet` Objects**: If you have already created `DataSet` objects, you can pass a list of them directly.

    ```python
    from intugle.analysis.models import DataSet
    from intugle import SemanticModel

    # Create DataSet objects from file-based sources
    customers_data = {"path": "path/to/customers.csv", "type": "csv"}
    orders_data = {"path": "path/to/orders.csv", "type": "csv"}
    
    dataset_one = DataSet(customers_data, name="customers")
    dataset_two = DataSet(orders_data, name="orders")

    datasets = [dataset_one, dataset_two]

    sm = SemanticModel(data_input=datasets, domain="e-commerce")
    ```

The `domain` parameter is an optional but highly recommended string that gives context to the underlying AI models, helping them generate more relevant business glossary terms.

:::caution Naming Convention
The `name` you assign to a `DataSet` is used as a key and file name throughout the system. To avoid errors, **dataset names cannot contain whitespaces**. Use underscores (`_`) instead.
:::

## The Semantic Model Pipeline

The `SemanticModel` executes its workflow in distinct, modular stages. This design enables greater control and makes the process resilient to interruptions.

### Profiling

This is the first and most foundational stage. It performs a deep analysis of each dataset to understand its structure and content, covering profiling, datatype identification, and key identification.

```python
# Run only the profiling and key identification stage
sm.profile()
```

Progress from this stage is automatically saved to a `.yml` file for each dataset.

### Link prediction

Once the datasets are profiled, this stage uses the `LinkPredictor` to analyze the metadata from all datasets and discover potential relationships between them. You can learn more about the [Link Prediction](./link-prediction.md) process in its dedicated section.

```python
# Run the link prediction stage
# This assumes profile() has already been run
sm.predict_links()

# Access the links via the `links` attribute, which is a shortcut
discovered_links = sm.links
print(discovered_links)

# You can also access the full LinkPredictor instance for more options
# See the section below for more details.
```

The discovered relationships are saved to a central `__relationships__.yml` file.

### Business glossary generation

In the final stage, the `SemanticModel` uses a Large Language Model (LLM) to generate business-friendly context for your data.

```python
# Run the glossary generation stage
# This assumes profile() has already been run
sm.generate_glossary()
```

This information is saved back into each dataset's `.yml` file.

### The build method

For convenience, the `build()` method runs all three stages (`profile`, `predict_links`, `generate_glossary`) in the correct sequence.

```python
# Run the full pipeline from start to finish
sm.build()

# You can also force it to re-run everything, ignoring any cached results
sm.build(force_recreate=True)
```

This modular design means that if the process is interrupted during the `generate_glossary` stage, you can simply re-run `sm.build()`, and it will skip the already-completed stages, picking up right where it left off.

## Accessing processed datasets and predictor

After running any stage of the pipeline, you can access the enriched `DataSet` objects and the `LinkPredictor` instance to explore the results programmatically.

```python
# Run the full build
sm.build()

# Access the 'customers' dataset
customers_dataset = sm.datasets['customers']

# Access the LinkPredictor instance
link_predictor = sm.link_predictor

# Now you can explore rich metadata or results
print(f"Primary Key for customers: {customers_dataset.source_table_model.description}")
print("Discovered Links:")
print(link_predictor.get_links_df())
```

Learn more about what you can do with these objects. See the [DataSet](./dataset.md) and [Link Prediction](./link-prediction.md) documentation.

## Utility DataFrames

The `SemanticModel` provides three convenient properties that consolidate the results from all processed datasets into single Pandas DataFrames.

### `profiling_df`

Returns a DataFrame containing the full profiling metrics for every column across all datasets.

```python
# Get a single DataFrame of all column profiles
all_profiles = sm.profiling_df
print(all_profiles.head())
```

### `links_df`

A shortcut to the `get_links_df()` method on the `LinkPredictor`, this property returns a DataFrame of all discovered relationships.

```python
# Get a DataFrame of all predicted links
all_links = sm.links_df
print(all_links)
```

### `glossary_df`

Returns a DataFrame that serves as a consolidated business glossary, listing the table name, column name, description, and tags for every column across all datasets.

```python
# Get a single, unified business glossary
full_glossary = sm.glossary_df
print(full_glossary.head())
```