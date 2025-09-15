---
sidebar_position: 4
title: Link Prediction
---

# Link Prediction

Link Prediction is one of the most powerful features of the Intugle Data Tools library. It is the process of automatically discovering meaningful relationships and potential join keys between different, isolated datasets. This turns a collection of separate tables into a connected semantic graph, which is the foundation for building unified data products.

## The `LinkPredictor` Class

The core component responsible for this process is the `LinkPredictor`. While the `KnowledgeBuilder` manages this process for you, you can also use the `LinkPredictor` directly for more granular control.

### Accessing the `LinkPredictor`

After running the `predict_links()` or `build()` method on a `KnowledgeBuilder` instance, you can access the underlying `LinkPredictor` instance via the `link_predictor` attribute.

```python
# After running the pipeline...
predictor_instance = kb.link_predictor

# Now you can use all the methods of the LinkPredictor
links_list = predictor_instance.links
```

### Manual Usage

To use the `LinkPredictor` manually, you must provide it with a list of fully profiled `DataSet` objects.

```python
from intugle import DataSet, LinkPredictor

# 1. Initialize and fully profile your DataSet objects first
customers_data = {"path": "path/to/customers.csv", "type": "csv"}
orders_data = {"path": "path/to/orders.csv", "type": "csv"}

customers_dataset = DataSet(customers_data, name="customers")
customers_dataset.profile().identify_datatypes().identify_keys()

orders_dataset = DataSet(orders_data, name="orders")
orders_dataset.profile().identify_datatypes().identify_keys()

# 2. Initialize the LinkPredictor with the processed datasets
predictor = LinkPredictor([customers_dataset, orders_dataset])

# 3. Run the prediction
predictor.predict(save=True)

# 4. Access the results
# The discovered links are stored as a list of PredictedLink objects in the `links` attribute
links_list = predictor.links
for link in links_list:
    print(f"Found link from {link.from_dataset}.{link.from_column} to {link.to_dataset}.{link.to_column}")
```

### Caching Mechanism

The `predict()` method is designed to be efficient. It saves its results to a `__relationships__.yml` file and only re-runs the analysis if it detects that any of the underlying dataset analyses have changed since the last run.

### Useful Methods and Attributes

#### `links`

The primary way to access the results. This attribute holds a list of `PredictedLink` Pydantic objects, giving you structured access to the discovered relationships.

#### `get_links_df()`

A utility function that converts the `links` list into a Pandas DataFrame. This is useful for quick exploration, analysis, or display in a notebook environment.

```python
# Get the results as a DataFrame for easy viewing
links_df = predictor.get_links_df()

# Display the DataFrame
# columns: from_dataset, from_column, to_dataset, to_column
print(links_df)
```

#### `save_yaml()` and `load_from_yaml()`

You can manually save the state of the predictor or load results from a specific file.

```python
# Save the discovered links to a custom file
predictor.save_yaml("my_custom_links.yml")

# Load links from a file
predictor.load_from_yaml("my_custom_links.yml")
```

#### `show_graph()`

After running the prediction, you can easily visualize the discovered relationships as a graph. This is an excellent way to understand the overall structure of your connected data.

```python
# This will render a graph of the relationships
predictor.show_graph()
```