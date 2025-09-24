import logging

from typing import List, Optional, TypedDict

import pandas as pd

from pydantic import BaseModel, Field

from intugle.core import settings
from intugle.core.utilities.processing import classify_datetime_format, preprocess_profiling_data

log = logging.getLogger(__name__)


class linkage(BaseModel):
    table1: str = Field(description="Verbatim name of table1 or NA")
    column1: str = Field(description="Verbatim name of column1 in table1 or NA")
    table2: str = Field(description="Verbatim name of table2 or NA")
    column2: str = Field(description="Verbatim name of column2 in table2 or NA")


def extract_innermost_dict(d):
    if isinstance(d, dict):
        for key, value in d.items():
            if isinstance(value, dict):
                # Recursively search for the innermost dictionary
                return extract_innermost_dict(value)
    return d  # Return the current dictionary when no further dictionaries are found


FEASIBLE_DTYPES = {
    "group1": ["integer", "float"],
    "group2": ["alphanumeric", "close_ended_text"],
    "group3": ["close_ended_text", "open_ended_text"]
}


class GraphState(TypedDict):
    input_text: str
    potential_link: dict
    error_msg: List[str]
    iteration: int
    link_type: str
    if_error: bool
    intersect_count: Optional[int] = None
    intersect_ratio_from_col: Optional[float] = None
    intersect_ratio_to_col: Optional[float] = None
    accuracy: Optional[float] = None


def dtype_check(dtype1: str, dtype2: str) -> bool:

    if dtype1 == dtype2:
        return True
    
    for _, feasible_dtypes in FEASIBLE_DTYPES.items():

        if dtype1 in feasible_dtypes and dtype2 in feasible_dtypes:
            return True
        
    return False


def preprocess_profiling_df(profiling_data: pd.DataFrame):

    profiling_data = preprocess_profiling_data(
        profiling_data=profiling_data,
        sample_limit=settings.STRATA_SAMPLE_LIMIT,
        dtypes_to_filter=["dimension"],
        truncate_sample_data=True
    )

    if settings.REMOVE_DATETIME_LP:
        profiling_data = profiling_data.loc[
            ~(profiling_data["datatype_l1"] == "date & time")
        ].reset_index(drop=True)

    condn2 = (
        profiling_data["datatype_l1"].isin(["integer", "float"])
    ) & (profiling_data["datatype_l2"] == "dimension")

    profiling_data["datatype"] = profiling_data["datatype_l1"]

    profiling_data.loc[condn2, "datatype"] = (
        profiling_data.loc[condn2, "datatype_l1"] + "_dimension"
    )

    condn = profiling_data["datatype_l1"] == "date & time"

    if condn.any():
        log.info(
            "[!] Warning date time should not be considered in link prediction"
        )
        profiling_data.loc[condn, "date_time_format"] = profiling_data.loc[
            condn, "sample_data"
        ].apply(
            classify_datetime_format,
        )

        def datetime_format(dtype, format):
            return f"{dtype} ({format})"

        profiling_data.loc[condn, "datatype"] = profiling_data.loc[condn].apply(
            lambda row: datetime_format(
                row["predicted_datatype_l1"], row["date_time_format"]
            ),
            axis=1,
        )
    
    def percent_conversion(x):
        return f"{(x * 100):.2f}%"

    profiling_data["uniqueness_ratio"] = profiling_data["uniqueness"]
    profiling_data["uniqueness"] = profiling_data.uniqueness.apply(
        percent_conversion
    )
    profiling_data["completeness"] = profiling_data.completeness.apply(
        percent_conversion
    )

    return profiling_data