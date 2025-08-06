from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ProfilingOutput(BaseModel):
    count: int
    columns: list[str]
    dtypes: dict[str, str]


class ColumnProfile(BaseModel):
    """
    A Pydantic model to represent the detailed profile statistics of a column.
    """
    null_count: int = Field(..., description="The total number of null (NaN or None) values in the column.")
    count: int = Field(..., description="The total number of rows in the DataFrame (including nulls).")
    distinct_count: int = Field(..., description="The number of unique non-null values in the column.")


class ColumnProfileOutput(BaseModel):
    """
    A Pydantic model for validating the response of the column_profile function.
    
    This model ensures that the output conforms to a strict, predictable schema.
    """
    name: str = Field(..., description="The name of the column being profiled.")
    business_name: str = Field(..., description="Cleaned column name")
    table_name: str = Field(..., description="The name of the source table or a placeholder (e.g., 'pandas_dataframe').")
    profile: ColumnProfile = Field(..., description="An object containing detailed count statistics for the column.")
    sample_data: List[Any] = Field(..., description="A sample of unique values from the column, up to the specified sample_limit.")
    dtype_sample: Optional[List[Any]] = Field(None, description="A combined sample of unique and non-unique values, intended for data type inference.")
    ts: float = Field(..., description="The timestamp indicating how long the profiling took, in seconds.")
    datatype_l1: Optional[str] = Field(default=None, description="The inferred data type for the column, based on the sample data.")


class DataTypeIdentificationL1Output(BaseModel):
    """
    A Pydantic model for validating the response of the datatype_identification function.
    
    This model ensures that the output conforms to a strict, predictable schema.
    """
    column_name: str = Field(..., description="The name of the column being profiled.")
    table_name: str = Field(..., description="The name of the source table or a placeholder (e.g., 'pandas_dataframe').")
    datatype_l1: str = Field(..., description="The inferred data type for the column.")
