---
sidebar_position: 8
---

# Implementing a Connector

:::tip Pro Tip: Use an AI Coding Assistant
The fastest way to implement a new adapter is to use an AI coding assistant like the **Gemini CLI**, **Cursor**, or **Claude**.

1.  **Provide Context:** Give the assistant the code for an existing, similar adapter (e.g., `PostgresAdapter` or `DatabricksAdapter`).
2.  **State Your Goal:** Ask it to replicate the structure and logic for your new data source. For example: *"Using the Postgres adapter as a reference, create a new adapter for Redshift."*
3.  **Iterate:** The assistant can generate the boilerplate code for the models, the adapter class, and the registration functions, allowing you to focus on the specific implementation details for your database driver.
:::

`intugle` is designed to be extensible, allowing you to connect to any data source by creating a custom adapter. This guide walks you through the process of building your own connector.

If you build a connector that could benefit the community, we strongly encourage you to [open a pull request and contribute it](https://github.com/Intugle/data-tools/blob/main/CONTRIBUTING.md) to the `intugle` project!

## Overview

An adapter is a Python class that inherits from `intugle.adapters.adapter.Adapter` and implements a set of methods for interacting with a specific data source. It handles everything from connecting to the database to profiling data and executing queries.

The core steps to create a new connector are:
1.  **Create the Scaffolding:** Set up the necessary directory and files.
2.  **Define Configuration Models:** Create Pydantic models for your connector's configuration.
3.  **Implement the Adapter Class:** Write the logic to interact with your data source.
4.  **Register the Adapter:** Make your new adapter discoverable by the `intugle` factory.
5.  **Add Optional Dependencies:** Declare the necessary driver libraries.

## Step 1: Create the Scaffolding

First, create a new directory for your connector within the `src/intugle/adapters/types/` directory. For a connector named `myconnector`, you would create:

```
src/intugle/adapters/types/myconnector/
├── __init__.py
├── models.py
└── myconnector.py
```

-   `__init__.py`: Can be an empty file.
-   `models.py`: Will contain the Pydantic configuration models.
-   `myconnector.py`: Will contain the main adapter class logic.

## Step 2: Define Configuration Models

In `src/intugle/adapters/types/myconnector/models.py`, you need to define two Pydantic models:

1.  **Connection Config:** Defines the parameters needed to connect to your data source (e.g., host, user, password). This is the structure that will be read from `profiles.yml`.
2.  **Data Config:** Defines how to identify a specific table or asset from that source. This is the structure used when passing datasets into the `SemanticModel`.

**Example `models.py`:**
```python
from typing import Optional
from intugle.common.schema import SchemaBase

class MyConnectorConnectionConfig(SchemaBase):
    host: str
    port: int
    user: str
    password: str
    database: str
    schema: Optional[str] = None

class MyConnectorConfig(SchemaBase):
    identifier: str
    type: str = "myconnector"
```

Finally, open `src/intugle/adapters/models.py` and add your new `MyConnectorConfig` to the `DataSetData` type hint. This is for static type checking and improves developer experience.

```python
# src/intugle/adapters/models.py

# ... other imports
from intugle.adapters.types.myconnector.models import MyConnectorConfig

if TYPE_CHECKING:
    # ... other configs
    DataSetData = pd.DataFrame | ... | MyConnectorConfig
```

## Step 3: Implement the Adapter Class

In `src/intugle/adapters/types/myconnector/myconnector.py`, create your adapter class. It must inherit from `Adapter` and implement its abstract methods.

This is a simplified skeleton. Refer to the `PostgresAdapter` or `DatabricksAdapter` for a complete example.

**Example `myconnector.py`:**
```python
from typing import Any, Optional
import pandas as pd
from intugle.adapters.adapter import Adapter
from intugle.adapters.factory import AdapterFactory
from intugle.adapters.models import ColumnProfile, ProfilingOutput, DataSetData
from .models import MyConnectorConfig, MyConnectorConnectionConfig
from intugle.core import settings

# Import your database driver
# import myconnector_driver

class MyConnectorAdapter(Adapter):
    def __init__(self):
        # Initialize your connection here
        connection_params = settings.PROFILES.get("myconnector", {})
        config = MyConnectorConnectionConfig.model_validate(connection_params)
        # self.connection = myconnector_driver.connect(**config.model_dump())
        self._database = config.database
        self._schema = config.schema
        pass

    # --- Properties ---
    @property
    def database(self) -> Optional[str]:
        return self._database

    @property
    def schema(self) -> Optional[str]:
        return self._schema
    
    @property
    def source_name(self) -> str:
        return "my_connector_source"

    # --- Abstract Method Implementations ---

    def profile(self, data: Any, table_name: str) -> ProfilingOutput:
        # Return table-level metadata: row count, column names, and dtypes
        raise NotImplementedError()

    def column_profile(self, data: Any, table_name: str, column_name: str, total_count: int, **kwargs) -> Optional[ColumnProfile]:
        # Return column-level statistics: null count, distinct count, samples, etc.
        raise NotImplementedError()

    def execute(self, query: str):
        # Execute a query and return the raw results
        raise NotImplementedError()

    def to_df_from_query(self, query: str) -> pd.DataFrame:
        # Execute a query and return the result as a pandas DataFrame
        raise NotImplementedError()

    def create_table_from_query(self, table_name: str, query: str, materialize: str = "view", **kwargs) -> str:
        # Materialize a query as a new table or view
        raise NotImplementedError()

    def create_new_config_from_etl(self, etl_name: str) -> "DataSetData":
        # Return a new MyConnectorConfig for a materialized table
        return MyConnectorConfig(identifier=etl_name)

    def intersect_count(self, table1: "DataSet", column1_name: str, table2: "DataSet", column2_name: str) -> int:
        # Calculate the count of intersecting values between two columns
        raise NotImplementedError()
    
    def load(self, data: Any, table_name: str):
        # For database adapters, this is often a no-op
        pass

    def to_df(self, data: DataSetData, table_name: str):
        # Read an entire table into a pandas DataFrame
        config = MyConnectorConfig.model_validate(data)
        return self.to_df_from_query(f"SELECT * FROM {config.identifier}")

    def get_details(self, data: DataSetData):
        config = MyConnectorConfig.model_validate(data)
        return config.model_dump()
```

## Step 4: Register the Adapter

To make `intugle` aware of your new adapter, you must register it with the factory.

1.  **Add registration functions to `myconnector.py`:** At the bottom of your adapter file, add two functions: one to check if the adapter can handle a given data config, and one to register it with the factory.

    ```python
    # In src/intugle/adapters/types/myconnector/myconnector.py

    def can_handle_myconnector(df: Any) -> bool:
        try:
            MyConnectorConfig.model_validate(df)
            return True
        except Exception:
            return False

    def register(factory: AdapterFactory):
        # Check if the required driver is installed
        # if MYCONNECTOR_DRIVER_AVAILABLE:
        factory.register("myconnector", can_handle_myconnector, MyConnectorAdapter, MyConnectorConfig)
    ```

2.  **Add the adapter to the default plugins list:** Open `src/intugle/adapters/factory.py` and add the path to your new adapter module.

    ```python
    # In src/intugle/adapters/factory.py

    DEFAULT_PLUGINS = [
        "intugle.adapters.types.pandas.pandas",
        # ... other adapters
        "intugle.adapters.types.myconnector.myconnector",
    ]
    ```

## Step 5: Add Optional Dependencies

If your adapter requires a specific driver library (like `asyncpg` for Postgres), you should add it as an optional dependency.

1.  Open the `pyproject.toml` file at the root of the project.
2.  Add a new extra under the `[project.optional-dependencies]` section.

    ```toml
    # In pyproject.toml

    [project.optional-dependencies]
    # ... other dependencies
    myconnector = ["myconnector-driver-library>=1.0.0"]
    ```

This allows users to install the necessary libraries by running `pip install "intugle[myconnector]"`.

## Best Practices and Considerations

When implementing your adapter, keep the following points in mind to ensure it is robust, secure, and efficient.

### Handling Database Objects
Your adapter should be able to interact with different types of database objects, not just tables.
-   **Tables, Views, and Materialized Views:** Ensure your `profile` method can read and `create_table_from_query` method can handle creating these different object types. The `materialize` parameter can be used to control this behavior. For example, the Postgres adapter supports `table`, `view`, and `materialized_view`.
-   **Identifier Quoting:** Always wrap table and column identifiers in quotes (e.g., `"` for Postgres and Snowflake) to handle special characters, spaces, and case-sensitivity correctly.

### Secure Query Execution
-   **Parameterized Queries:** To prevent SQL injection vulnerabilities, always use parameterized queries when user-provided values are part of a SQL statement. Most database drivers provide a safe way to pass parameters (e.g., using `?` or `$1` placeholders) instead of formatting them directly into the query string.

    **Do this:**
    ```python
    # Example with asyncpg
    await connection.fetch("SELECT * FROM users WHERE id = $1", user_id)
    ```

    **Avoid this:**
    ```python
    # Unsafe - vulnerable to SQL injection
    await connection.fetch(f"SELECT * FROM users WHERE id = {user_id}")
    ```

### Stability and Error Handling
-   **Network Errors and Timeouts:** Implement timeouts for both establishing connections and executing queries. This prevents your application from hanging indefinitely if the database is unresponsive. Your chosen database driver should provide options for setting these timeouts.
-   **Graceful Error Handling:** Wrap database calls in `try...except` blocks to catch potential exceptions (e.g., connection errors, permission denied) and provide clear, informative error messages to the user.

### Atomicity
-   **Transactions:** For operations that involve multiple SQL statements (like dropping and then recreating a table), wrap them in a transaction. This ensures that the entire operation is atomic—it either completes successfully, or all changes are rolled back if an error occurs, preventing the database from being left in an inconsistent state.

That's it! You have now implemented and registered a custom connector.
