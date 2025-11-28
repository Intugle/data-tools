---
sidebar_position: 6
---

# SQLite

`intugle` integrates with SQLite, allowing you to read data from your local database files.

## Installation

To use `intugle` with SQLite, you generally only need the base package as `sqlite3` is included in Python. However, for SQL generation features, `sqlglot` is required.

```bash
pip install intugle sqlglot
```

## Configuration

To connect to your SQLite database, you must provide the path to your database file in a `profiles.yml` file at the root of your project. The adapter looks for a top-level `sqlite:` key.

**Example `profiles.yml`:**

```yaml
sqlite:
  path: /absolute/path/to/your/database.db
```

## Usage

### Reading Data from SQLite

To include a SQLite table or view in your `SemanticModel`, define it in your input dictionary with `type: "sqlite"` and use the `identifier` key to specify the object name.

```python
from intugle import SemanticModel

datasets = {
    "CUSTOMERS": {
        "identifier": "CUSTOMERS",
        "type": "sqlite"
    },
    "ORDERS": {
        "identifier": "ORDERS",
        "type": "sqlite"
    }
}

# Initialize the semantic model
sm = SemanticModel(datasets, domain="E-commerce")

# Build the model as usual
sm.build()
```

### Materializing Data Products

When you use the `DataProduct` class with a SQLite connection, the resulting data product can be materialized as a new **table** or **view** directly within your database.

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
