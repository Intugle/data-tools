---
sidebar_position: 3
---

# Postgres

`intugle` integrates with PostgreSQL, allowing you to read data from your tables, views, and materialized views, and deploy your `SemanticModel` by setting constraints and comments directly in your PostgreSQL database.

## Installation

To use `intugle` with PostgreSQL, you must install the optional dependencies:

```bash
pip install "intugle[postgres]"
```

This installs the `asyncpg` and `sqlglot` libraries.

## Configuration

To connect to your PostgreSQL database, you must provide connection credentials in a `profiles.yml` file at the root of your project. The adapter looks for a top-level `postgres:` key.

**Example `profiles.yml`:**

```yaml
postgres:
  host: <your_postgres_host>
  port: 5432 # Default PostgreSQL port
  user: <your_username>
  password: <your_password>
  database: <your_database_name>
  schema: <your_schema_name>
```

## Usage

### Reading Data from PostgreSQL

To include a PostgreSQL table, view, or materialized view in your `SemanticModel`, define it in your input dictionary with `type: "postgres"` and use the `identifier` key to specify the object name.

:::caution Important
The dictionary key for your dataset (e.g., `"CUSTOMERS"`) must exactly match the table, view, or materialized view name specified in the `identifier`.
:::

```python
from intugle import SemanticModel

datasets = {
    "CUSTOMERS": {
        "identifier": "CUSTOMERS", # Must match the key above
        "type": "postgres"
    },
    "ORDERS_VIEW": {
        "identifier": "ORDERS_VIEW", # Can be a view
        "type": "postgres"
    },
    "PRODUCT_MV": {
        "identifier": "PRODUCT_MV", # Can be a materialized view
        "type": "postgres"
    }
}

# Initialize the semantic model
sm = SemanticModel(datasets, domain="E-commerce")

# Build the model as usual
sm.build()
```

### Materializing Data Products

When you use the `DataProduct` class with a PostgreSQL connection, the resulting data product can be materialized as a new **table**, **view**, or **materialized view** directly within your target schema.

```python
from intugle import DataProduct

etl_model = {
    "name": "top_customers",
    "fields": [
        {"id": "CUSTOMERS.customer_id", "name": "customer_id"},
        {"id": "CUSTOMERS.name", "name": "customer_name"},
    ]
}

dp = DataProduct()

# Materialize as a view (default)
dp.build(etl_model, materialize="view")

# Materialize as a table
dp.build(etl_model, materialize="table")

# Materialize as a materialized view
dp.build(etl_model, materialize="materialized_view")
```

### Deploying the Semantic Model

Once your semantic model is built, you can deploy it to PostgreSQL using the `deploy()` method. This process syncs your model's intelligence to your physical tables by:
1.  **Syncing Metadata:** It updates the comments on your physical PostgreSQL tables and columns with the business glossaries from your `intugle` model.
2.  **Setting Constraints:** It sets `PRIMARY KEY` and `FOREIGN KEY` constraints on your tables based on the relationships discovered in the model.

```python
# Deploy the model to PostgreSQL
sm.deploy(target="postgres")

# You can also control which parts of the deployment to run
sm.deploy(
    target="postgres",
    sync_glossary=True,
    set_primary_keys=True,
    set_foreign_keys=True
)
```

:::info Required Permissions
To successfully deploy a semantic model, the PostgreSQL user you are using must have the following privileges:
*   `USAGE` on the target schema.
*   `CREATE TABLE`, `CREATE VIEW`, `CREATE MATERIALIZED VIEW` on the target schema.
*   `COMMENT` privilege on tables and columns.
*   `ALTER TABLE` to add primary and foreign key constraints.
:::
