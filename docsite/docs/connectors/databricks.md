---
sidebar_position: 2
---

# Databricks

`intugle` integrates with Databricks, allowing you to read data from your tables and deploy your `SemanticModel` by setting constraints and comments directly in your Databricks account.

## Installation

To use `intugle` with Databricks, you must install the optional dependencies:

```bash
pip install "intugle[databricks]"
```

This installs the `pyspark`, `sqlglot` and  `databricks-sql-connector` libraries.

## Configuration

The Databricks adapter can connect using credentials from a `profiles.yml` file or automatically use an active session when running inside a Databricks notebook.

### Connecting from an External Environment

When running `intugle` outside of a Databricks notebook, you must provide full connection credentials in a `profiles.yml` file at the root of your project. The adapter looks for a top-level `databricks:` key.

**Example `profiles.yml`:**

```yaml
databricks:
  host: <your_databricks_host>
  http_path: <your_sql_warehouse_http_path>
  token: <your_personal_access_token>
  schema: <your_schema>
  catalog: <your_catalog> # Optional, for Unity Catalog
```

### Connecting from a Databricks Notebook

When your code is executed within a Databricks Notebook, the adapter automatically detects and uses the notebook's active Spark session for execution. However, it still requires a `profiles.yml` file to determine the target `schema` and `catalog` for your operations.

**Example `profiles.yml` for Notebooks:**

```yaml
databricks:
  schema: <your_schema>
  catalog: <your_catalog> # Optional, for Unity Catalog
```

## Usage

### Reading Data from Databricks

To include a Databricks table in your `SemanticModel`, define it in your input dictionary with `type: "databricks"` and use the `identifier` key to specify the table name.

:::caution Important
The dictionary key for your dataset (e.g., `"CUSTOMERS"`) must exactly match the table name specified in the `identifier`.
:::

```python
from intugle import SemanticModel

datasets = {
    "CUSTOMERS": {
        "identifier": "CUSTOMERS", # Must match the key above
        "type": "databricks"
    },
    "ORDERS": {
        "identifier": "ORDERS", # Must match the key above
        "type": "databricks"
    }
}

# Initialize the semantic model
sm = SemanticModel(datasets, domain="E-commerce")

# Build the model as usual
sm.build()
```

### Materializing Data Products

When you use the `DataProduct` class with a Databricks connection, the resulting data product will be materialized as a new **view** directly within your target schema.

### Deploying the Semantic Model

Once your semantic model is built, you can deploy it to Databricks using the `deploy()` method. This process syncs your model's intelligence to your physical tables by:
1.  **Syncing Metadata:** It updates the comments on your physical Databricks tables and columns with the business glossaries from your `intugle` model. You can also sync tags.
2.  **Setting Constraints:** It sets `PRIMARY KEY` and `FOREIGN KEY` constraints on your tables based on the relationships discovered in the model.

```python
# Deploy the model to Databricks
sm.deploy(target="databricks")

# You can also control which parts of the deployment to run
sm.deploy(
    target="databricks",
    sync_glossary=True,
    sync_tags=True,
    set_primary_keys=True,
    set_foreign_keys=True
)
```

