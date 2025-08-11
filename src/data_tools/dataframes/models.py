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


class AssetColumnProfileResponse(BaseModel):
    """
    A Pydantic model for validating the response of the asset_column_profile_pandas function.
    
    This model ensures that the output conforms to a strict, predictable schema.
    """
    name: str = Field(..., description="The name of the column being profiled.")
    table_name: str = Field(..., description="The name of the source table or a placeholder (e.g., 'pandas_dataframe').")
    profile: ColumnProfile = Field(..., description="An object containing detailed count statistics for the column.")
    sample_data: List[Any] = Field(..., description="A sample of unique values from the column, up to the specified sample_limit.")
    dtype_sample: Optional[List[Any]] = Field(None, description="A combined sample of unique and non-unique values, intended for data type inference.")
    ts: float = Field(..., description="The timestamp indicating how long the profiling took, in seconds.")
