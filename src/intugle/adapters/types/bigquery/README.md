# BigQuery Adapter for Intugle

This adapter enables Intugle to connect to Google BigQuery datasets for profiling, analysis, and data product generation.

## Installation

Install the BigQuery adapter dependencies:

```bash
pip install intugle[bigquery]
```

## Configuration

Configure your BigQuery connection in `profiles.yml`:

```yaml
bigquery:
  name: my_bigquery_source
  project_id: your-gcp-project-id
  dataset: your_dataset_name
  location: US  # Optional, defaults to US
  credentials_path: /path/to/service-account-credentials.json  # Optional
```

### Authentication Options

1. **Service Account JSON File** (Recommended for production):
   - Set `credentials_path` to your service account JSON file
   - The service account needs BigQuery Data Viewer and BigQuery Job User roles

2. **Application Default Credentials** (For development):
   - Omit `credentials_path`
   - Uses `gcloud auth application-default login`
   - Or uses environment variable `GOOGLE_APPLICATION_CREDENTIALS`

## Usage

### Basic Example

```python
from intugle.adapters.types.bigquery.models import BigQueryConfig
from intugle.adapters.factory import AdapterFactory

# Create adapter factory
factory = AdapterFactory()

# Define your BigQuery table
config = BigQueryConfig(
    identifier="my_table",
    type="bigquery"
)

# Get the adapter
adapter = factory.create(config)

# Profile the table
profile_result = adapter.profile(config, "my_table")
print(f"Total rows: {profile_result.count}")
print(f"Columns: {profile_result.columns}")

# Query and get DataFrame
df = adapter.to_df_from_query("SELECT * FROM `project.dataset.table` LIMIT 100")
```

### Creating Views/Tables from Queries

```python
# Create a view
adapter.create_table_from_query(
    table_name="my_new_view",
    query="SELECT * FROM `project.dataset.source_table` WHERE date > '2024-01-01'",
    materialize="view"
)

# Create a materialized table
adapter.create_table_from_query(
    table_name="my_new_table",
    query="SELECT * FROM `project.dataset.source_table` WHERE date > '2024-01-01'",
    materialize="table"
)
```

## Features

- ✅ Connect to BigQuery using service accounts or application default credentials
- ✅ Profile BigQuery tables and columns
- ✅ Execute Standard SQL queries
- ✅ Convert query results to pandas DataFrames
- ✅ Create views and tables from queries
- ✅ Analyze relationships between tables
- ✅ Support for composite keys
- ✅ Full integration with Intugle's semantic search and data product generation

## Supported Operations

| Operation | Description |
|-----------|-------------|
| `profile()` | Get table statistics and column information |
| `column_profile()` | Get detailed column statistics including null counts, distinct values, and samples |
| `execute()` | Run arbitrary SQL queries |
| `to_df()` | Convert table to pandas DataFrame |
| `to_df_from_query()` | Execute query and return results as DataFrame |
| `create_table_from_query()` | Create views or tables from queries |
| `intersect_count()` | Count matching values between two columns |
| `get_composite_key_uniqueness()` | Check uniqueness of composite keys |
| `intersect_composite_keys_count()` | Count matching composite key combinations |

## Requirements

- Python 3.8+
- google-cloud-bigquery >= 3.11.0
- Valid Google Cloud Project with BigQuery enabled
- Appropriate IAM permissions (BigQuery Data Viewer, BigQuery Job User)

## Limitations

- Large dataset queries may incur BigQuery processing costs
- Query results are limited by BigQuery's maximum response size
- Some operations require specific BigQuery permissions

## Troubleshooting

### Authentication Errors

If you encounter authentication errors:

1. Verify your credentials file path is correct
2. Check that the service account has the required permissions
3. Ensure `GOOGLE_APPLICATION_CREDENTIALS` environment variable is set (if using ADC)

### Permission Errors

Ensure your service account or user has these roles:
- `roles/bigquery.dataViewer` - Read table data
- `roles/bigquery.jobUser` - Run queries

### Query Timeout

For long-running queries, consider:
- Using table sampling for profiling
- Breaking down complex queries into smaller steps
- Increasing the query timeout in your BigQuery client configuration

## License

This adapter follows the same Apache 2.0 license as the Intugle project.

## Contributing

Contributions are welcome! Please ensure:
- All tests pass
- New features include unit tests
- Code follows the existing style
- Documentation is updated

## Support

For issues or questions:
- Open an issue on GitHub
- Join our Discord community
- Check the main Intugle documentation
