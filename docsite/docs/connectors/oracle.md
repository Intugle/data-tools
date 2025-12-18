---
sidebar_position: 4
---

# Oracle

`intugle` integrates with Oracle Database, allowing you to read data from your tables, views, and materialized views. It uses the modern [`python-oracledb`](https://python-oracledb.readthedocs.io/en/latest/) driver.

## Installation

To use `intugle` with Oracle, you must install the optional dependencies:

```bash
pip install "intugle[oracle]"
```

This installs the `oracledb`, `numpy`, and `sqlglot` libraries.

## Configuration

To connect to your Oracle database, you must provide connection credentials in a `profiles.yml` file. The adapter looks for a top-level `oracle:` key. You must provide either a `service_name` or a `sid`.

**Example `profiles.yml`:**

```yaml
oracle:
  host: <your_oracle_host>
  port: 1521 # Default Oracle port
  user: <your_username>
  password: <your_password>
  service_name: <your_service_name>
  # OR
  # sid: <your_sid>
  schema: <your_schema_name> # Optional, defaults to USERNAME in uppercase
```

| Key            | Description                                                                  | Required | Default |
| -------------- | ---------------------------------------------------------------------------- | -------- | ------- |
| `host`         | The hostname or IP address of your Oracle instance.                          | Yes      |         |
| `port`         | The port number for the connection.                                          | No       | `1521`  |
| `user`         | The username for authentication.                                             | Yes      |         |
| `password`     | The password for authentication.                                             | Yes      |         |
| `service_name` | The Oracle service name.                                                     | No*      |         |
| `sid`          | The Oracle System Identifier (SID).                                          | No*      |         |
| `schema`       | The schema to use. If not provided, it defaults to the username in uppercase. | No       |         |

*\*Either `service_name` or `sid` must be provided.*

## Usage

### Reading Data from Oracle

To include an Oracle table, view, or materialized view in your `SemanticModel`, define it in your input dictionary with `type: "oracle"` and use the `identifier` key to specify the object name.

:::caution Important
The dictionary key for your dataset (e.g., `"CUSTOMERS"`) must exactly match the table or view name specified in the `identifier`. Oracle identifiers are typically case-insensitive and stored in uppercase.
:::

```python
from intugle import SemanticModel

datasets = {
    "CUSTOMERS": {
        "identifier": "CUSTOMERS", # Must match the key above
        "type": "oracle"
    },
    "ORDERS_VIEW": {
        "identifier": "ORDERS_VIEW", # Can be a view
        "type": "oracle"
    }
}

# Initialize the semantic model
sm = SemanticModel(datasets, domain="E-commerce")

# Build the model as usual
sm.build()
```

### Materializing Data Products

When you use the `DataProduct` class with an Oracle connection, the resulting data product can be materialized as a new **table**, **view**, or **materialized view** directly within your target schema.

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

:::info Compatibility
The Oracle adapter uses the `FETCH FIRST n ROWS ONLY` syntax for data profiling samples, which requires **Oracle Database 12c or later**.
:::
