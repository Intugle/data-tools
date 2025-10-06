---
sidebar_position: 4
---

# Implementing a Connector

:::tip Pro Tip: Use an AI Coding Assistant
The fastest way to implement a new adapter is to use an AI coding assistant like the **Gemini CLI**, **Cursor**, or **Claude**.

1.  **Provide Context:** Give the assistant the code for an existing, similar adapter (e.g., `SnowflakeAdapter` or `DatabricksAdapter`).
2.  **State Your Goal:** Ask it to replicate the structure and logic for your new data source. For example: *"Using the Snowflake adapter as a reference, create a new adapter for MyConnector."*
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

1.  **Connection Config:** Defines the parameters needed to connect to your data source (e.g., host, user, password). This will be the format that will be picked up from the profiles.yml
2.  **Data Config:** Defines how to identify a specific table or asset from that source. This will be the format that will be used to pass the datasets into the SemanticModel

**Example `models.py`:**
```python
from typing import Optional
from intugle.common.schema import SchemaBase

class MyConnectorConnectionConfig(SchemaBase):
    host: str
    port: int
    user: str
    password: str
    schema: Optional[str] = None

class MyConnectorConfig(SchemaBase):
    identifier: str
    type: str = "myconnector"
```

Finally, open `src/intugle/adapters/models.py` and add your new `MyConnectorConfig` to the `DataSetData` type hint:

```python
# src/intugle/adapters/models.py

# ... other imports
from intugle.adapters.types.myconnector.models import MyConnectorConfig

DataSetData = pd.DataFrame | DuckdbConfig | ... | MyConnectorConfig
```

## Step 3: Implement the Adapter Class

In `src/intugle/adapters/types/myconnector/myconnector.py`, create your adapter class. It must inherit from `Adapter` and implement its abstract methods.

This is a simplified skeleton. You can look at the `DatabricksAdapter` or `SnowflakeAdapter` for a more complete example.

**Example `myconnector.py`:**
```python
from typing import Any, Optional
import pandas as pd
from intugle.adapters.adapter import Adapter
from intugle.adapters.factory import AdapterFactory
from intugle.adapters.models import ColumnProfile, ProfilingOutput
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
        pass

    # --- Must be implemented ---

    def profile(self, data: Any, table_name: str) -> ProfilingOutput:
        # Return table-level metadata: row count, column names, and dtypes
        raise NotImplementedError()

    def column_profile(self, data: Any, table_name: str, column_name: str, total_count: int) -> Optional[ColumnProfile]:
        # Return column-level statistics: null count, distinct count, samples, etc.
        raise NotImplementedError()

    def execute(self, query: str):
        # Execute a query and return the raw results
        raise NotImplementedError()

    def to_df_from_query(self, query: str) -> pd.DataFrame:
        # Execute a query and return the result as a pandas DataFrame
        raise NotImplementedError()

    def create_table_from_query(self, table_name: str, query: str) -> str:
        # Materialize a query as a new table or view
        raise NotImplementedError()

    def create_new_config_from_etl(self, etl_name: str) -> "DataSetData":
        # Return a new MyConnectorConfig for a materialized table
        return MyConnectorConfig(identifier=etl_name)

    def intersect_count(self, table1: "DataSet", column1_name: str, table2: "DataSet", column2_name: str) -> int:
        # Calculate the count of intersecting values between two columns
        raise NotImplementedError()

    # --- Other required methods ---
    
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
        factory.register("myconnector", can_handle_myconnector, MyConnectorAdapter)
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

If your adapter requires a specific driver library (like `databricks-sql-connector` for Databricks), you should add it as an optional dependency.

1.  Open the `pyproject.toml` file at the root of the project.
2.  Add a new extra under the `[project.optional-dependencies]` section.

    ```toml
    # In pyproject.toml

    [project.optional-dependencies]
    # ... other dependencies
    myconnector = ["myconnector-driver-library>=1.0.0"]
    ```

This allows users to install the necessary libraries by running `pip install "intugle[myconnector]"`.

That's it! You have now implemented and registered a custom connector.
