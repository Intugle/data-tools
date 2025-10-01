---
sidebar_position: 1
title: Semantic Model
---

# Semantic Model

The `SemanticModel` is the core class in `intugle`. It orchestrates the entire process of profiling, link prediction, and glossary generation to build a unified semantic layer over your data.

## Initialization

You can initialize the `SemanticModel` in two ways, depending on your use case.

### Method 1: From a Dictionary (Recommended)

This is the simplest and most common method. You provide a dictionary where each key is a unique name for a dataset, and the value contains its configuration (like path and type).

```python
from intugle import SemanticModel

datasets = {
    "allergies": {"path": "path/to/allergies.csv", "type": "csv"},
    "patients": {"path": "path/to/patients.csv", "type": "csv"},
    "claims": {"path": "path/to/claims.csv", "type": "csv"},
}

sm = SemanticModel(datasets, domain="Healthcare")
```

:::info Connecting to Data Sources
While these examples use local CSV files, `intugle` can connect to various data sources. See our **[Connectors documentation](../../connectors/snowflake)** for details on specific integrations like Snowflake.
:::

### Method 2: From a List of DataSet Objects

For more advanced scenarios, you can initialize the `SemanticModel` with a list of pre-configured `DataSet` objects. This is useful if you have already instantiated `DataSet` objects for other purposes.

```python
from intugle import SemanticModel, DataSet

# Create DataSet objects first
dataset_allergies = DataSet(data={"path": "path/to/allergies.csv", "type": "csv"}, name="allergies")
dataset_patients = DataSet(data={"path": "path/to/patients.csv", "type": "csv"}, name="patients")

# Initialize the SemanticModel with the list of objects
sm = SemanticModel([dataset_allergies, dataset_patients], domain="Healthcare")
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