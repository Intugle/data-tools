# Amazon Redshift Adapter for Intugle

This document explains how to use the **RedshiftAdapter** in Intugle to connect, profile, and work with Amazon Redshift data warehouses.

## Overview

The Redshift adapter enables Intugle to:

* Connect to Redshift clusters.
* Profile tables and columns.
* Execute queries and create new tables/views.
* Perform semantic searches and generate data products.

## Installation

Install the optional Redshift dependencies:

```bash
pip install "intugle[redshift]"
```

This installs:

* `redshift-connector>=2.0.0`
* Other necessary dependencies for Redshift integration

## Configuration

Configure your Redshift connection either in `profiles.yml` or via Python using `RedshiftConfig`.

### Example Python Configuration:

```python
from intugle.adapters.types.redshift.models import RedshiftConfig
from intugle.adapters.types.redshift.redshift import RedshiftAdapter

cfg = RedshiftConfig(
    host="your-cluster.xxxxxxxxxxxx.us-east-1.redshift.amazonaws.com",
    port=5439,
    user="your_username",
    password="your_password",
    database="dev",
    schema="public",
    ssl=True
)

adapter = RedshiftAdapter(cfg)
```

### IAM Authentication

You can enable IAM-based authentication instead of username/password:

```yaml
redshift:
  iam: true
  cluster_id: "your-cluster-id"
  region: "us-east-1"
```

## Using the Adapter

### Connect to Redshift

```python
conn = adapter.connect()
```

### Profile Tables

```python
profile = adapter.profile(table_name="sales")
print(profile)
```

### Execute Query

```python
result_df = adapter.to_df_from_query("SELECT * FROM sales LIMIT 10")
```

### Create Table from Query

```python
adapter.create_table_from_query(
    table_name="new_sales",
    query="SELECT * FROM sales WHERE amount > 100"
)
```
## Notes

* Redshift is largely PostgreSQL-compatible, but some SQL functions or data types may differ.
* Use `ssl=True` in production for secure connections.
* IAM authentication is optional but recommended for added security.
* The adapter uses `redshift-connector` under the hood for database interactions.
