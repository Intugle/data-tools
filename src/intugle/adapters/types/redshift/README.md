# Amazon Redshift Adapter

The Redshift adapter allows Intugle to connect to and interact with Amazon Redshift data warehouses.

## Installation

To use the Redshift adapter, you need to install Intugle with the Redshift optional dependencies:

```bash
pip install intugle[redshift]
```

This will install:
- `redshift-connector>=2.1.0` - The official Amazon Redshift Python connector
- `sqlglot>=27.20.0` - SQL transpilation library

## Configuration

Add a Redshift configuration to your `profiles.yml` file:

```yaml
redshift:
  name: my_redshift_source
  user: your_username
  password: your_password
  host: your-cluster.region.redshift.amazonaws.com
  port: 5439  # Default Redshift port
  database: your_database
  schema: public
```

### Configuration Parameters

- **name** (optional): A friendly name for your Redshift source. Defaults to "my_redshift_source"
- **user**: Your Redshift username
- **password**: Your Redshift password
- **host**: The Redshift cluster endpoint (without the port)
- **port**: The port number (default: 5439)
- **database**: The database name to connect to
- **schema**: The schema to use for queries

## Usage

### Basic Example

```python
from intugle.adapters.types.redshift.models import RedshiftConfig
from intugle.adapters.types.redshift.redshift import RedshiftAdapter

# Create a config for your table
config = RedshiftConfig(
    identifier="my_table",
    type="redshift"
)

# Get the adapter instance
adapter = RedshiftAdapter()

# Profile the table
profile = adapter.profile(config, "my_table")
print(f"Total rows: {profile.count}")
print(f"Columns: {profile.columns}")
```

### Profile a Column

```python
# Get detailed profile for a specific column
column_profile = adapter.column_profile(
    data=config,
    table_name="my_table",
    column_name="customer_id",
    total_count=profile.count,
    sample_limit=10,
    dtype_sample_limit=10000
)

print(f"Distinct count: {column_profile.distinct_count}")
print(f"Null count: {column_profile.null_count}")
print(f"Uniqueness: {column_profile.uniqueness}")
print(f"Completeness: {column_profile.completeness}")
```

### Query and Create Views/Tables

```python
# Execute a query and get results as DataFrame
df = adapter.to_df_from_query("SELECT * FROM my_table LIMIT 100")

# Create a view from a query
query = """
SELECT customer_id, SUM(order_total) as total_spent
FROM orders
GROUP BY customer_id
HAVING SUM(order_total) > 1000
"""

adapter.create_table_from_query(
    table_name="high_value_customers",
    query=query,
    materialize="view"  # Options: "view", "table", "materialized_view"
)
```

### Analyzing Relationships

```python
from intugle.analysis.models import DataSet

# Create DataSet objects
customers = DataSet(
    RedshiftConfig(identifier="customers"),
    name="customers"
)

orders = DataSet(
    RedshiftConfig(identifier="orders"),
    name="orders"
)

# Find intersection count between tables
intersection = adapter.intersect_count(
    table1=customers,
    column1_name="customer_id",
    table2=orders,
    column2_name="customer_id"
)

print(f"Common customer IDs: {intersection}")
```

## Features

The Redshift adapter supports all standard Intugle adapter operations:

- **Profiling**: Get row counts, column lists, and data types
- **Column Profiling**: Detailed statistics including null counts, distinct values, uniqueness, and completeness
- **Query Execution**: Run arbitrary SQL queries
- **DataFrame Conversion**: Convert query results to Pandas DataFrames
- **Table/View Creation**: Create tables, views, or materialized views from queries
- **Relationship Analysis**: Calculate intersections between tables
- **Composite Key Analysis**: Analyze uniqueness of composite keys

## SQL Dialect

The adapter uses SQLGlot to transpile queries to Redshift's SQL dialect. This means you can write queries in a more standard SQL format, and they will be automatically converted to Redshift-compatible SQL.

## Notes

- The Redshift adapter is based on the PostgreSQL adapter since Redshift is built on PostgreSQL
- Some SQL features may differ from standard PostgreSQL due to Redshift's columnar storage and distributed architecture
- For best performance, consider Redshift's distribution keys and sort keys when creating tables
- Materialized views in Redshift need to be manually refreshed using `REFRESH MATERIALIZED VIEW`

## Troubleshooting

### Connection Issues

If you're having trouble connecting:

1. Verify your cluster endpoint and credentials
2. Check that your IP is whitelisted in the Redshift security group
3. Ensure the cluster is publicly accessible (if connecting from outside AWS)
4. Verify the database and schema exist

### Missing Dependencies

If you see an error about missing dependencies:

```
ImportError: Redshift dependencies are not installed. Please run 'pip install intugle[redshift]'.
```

Install the required dependencies:

```bash
pip install intugle[redshift]
```

## License

The `redshift-connector` package is licensed under the Apache License 2.0, which is compatible with this project's Apache 2.0 license.
