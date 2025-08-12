import json
import logging

import pandas as pd

log = logging.getLogger(__name__)

DTYPE_MAPPING = {
    "integer": "INTEGER",
    "float": "FLOAT",
    "date & time": "DATETIME",
    "close_ended_text": "TEXT",
    "open_ended_text": "TEXT",
    "alphanumeric": "TEXT",
    "others": "TEXT",
    "range_type": "TEXT"
}


def generate_create_table_query(table_columns: list,
                                   column_datatypes: dict = {},
                                   table_name: str = "",
                                   profiling_data: pd.DataFrame = None,
                                   primary_keys: list = [],
                                   columns_required: list = [],
                                   mapping_dtypes_to_sql: bool = False
                                   ):
    
    create_table_query = f"CREATE TABLE {table_name.lower()} ("
    column_parts = []
    lngth = len(table_columns)

    for i, column in enumerate(table_columns, 1):
        parts = []
        parts.append(f"{column}")
        column_id = (table_name, column)    
        if column_id in column_datatypes:
            datatype = column_datatypes[column_id] if not mapping_dtypes_to_sql else DTYPE_MAPPING[column_datatypes[column_id]]
            datatype = "(" + datatype + ")"
        else:
            datatype = "VARCHAR(20)"

        parts.append(f"{datatype}")

        pk = ""
        if column_id in primary_keys:
            pk = "PRIMARY KEY"
        
        pk = f"{pk},".lstrip()
        if i == lngth:
            pk = pk.rstrip(",")

        parts.append(pk)

        profiling = ""
        if profiling_data is not None:
            
            profiling = profiling_data.loc[
                (profiling_data["column_name"] == column) & 
                (profiling_data["table_name"] == table_name), 
                list(columns_required)
            ].to_dict(orient="records")[0]

            sample_data = ""

            profiling = json.dumps(profiling).replace("{", "").replace("}", "").replace('"', '').replace("_l1", "")
            profiling = f" -- {profiling}{sample_data}"
        
        parts.append(profiling)
        column_parts.append(" ".join(parts))

    create_table_query = "\n".join([create_table_query] + column_parts + [");"])
    return create_table_query


def read_column_datatypes(dtype: pd.DataFrame,):
    column_datatypes = {}
    try:
        for row in range(len(dtype)): 
            table_name = dtype['table_name'][row].lower()
            column_name = dtype['column_name'][row].lower()
            datatype = dtype['datatype_l1'][row]
            column_datatypes[(table_name, column_name)] = datatype
    except Exception as ex:
        log.warning(f"[!] Error while getting column datatypes: {ex}")
        
    return column_datatypes






