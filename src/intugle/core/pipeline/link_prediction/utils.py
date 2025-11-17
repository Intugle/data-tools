import json
import logging

from typing import Dict, List, Optional, TypedDict

import pandas as pd

from pydantic import BaseModel, Field

from intugle.analysis.models import DataSet
from intugle.core import settings
from intugle.core.utilities.processing import classify_datetime_format, preprocess_profiling_data
from intugle.models.resources.model import PrimaryKey

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
                row["datatype_l1"], row["date_time_format"]
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


DTYPE_MAPPING = {
    "integer": "INTEGER",
    "float": "FLOAT",
    "date & time": "DATETIME",
    "close_ended_text": "TEXT",
    "open_ended_text": "TEXT",
    "alphanumeric": "TEXT",
    "others": "TEXT",
    "range_type": "TEXT",
}


def generate_table_ddl_statements(
    table_columns: list,
    column_datatypes: dict = {},
    table_name: str = "",
    profiling_data: pd.DataFrame = None,
    columns_required: list = [],
    primary_key_obj: Optional[PrimaryKey] = None,
):
    create_table_query = f"CREATE TABLE {table_name} (\n"
    column_parts = []

    for column in table_columns:
        parts = []
        parts.append(f"  {column}")
        if column in column_datatypes:
            datatype = DTYPE_MAPPING[column_datatypes[column]]
            datatype = f"({datatype})"
        else:
            datatype = "VARCHAR(20)"

        parts.append(datatype)

        profiling = ""
        if profiling_data is not None:
            try:
                profiling_row = profiling_data.loc[
                    profiling_data["upstream_column_name"] == column,
                    list(columns_required),
                ].to_dict(orient="records")[0]
            except IndexError:
                # Column not found in profiling_data, skip adding profiling info
                profiling_row = {}

            if profiling_row:
                # Format sample_data as a string representation of a list
                sample_data_str = str(profiling_row.pop("sample_data", []))
                profiling_str = json.dumps(profiling_row).replace("{", "").replace("}", "").replace("\"", "")
                profiling = f" -- {profiling_str}, sample_data: {sample_data_str}"

        column_parts.append(" ".join(parts) + profiling)

    pk_clause = []
    if primary_key_obj and primary_key_obj.columns:
        pk_cols = ", ".join([f'"{col}"' for col in primary_key_obj.columns])
        pk_clause.append(f"  PRIMARY KEY ({pk_cols})")

    all_parts = column_parts
    if pk_clause:
        all_parts.append(pk_clause[0])

    create_table_query += ",\n".join(all_parts)
    create_table_query += "\n);"

    return create_table_query


def prepare_ddl_statements(dataset: DataSet) -> Dict[str, str]:
    ddl_statements = {}
    table_name = dataset.name
    profiling_df = dataset.profiling_df.copy()
    profiling_df.rename(columns={
        "column_name": "upstream_column_name",
        "table_name": "upstream_table_name",
        "distinct_count": "distinct_value_count",
        "predicted_datatype_l1": "datatype_l1",
        "predicted_datatype_l2": "datatype_l2",
        "uniqueness": "uniqueness_ratio",
        "completeness": "completeness_ratio",
        "business_glossary": "glossary",
    }, inplace=True)

    column_datatypes = {
        col.name: col.type
        for col in dataset.source.table.columns
        if col.type is not None
    }

    ddl_statement = generate_table_ddl_statements(
        table_columns=profiling_df["upstream_column_name"].to_list(),
        table_name=table_name,
        profiling_data=profiling_df,
        columns_required=[
            "glossary",
            "datatype_l1",
            "distinct_value_count",
            "uniqueness_ratio",
            "completeness_ratio",
            "sample_data"
        ],
        column_datatypes=column_datatypes,
        primary_key_obj=dataset.source.table.key,
    )

    ddl_statements[table_name] = ddl_statement

    return ddl_statements


