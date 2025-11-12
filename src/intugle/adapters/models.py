from enum import Enum
from typing import TYPE_CHECKING, Any, List, Optional

from pydantic import BaseModel, Field


# Dynamic type registration - DataSetData is now built from registered adapters
# This avoids hardcoding specific config types
def get_dataset_data_type() -> type:
    """
    Returns the dynamically constructed DataSetData Union type.
    This function retrieves the type from AdapterFactory after all adapters have been registered.
    """
    from intugle.adapters.factory import AdapterFactory
    return AdapterFactory.get_dataset_data_type()


# For type hints that need DataSetData before runtime, we use a forward reference
if TYPE_CHECKING:
    import pandas as pd

    from intugle.adapters.types.databricks.models import DatabricksConfig
    from intugle.adapters.types.duckdb.models import DuckdbConfig
    from intugle.adapters.types.postgres.models import PostgresConfig
    from intugle.adapters.types.snowflake.models import SnowflakeConfig
    from intugle.adapters.types.sqlserver.models import SQLServerConfig

    DataSetData = pd.DataFrame | DuckdbConfig | SnowflakeConfig | DatabricksConfig | PostgresConfig | SQLServerConfig
else:
    # At runtime, this is dynamically determined
    DataSetData = Any


class ProfilingOutput(BaseModel):
    count: int
    columns: list[str]
    dtypes: dict[str, str]


class ColumnProfile(BaseModel):
    """
    A Pydantic model for validating the response of the column_profile function.

    """

    column_name: str = Field(..., description="The name of the column being profiled.")
    business_name: str = Field(..., description="Cleaned column name")
    table_name: str = Field(
        ..., description="The name of the source table or a placeholder (e.g., 'pandas_dataframe')."
    )
    null_count: int = Field(..., description="The total number of null (NaN or None) values in the column.")
    count: int = Field(..., description="The total number of rows in the DataFrame (including nulls).")
    distinct_count: int = Field(..., description="The number of unique non-null values in the column.")
    uniqueness: float = Field(
        ..., description="The ratio of distinct values to total count, indicating the uniqueness of the column."
    )
    completeness: float = Field(
        ..., description="The ratio of non-null values to total count, indicating the completeness of the column."
    )
    sample_data: List[Any] = Field(
        ..., description="A sample of unique values from the column, up to the specified sample_limit."
    )
    dtype_sample: Optional[List[Any]] = Field(
        None, description="A combined sample of unique and non-unique values, intended for data type inference."
    )
    ts: float = Field(..., description="The timestamp indicating how long the profiling took, in seconds.")
    datatype_l1: Optional[str] = Field(
        default=None, description="The inferred data type for the column, based on the sample data."
    )
    datatype_l2: Optional[str] = Field(
        default=None,
        description="The inferred data type category (dimension/measure) for the column, based on the datatype l1 results",
    )
    business_glossary: Optional[str] = Field(
        default=None, description="The business glossary entry for the column, if available."
    )
    business_tags: Optional[List[str]] = Field(
        default=None, description="A list of business tags associated with the column, if any."
    )


class DataTypeIdentificationL1Output(BaseModel):
    """
    A Pydantic model for validating the response of the datatype_identification function.

    """

    column_name: str = Field(..., description="The name of the column being profiled.")
    table_name: str = Field(
        ..., description="The name of the source table or a placeholder (e.g., 'pandas_dataframe')."
    )
    datatype_l1: str = Field(
        ..., validation_alias="predicted_datatype_l1", description="The inferred data type for the column."
    )


class DataTypeIdentificationL2Input(BaseModel):
    """
    A Pydantic model for validating the response of the column_profile function.

    """

    column_name: str = Field(..., description="The name of the column being profiled.")
    table_name: str = Field(
        ..., description="The name of the source table or a placeholder (e.g., 'pandas_dataframe')."
    )
    sample_data: List[Any] = Field(
        ..., description="A sample of unique values from the column, up to the specified sample_limit."
    )
    datatype_l1: Optional[str] = Field(
        default=None, description="The inferred data type for the column, based on the sample data."
    )


class L2OutputTypes(str, Enum):
    dimension = "dimension"
    measure = "measure"
    unknown = "unknown"


class DataTypeIdentificationL2Output(BaseModel):
    """
    A Pydantic model for validating the response of the datatype_identification function.

    """

    column_name: str = Field(..., description="The name of the column being profiled.")
    table_name: str = Field(
        ..., description="The name of the source table or a placeholder (e.g., 'pandas_dataframe')."
    )
    datatype_l2: L2OutputTypes = Field(
        ...,
        validation_alias="predicted_datatype_l2",
        description="The inferred category (dimension or measure) for the column.",
    )



class ColumnGlossary(BaseModel):
    """
    Represents the business glossary and tags for a single column.
    """

    column_name: str = Field(..., description="The name of the column.")
    business_glossary: str = Field(None, description="A business-friendly term for the column.")
    business_tags: List[str] = Field(
        default_factory=list, description="A list of business tags associated with the column."
    )


class BusinessGlossaryOutput(BaseModel):
    """
    Represents the business glossary and tags for all columns in a dataset.
    """

    table_name: str = Field(
        ..., description="The name of the source table or a placeholder (e.g., 'pandas_dataframe')."
    )
    table_glossary: str = Field(..., description="A business-friendly description for the dataset.")
    columns: List[ColumnGlossary] = Field(
        default_factory=list, description="A list of ColumnGlossary objects for each column in the dataset."
    )
