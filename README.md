# Data Analysis Pipeline

A flexible and extensible Python library for building data analysis pipelines. This tool allows you to define a series of analysis steps that are executed in sequence, with each step building upon the results of the previous ones. The pipeline is designed to be dataframe-agnostic, with built-in support for pandas DataFrames and an easy-to-use plugin system for adding support for other libraries like Spark.

## Key Features

- **Analysis Pipeline**: Chain together multiple analysis steps to create a sophisticated data processing workflow.
- **Automatic Type Detection**: The underlying dataframe type is automatically detected, so you can use the same pipeline for different data sources.
- **Extensible Plugin Architecture**: Easily add support for new dataframe libraries (e.g., Spark, Dask) by creating a simple plugin.
- **Clear Dependency Management**: Each analysis step can depend on the results of previous steps, ensuring a robust and predictable workflow.
- **Separation of Concerns**: The pipeline architecture cleanly separates the analysis logic from the data access layer, making the code easier to maintain and test.

## Installation

To get started, clone the repository and install the necessary dependencies using `uv`.

```bash
git clone <your-repository-url>
cd data-tools
uv pip install -e .
```

## Quick Start

Using the library is straightforward. Simply define your pipeline, create your dataframe, and run the analysis.

```python
import pandas as pd
from data_tools.analysis.pipeline import Pipeline
from data_tools.analysis.steps import TableProfiler

# 1. Define your pipeline
pipeline = Pipeline([
    TableProfiler(),
    # Add other analysis steps here
])

# 2. Create your dataframe
data = {
    'name': ['Alice', 'Bob', 'Charlie'],
    'age': [30, 25, 35],
    'city': ['New York', 'Los Angeles', 'Chicago'],
    'joined_date': pd.to_datetime(['2023-01-15', '2022-05-20', '2023-03-10'])
}
my_df = pd.DataFrame(data)

# 3. Run the pipeline
analysis_results = pipeline.run(my_df)

# 4. Access the results
profile = analysis_results.results["table_profile"]

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

The library is built around a central `Pipeline` class that executes a series of `AnalysisStep` objects on a `DataSet`.

1.  **`DataSet`**: A container for the raw dataframe and all the analysis results. This object is passed from one pipeline step to the next.
2.  **`AnalysisStep`**: An abstract base class that defines the interface for all analysis steps. Each step implements an `analyze` method that takes a `DataSet` as input and adds its results to the `DataSet`.
3.  **`DataFrameFactory`**: A factory that automatically detects the dataframe type and creates a wrapper object that provides a consistent API for accessing the data.
4.  **`Pipeline`**: The orchestrator that takes a list of analysis steps and a dataframe, creates a `DataSet`, and runs the steps in sequence.

## Extending the Tool

### Adding a New Analysis Step

To add a new analysis step, create a new class that inherits from `AnalysisStep` and implement the `analyze` method.

```python
from data_tools.analysis.steps import AnalysisStep
from data_tools.analysis.models import DataSet

class MyCustomProfiler(AnalysisStep):
    def analyze(self, dataset: DataSet) -> None:
        # Your analysis logic here
        # ...
        dataset.results["my_custom_profile"] = my_results
```

### Adding a New DataFrame Type

To add support for a new dataframe library (e.g., Spark), follow these steps:

1.  **Create a New Module**: Add a file like `src/data_tools/dataframes/types/spark.py`.
2.  **Implement the `DataFrame` Interface**: Create a class (e.g., `SparkDF`) that inherits from `DataFrame` and implements the `profile()` method with logic specific to Spark DataFrames.
3.  **Create a Checker Function**: Write a function that returns `True` if the input object is a Spark DataFrame.
4.  **Create a Register Function**: In the same file, create a function to register your new components with the factory.
5.  **Activate the Plugin**: Add the path to your new module in the `DEFAULT_PLUGINS` list in `src/data_tools/dataframes/factory.py`.

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