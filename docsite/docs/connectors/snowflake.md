---
sidebar_position: 1
---

# Snowflake

`intugle` integrates with Snowflake, allowing you to read data from Snowflake tables and deploy your `SemanticModel` as a **Semantic View** in your Snowflake account.

## Installation

To use `intugle` with Snowflake, you must install the optional dependencies:

```bash
pip install "intugle[snowflake]"
```

This installs the `snowflake-snowpark-python` library.

## Configuration

The Snowflake adapter can connect using credentials from a `profiles.yml` file or automatically use an active session when running inside a Snowflake Notebook.

### Connecting from an External Environment

When running `intugle` outside of a Snowflake Notebook, you must provide connection credentials in a `profiles.yml` file at the root of your project. The adapter looks for a top-level `snowflake:` key.

**Example `profiles.yml`:**

```yaml
snowflake:
  type: snowflake
  account: <your_snowflake_account>
  user: <your_username>
  password: <your_password>
  role: <your_role>
  warehouse: <your_warehouse>
  database: <your_database>
  schema: <your_schema>
```

### Connecting from a Snowflake Notebook

When your code is executed within a Snowflake Notebook, the adapter automatically detects and uses the notebook's active Snowpark session. **No configuration is required.**

## Usage

### Reading Data from Snowflake

To include a Snowflake table in your `SemanticModel`, define it in your input dictionary with `type: "snowflake"` and use the `identifier` key to specify the table name.

:::caution Important
The dictionary key for your dataset (e.g., `"CUSTOMERS"`) must exactly match the table name specified in the `identifier`.
:::

```python
from intugle import SemanticModel

datasets = {
    "CUSTOMERS": {
        "identifier": "CUSTOMERS", # Must match the key above
        "type": "snowflake"
    },
    "ORDERS": {
        "identifier": "ORDERS", # Must match the key above
        "type": "snowflake"
    }
}

# Initialize the semantic model
sm = SemanticModel(datasets, domain="E-commerce")

# Build the model as usual
sm.build()
```

### Materializing Data Products

When you use the `DataProduct` class with a Snowflake connection, the resulting data product will be materialized as a new table directly within your Snowflake schema.

### Deploying the Semantic Model

Once your semantic model is built, you can deploy it to Snowflake using the `deploy()` method. This process performs two actions:
1.  **Syncs Metadata:** It updates the comments on your physical Snowflake tables and columns with the business glossaries from your `intugle` model.
2.  **Creates Semantic View:** It constructs and executes a `CREATE OR REPLACE SEMANTIC VIEW` statement in your target database and schema.

```python
# Deploy the model to Snowflake
sm.deploy(target="snowflake")

# You can also provide a custom name for the view
sm.deploy(target="snowflake", model_name="my_custom_semantic_view")
```

:::info Required Permissions
To successfully deploy a semantic model, the Snowflake role you are using must have the following privileges:
*   `USAGE` on the target database and schema.
*   `CREATE SEMANTIC VIEW` on the target schema.
*   `ALTER TABLE` permissions on the source tables to update their comments.
:::

:::tip Next Steps: Chat with your Data using Cortex Analyst
Now that you have deployed a Semantic View, you can use **Snowflake Cortex Analyst** to interact with your data using natural language. Cortex Analyst leverages the relationships and context defined in your Semantic View to answer questions without requiring you to write SQL.

To get started, navigate to **AI & ML -> Cortex Analyst** in the Snowflake UI and select your newly created view.
:::
