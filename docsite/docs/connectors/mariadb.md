---
sidebar_position: 5
---

# MariaDB

`intugle` integrates with MariaDB, allowing you to read data from your tables and views.

## Installation

To use `intugle` with MariaDB, you must install the optional dependencies:

```bash
pip install "intugle[mariadb]"
```

This installs the `mariadb` (MariaDB Connector/Python) and `sqlglot` libraries.

:::warning Linux Dependencies
On Linux, the MariaDB Connector/Python requires the MariaDB C Connector dependencies to be installed on your system.
For example, on Ubuntu/Debian:
```bash
sudo apt-get install libmariadb3 libmariadb-dev
```
On CentOS/RHEL:
```bash
sudo yum install mariadb-connector-c-devel
```
Please refer to the [MariaDB Connector/Python documentation](https://mariadb.com/docs/server/connect/programming-languages/python/install/#installing-mariadb-connector-python) for more details.
:::

## Configuration

To connect to your MariaDB database, you must provide connection credentials in a `profiles.yml` file at the root of your project. The adapter looks for a top-level `mariadb:` key.

**Example `profiles.yml`:**

```yaml
mariadb:
  host: <your_mariadb_host>
  port: 3306 # Default MariaDB port
  user: <your_username>
  password: <your_password>
  database: <your_database_name>
```

## Usage

### Reading Data from MariaDB

To include a MariaDB table or view in your `SemanticModel`, define it in your input dictionary with `type: "mariadb"` and use the `identifier` key to specify the object name.

:::caution Important
The dictionary key for your dataset (e.g., `"CUSTOMERS"`) must exactly match the table or view name specified in the `identifier`.
:::

```python
from intugle import SemanticModel

datasets = {
    "CUSTOMERS": {
        "identifier": "CUSTOMERS", # Must match the key above
        "type": "mariadb"
    },
    "ORDERS_VIEW": {
        "identifier": "ORDERS_VIEW", # Can be a view
        "type": "mariadb"
    }
}

# Initialize the semantic model
sm = SemanticModel(datasets, domain="E-commerce")

# Build the model as usual
sm.build()
```

### Materializing Data Products

When you use the `DataProduct` class with a MariaDB connection, the resulting data product can be materialized as a new **table** or **view** directly within your target database.

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
