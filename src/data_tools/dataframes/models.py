from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


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
    table_name: str = Field(..., description="The name of the source table or a placeholder (e.g., 'pandas_dataframe').")
    null_count: int = Field(..., description="The total number of null (NaN or None) values in the column.")
    count: int = Field(..., description="The total number of rows in the DataFrame (including nulls).")
    distinct_count: int = Field(..., description="The number of unique non-null values in the column.")
    uniqueness: float = Field(..., description="The ratio of distinct values to total count, indicating the uniqueness of the column.")
    completeness: float = Field(..., description="The ratio of non-null values to total count, indicating the completeness of the column.")
    sample_data: List[Any] = Field(..., description="A sample of unique values from the column, up to the specified sample_limit.")
    dtype_sample: Optional[List[Any]] = Field(None, description="A combined sample of unique and non-unique values, intended for data type inference.")
    ts: float = Field(..., description="The timestamp indicating how long the profiling took, in seconds.")
    datatype_l1: Optional[str] = Field(default=None, description="The inferred data type for the column, based on the sample data.")
    datatype_l2: Optional[str] = Field(default=None, description="The inferred data type category (dimension/measure) for the column, based on the datatype l1 results")


class DataTypeIdentificationL1Output(BaseModel):
    """
    A Pydantic model for validating the response of the datatype_identification function.
    
    """
    column_name: str = Field(..., description="The name of the column being profiled.")
    table_name: str = Field(..., description="The name of the source table or a placeholder (e.g., 'pandas_dataframe').")
    datatype_l1: str = Field(..., validation_alias='predicted_datatype_l1', description="The inferred data type for the column.")


class DataTypeIdentificationL2Input(BaseModel):
    """
    A Pydantic model for validating the response of the column_profile function.
    
    """
    column_name: str = Field(..., description="The name of the column being profiled.")
    table_name: str = Field(..., description="The name of the source table or a placeholder (e.g., 'pandas_dataframe').")
    sample_data: List[Any] = Field(..., description="A sample of unique values from the column, up to the specified sample_limit.")
    datatype_l1: Optional[str] = Field(default=None, description="The inferred data type for the column, based on the sample data.")


class L2OutputTypes(str, Enum):
    dimension = "dimension"
    measure = "measure"
    unknown = "unknown"


class DataTypeIdentificationL2Output(BaseModel):
    """
    A Pydantic model for validating the response of the datatype_identification function.
    
    """
    column_name: str = Field(..., description="The name of the column being profiled.")
    table_name: str = Field(..., description="The name of the source table or a placeholder (e.g., 'pandas_dataframe').")
    datatype_l2: L2OutputTypes = Field(..., validation_alias='predicted_datatype_l2', description="The inferred category (dimension or measure) for the column.")


class KeyIdentificationOutput(BaseModel):
    """
    A Pydantic model for validating the response of the key_identification function.
    
    """
    column_name: str = Field(..., description="The name of the column identified as a primary key.")