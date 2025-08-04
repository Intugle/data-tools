# Data Tools

A flexible and extensible Python library for profiling various types of dataframes. This tool automatically detects the dataframe format (e.g., pandas) and provides a standardized profiling output.

## Key Features

- **Automatic Type Detection**: No need to specify the dataframe type; the factory handles it automatically.
- **Standardized Profiling**: Get consistent output (row count, columns, data types) regardless of the underlying dataframe library.
- **Extensible Plugin Architecture**: Easily add support for new dataframe libraries (e.g., Spark, Dask) by creating a simple plugin.
- **Lightweight and Modern**: Built with modern Python practices and a minimal set of dependencies.

## Installation

To get started, clone the repository and install the necessary dependencies using `uv`.

```bash
git clone <your-repository-url>
cd data-tools
uv pip install -e .
```

## Quick Start

Using the library is straightforward. Simply create your dataframe and pass it to the `DataFrameFactory`.

```python
import pandas as pd
from data_tools.dataframes.factory import DataFrameFactory

# 1. Create a dataframe from any supported library
data = {
    'name': ['Alice', 'Bob', 'Charlie'],
    'age': [30, 25, 35],
    'city': ['New York', 'Los Angeles', 'Chicago'],
    'joined_date': pd.to_datetime(['2023-01-15', '2022-05-20', '2023-03-10'])
}
my_df = pd.DataFrame(data)

# 2. Initialize the factory
# The factory automatically discovers and registers available dataframe types.
factory = DataFrameFactory()

# 3. Let the factory auto-detect and create the correct wrapper
# It inspects the object `my_df` and finds the right handler.
data_tool_df = factory.create(my_df)

# 4. Profile the data
profile = data_tool_df.profile()

# Print the results
print(profile.model_dump_json(indent=2))
```

### Expected Output

```json
{
  "count": 3,
  "columns": [
    "name",
    "age",
    "city",
    "joined_date"
  ],
  "dtypes": {
    "name": "string",
    "age": "integer",
    "city": "string",
    "joined_date": "date & time"
  }
}
```

## How It Works

The library uses a **Factory Pattern** with a plugin-based architecture.

1.  **`DataFrame` Abstract Class**: Defines a common interface (`profile()` method) that all dataframe wrappers must implement.
2.  **`DataFrameFactory`**: The central component that manages registration and object creation.
3.  **Plugins**: Each supported dataframe type (like pandas) is a "plugin." A plugin consists of:
    - A **checker function** that identifies if it can handle a given object (e.g., `isinstance(df, pd.DataFrame)`).
    - A **creator class** (e.g., `PandasDF`) that implements the `DataFrame` interface.
    - A **`register` function** that provides the checker and creator to the factory.

When `factory.create(df)` is called, the factory iterates through its registered plugins, uses the first checker that returns `True`, and then uses the corresponding creator to wrap the dataframe object.

## Extending the Tool (Adding a New DataFrame Type)

To add support for a new library (e.g., Spark), follow these steps:

1.  **Create a New Module**: Add a file like `src/data_tools/dataframes/types/spark.py`.

2.  **Implement the `DataFrame` Interface**: Create a class (e.g., `SparkDF`) that inherits from `DataFrame` and implements the `profile()` method with logic specific to Spark DataFrames.

3.  **Create a Checker Function**: Write a function that returns `True` if the input object is a Spark DataFrame.
    ```python
    def can_handle_spark(df: Any) -> bool:
        # Your logic to check if df is a Spark DataFrame
        return "pyspark.sql.dataframe.DataFrame" in str(type(df))
    ```

4.  **Create a Register Function**: In the same file, create a function to register your new components with the factory.
    ```python
    from data_tools.dataframes.factory import DataFrameFactory

    def register(factory: DataFrameFactory):
        factory.register("spark", can_handle_spark, SparkDF)
    ```

5.  **Activate the Plugin**: Add the path to your new module in the `DEFAULT_PLUGINS` list in `src/data_tools/dataframes/factory.py`.
    ```python
    DEFAULT_PLUGINS = [
        "data_tools.dataframes.types.pandas",
        "data_tools.dataframes.types.spark"  # Add this line
    ]
    ```

## Running Tests

To run the test suite, first install the testing dependencies and then execute `pytest` via `uv`.

```bash
# Install testing library
uv pip install pytest

# Run tests
uv run pytest
```

## License

This project is licensed under the terms of the LICENSE file.
