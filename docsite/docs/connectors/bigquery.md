---
sidebar_position: 7
---

# BigQuery

`intugle` integrates with Google BigQuery, allowing you to read data from your datasets for profiling, analysis, and data product generation.

## Installation

To use `intugle` with BigQuery, you must install the optional dependencies:

```bash
pip install "intugle[bigquery]"
```

This installs the `google-cloud-bigquery` library.

## Configuration

To connect to your BigQuery project, you must provide connection credentials in a `profiles.yml` file at the root of your project. The adapter looks for a top-level `bigquery:` key.

**Example `profiles.yml`:**

```yaml
bigquery:
  name: my_bigquery_source
  project_id: <your_gcp_project_id>
  dataset: <your_dataset_name>
  location: US  # Optional, defaults to US
  credentials_path: /path/to/service-account-credentials.json  # Optional
```

### Authentication Options

1. **Service Account JSON File** (Recommended for production):
   - Set `credentials_path` to your service account JSON file.
   - The service account needs **BigQuery Data Viewer** and **BigQuery Job User** roles.

2. **Application Default Credentials** (For development):
   - Omit `credentials_path`.
   - Uses `gcloud auth application-default login`.
   - Or uses environment variable `GOOGLE_APPLICATION_CREDENTIALS`.

## Usage

### Reading Data from BigQuery

To include a BigQuery table or view in your `SemanticModel`, define it in your input dictionary with `type: "bigquery"` and use the `identifier` key to specify the table name.

:::caution Important
The dictionary key for your dataset (e.g., `"my_table"`) must exactly match the table name specified in the `identifier`.
:::

```python
from intugle import SemanticModel

datasets = {
    "my_table": {
        "identifier": "my_table", # Must match the key above
        "type": "bigquery"
    },
    "another_view": {
        "identifier": "another_view",
        "type": "bigquery"
    }
}

# Initialize the semantic model
sm = SemanticModel(datasets, domain="Analytics")

# Build the model as usual
sm.build()
```

### Materializing Data Products

When you use the `DataProduct` class with a BigQuery connection, the resulting data product can be materialized as a new **table** or **view** directly within your target dataset.

:::caution
**Beta Feature:** The DataProduct feature for BigQuery is currently in beta. If you encounter any issues, please raise them on our [GitHub issues page](https://github.com/Intugle/data-tools/issues).
:::

```python
from intugle import DataProduct

etl_model = {
    "name": "top_users",
    "fields": [
        {"id": "users.id", "name": "user_id"},
        {"id": "users.name", "name": "user_name"},
    ]
}

dp = DataProduct()

# Materialize as a view (default)
dp.build(etl_model, materialize="view")

# Materialize as a table
dp.build(etl_model, materialize="table")
```

:::info Required Permissions
To successfully materialise data products, the Service Account or User must have the following privileges:
*   `roles/bigquery.dataViewer` - Read table data
*   `roles/bigquery.jobUser` - Run queries
*   `roles/bigquery.dataEditor` - Create tables and views
:::
