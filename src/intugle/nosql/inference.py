from typing import Any, Dict, List, Set


def infer_schema(data: List[Dict[str, Any]], sample_size: int = 100) -> Dict[str, str]:
    """
    Infers the schema of the NoSQL data by sampling records.
    Handles type conflicts (e.g., int vs str -> str).
    Identifies potential primary keys.
    """
    if not data:
        return {}

    schema: Dict[str, Set[str]] = {}
    
    # Analyze sample data
    for row in data[:sample_size]:
        for key, value in row.items():
            if key not in schema:
                schema[key] = set()
            
            if value is None:
                continue
                
            # Determine type
            if isinstance(value, bool):
                type_name = "bool"
            elif isinstance(value, int):
                type_name = "int"
            elif isinstance(value, float):
                type_name = "float"
            elif isinstance(value, str):
                type_name = "string"
            elif isinstance(value, dict):
                type_name = "object"
            elif isinstance(value, list):
                type_name = "list"
            else:
                type_name = "unknown"
                
            schema[key].add(type_name)

    final_schema: Dict[str, str] = {}
    
    # Resolve conflicts
    for key, types in schema.items():
        if not types:
            final_schema[key] = "string"  # Default for all-null
        elif len(types) == 1:
            final_schema[key] = list(types)[0]
        else:
            # Conflict resolution
            if "string" in types:
                final_schema[key] = "string"
            elif "float" in types and "int" in types:
                final_schema[key] = "float"
            elif "list" in types:
                # If list mixes with something else, it's tricky. 
                # For now, if list is involved, we might mark it as complex/string or keep as mixed.
                # Let's fallback to string/object representation for now if mixed.
                final_schema[key] = "string"  # simplified fallback
            else:
                final_schema[key] = "string"

    return final_schema


def identify_primary_key(schema: Dict[str, str]) -> str | None:
    """
    Identifies a potential primary key from the schema keys.
    """
    candidates = ["_id", "id", "uuid", "guid"]
    for candidate in candidates:
        if candidate in schema:
            return candidate
    return None
