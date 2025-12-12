import uuid

from typing import Any, Dict, List, Optional

import pandas as pd


class NoSQLParser:
    """
    Parser for converting NoSQL-style data (list of dictionaries) into a set of relational tables.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.tables: Dict[str, List[Dict[str, Any]]] = {}
        self.config = config or {}

    def parse(self, data: List[Dict[str, Any]], root_table_name: str = "root") -> Dict[str, pd.DataFrame]:
        """
        Parses a list of dictionaries into a dictionary of pandas DataFrames.
        Nested lists are stripped out into separate tables and linked via foreign keys.

        Args:
            data: A list of dictionaries representing the NoSQL data.
            root_table_name: The name of the root table (default: "root").

        Returns:
            A dictionary where keys are table names and values are pandas DataFrames.
        """
        self.tables = {}
        
        if not data:
            return {}

        # Check for root table rename
        root_table_name = self.config.get("table_renames", {}).get(root_table_name, root_table_name)

        for row in data:
            self._process_node(row, root_table_name)

        # Convert lists of dicts to DataFrames
        result = {}
        for table_name, rows in self.tables.items():
            if rows:
                result[table_name] = pd.json_normalize(rows)
            else:
                result[table_name] = pd.DataFrame()
        
        return result

    def _process_node(
        self, 
        row_data: Dict[str, Any], 
        table_name: str, 
        parent_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Recursively processes a node (row) of data.
        """
        # Determine Primary Key
        pk_column = self.config.get("pk_overrides", {}).get(table_name)
        
        # If ID not present, we need to establish it either via override or generation
        # If override is set, we expect that column to exist.
        if pk_column and pk_column in row_data:
            current_id = row_data[pk_column]
            # Ensure internal _id tracks this for consistency in processing, 
            # though usually we might want to keep the original column as the PK.
            # For this parser, we use _id as the internal tracker.
            row_data["_id"] = current_id 
        elif "_id" not in row_data:
            row_data["_id"] = str(uuid.uuid4())
            current_id = row_data["_id"]
        else:
            current_id = row_data["_id"]
        
        # If there is a parent, link back to it
        if parent_info:
            parent_id_col = f"{parent_info['table_name']}_id"
            row_data[parent_id_col] = parent_info['id']

        # Prepare storage for the current row, separating scalars from lists
        scalar_data = {}
        
        for key, value in row_data.items():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                # Handle list of dicts -> Child Table
                default_child_name = f"{table_name}_{key}"
                child_table_name = self.config.get("table_renames", {}).get(default_child_name, default_child_name)
                
                for item in value:
                    self._process_node(
                        item, 
                        child_table_name, 
                        parent_info={"table_name": table_name, "id": current_id}
                    )
            elif isinstance(value, list) and not value:
                # Empty list, ignore
                scalar_data[key] = value
            else:
                # Scalar or simple object
                scalar_data[key] = value

        if table_name not in self.tables:
            self.tables[table_name] = []
        self.tables[table_name].append(scalar_data)
