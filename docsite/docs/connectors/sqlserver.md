---
sidebar_position: 4
---

# SQL Server

The SQL Server adapter allows `intugle` to connect to Microsoft SQL Server and Azure SQL databases. It uses the modern [`mssql-python`](https://github.com/microsoft/mssql-python) driver, which connects directly to SQL Server without needing an external driver manager like ODBC.

## OS Dependencies

The `mssql-python` driver may require additional system-level libraries depending on your operating system (e.g., `libltdl` on Linux). Before proceeding, please ensure you have installed any necessary prerequisites for your OS.

For detailed, OS-specific installation instructions, please refer to the official **[Microsoft mssql-python documentation](httpshttps://learn.microsoft.com/en-us/sql/connect/python/mssql-python/python-sql-driver-mssql-python-quickstart?view=sql-server-ver17&tabs=windows%2Cazure-sql)**.

## Installation

To use this adapter, you must install the necessary dependencies as an extra:

```bash
pip install "intugle[sqlserver]"
```

## Profile Configuration

To configure the connection, add a `sqlserver` entry to your `profiles.yml` file.

**`profiles.yml`**
```yaml
sqlserver:
  name: my_sqlserver_source # A unique name for this source
  type: sqlserver
  host: "your_server_address"
  port: 1433
  user: "your_username"
  password: "your_password"
  database: "your_database_name"
  schema: "dbo" # Optional, defaults to 'dbo'
  encrypt: true # Optional, defaults to true
```

| Key        | Description                                                                                             | Required | Default |
| ---------- | ------------------------------------------------------------------------------------------------------- | -------- | ------- |
| `name`     | A unique identifier for this data source connection.                                                    | Yes      |         |
| `type`     | The type of the adapter. Must be `sqlserver`.                                                           | Yes      |         |
| `host`     | The hostname or IP address of your SQL Server instance.                                                 | Yes      |         |
| `port`     | The port number for the connection.                                                                     | No       | `1433`  |
| `user`     | The username for authentication.                                                                        | Yes      |         |
| `password` | The password for authentication.                                                                        | Yes      |         |
| `database` | The name of the database to connect to.                                                                 | Yes      |         |
| `schema`   | The default schema to use for tables that are not fully qualified.                                      | No       | `dbo`   |
| `encrypt`  | Whether to encrypt the connection. Recommended to keep this `true`.                                     | No       | `true`  |

## Dataset Configuration

When defining datasets for the `SemanticModel`, use the `type: "sqlserver"` and provide the table name as the `identifier`.

```python
from intugle import SemanticModel

datasets = {
    "customers": {
        "type": "sqlserver",
        "identifier": "Customers" # The name of the table in SQL Server
    },
    "orders": {
        "type": "sqlserver",
        "identifier": "Orders"
    },
    # ... other datasets
}

# Build the semantic model
sm = SemanticModel(datasets, domain="E-commerce")
sm.build()
```
