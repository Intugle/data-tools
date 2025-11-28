---
sidebar_position: 5
---

# MySQL

`intugle` integrates with MySQL, allowing you to read data from your tables and views.

## Installation

To use `intugle` with MySQL, you must install the optional dependencies:

```bash
pip install "intugle[mysql]"
```

This installs the `PyMySQL` and `sqlglot` libraries.

## Configuration

To connect to your MySQL database, you must provide connection credentials in a `profiles.yml` file at the root of your project. The adapter looks for a top-level `mysql:` key.

**Example `profiles.yml`:**

```yaml
mysql:
  host: <your_mysql_host>
  port: 3306 # Default MySQL port
  user: <your_username>
  password: <your_password>
  database: <your_database_name>
```

## Usage

### Reading Data from MySQL

To include a MySQL table or view in your `SemanticModel`, define it in your input dictionary with `type: "mysql"` and use the `identifier` key to specify the object name.

:::caution Important
The dictionary key for your dataset (e.g., `"CUSTOMERS"`) must exactly match the table or view name specified in the `identifier`.
:::

```python
from intugle import SemanticModel

datasets = {
    "CUSTOMERS": {
        "identifier": "CUSTOMERS", # Must match the key above
        "type": "mysql"
    },
    "ORDERS_VIEW": {
        "identifier": "ORDERS_VIEW", # Can be a view
        "type": "mysql"
    }
}

# Initialize the semantic model
sm = SemanticModel(datasets, domain="E-commerce")

# Build the model as usual
sm.build()
```

### Materializing Data Products

When you use the `DataProduct` class with a MySQL connection, the resulting data product can be materialized as a new **table** or **view** directly within your target database.

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
```
