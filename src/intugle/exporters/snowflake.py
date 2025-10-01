import re
from .base import Exporter
from intugle.libs.smart_query_generator.models.models import CategoryType
from intugle.core import settings
from intugle.models.resources.relationship import RelationshipType

RESERVED_WORDS = {'start', 'end', 'select', 'from', 'where', 'order', 'group', 'join', 'table', 'on'}

def clean_name(name: str) -> str:
    """Cleans an identifier to be a safe logical name for the Snowflake Semantic Model."""
    cleaned = name.strip().strip('"')
    # Replace invalid characters with underscore
    cleaned = re.sub(r'[^a-zA-Z0-9_$]', '_', cleaned)
    # Ensure it doesn't start with a number
    if re.match(r'^[0-9]', cleaned):
        cleaned = f'_{cleaned}'
    # Check against a list of common reserved words and prefix if necessary
    if cleaned.lower() in RESERVED_WORDS:
        return f'_{cleaned}'
    return cleaned

def quote_identifier(name: str) -> str:
    """Ensure the identifier is wrapped in exactly one pair of double quotes."""
    clean_name = name.strip().strip('"')
    return f'"{clean_name}"'

# Mapping from our types to Snowflake's expected data types
DATA_TYPE_MAPPING = {
    "integer": "NUMBER",
    "float": "FLOAT",
    "string": "TEXT",
    "date & time": "DATETIME",
    "alphanumeric": "TEXT",
    "close_ended_text": "TEXT",
    "open_ended_text": "TEXT",
    # Add other mappings as necessary
}

class SnowflakeExporter(Exporter):
    def export(self, **kwargs) -> dict:
        """
        Converts the internal manifest to a Snowflake Semantic Model YAML structure.
        """
        manifest = self.manifest
        
        # Get database and schema from profiles.yml
        profile = settings.PROFILES.get("intugle", {}).get("outputs", {}).get("dev", {})
        database = profile.get("database")
        schema = profile.get("schema")

        tables_list = []
        relationships_list = []

        # Process sources into tables
        for source in manifest.sources.values():
            table_dict = {
                "name": clean_name(source.table.name),
                "description": source.table.description,
                "base_table": {
                    "database": database,
                    "schema": schema,
                    "table": source.table.name
                },
                "dimensions": [],
                "facts": []
            }

            # Add primary key if it exists
            if source.table.key:
                table_dict["primary_key"] = {
                    "columns": [clean_name(source.table.key)]
                }

            # Map columns to dimensions and facts
            for column in source.table.columns:
                snowflake_type = DATA_TYPE_MAPPING.get(column.type, "TEXT") # Default to TEXT
                if column.category == CategoryType.dimension:
                    dimension = {
                        "name": clean_name(column.name),
                        "description": column.description,
                        "expr": quote_identifier(column.name),
                        "data_type": snowflake_type,
                        "unique": column.name == source.table.key
                    }
                    table_dict["dimensions"].append(dimension)
                elif column.category == CategoryType.measure:
                    fact = {
                        "name": clean_name(column.name),
                        "description": column.description,
                        "expr": quote_identifier(column.name),
                        "data_type": snowflake_type
                    }
                    table_dict["facts"].append(fact)
            
            tables_list.append(table_dict)

        # Process relationships
        for rel in manifest.relationships.values():
            source_table_name = rel.source.table
            target_table_name = rel.target.table
            
            source_table_info = manifest.sources.get(source_table_name)
            target_table_info = manifest.sources.get(target_table_name)

            if not source_table_info or not target_table_info:
                continue

            # Determine which table is the 'one' side (contains the PK for the join)
            if source_table_info.table.key == rel.source.column:
                # source is the 'one' side
                right_table = source_table_name
                right_column = rel.source.column
                left_table = target_table_name
                left_column = rel.target.column
            elif target_table_info.table.key == rel.target.column:
                # target is the 'one' side
                right_table = target_table_name
                right_column = rel.target.column
                left_table = source_table_name
                left_column = rel.source.column
            else:
                # This is not a valid FK relationship for Snowflake's semantic model
                continue

            relationship = {
                "name": rel.name,
                "left_table": clean_name(left_table),
                "right_table": clean_name(right_table),
                "relationship_columns": [
                    {
                        "left_column": clean_name(left_column),
                        "right_column": clean_name(right_column)
                    }
                ],
                "join_type": "left_outer",
                "relationship_type": RelationshipType.MANY_TO_ONE.value
            }
            relationships_list.append(relationship)

        # Construct the final semantic_model dictionary
        semantic_model_output = {
            "name": "intugle_generated_model",
            "description": "Semantic model generated by Intugle",
            "tables": tables_list,
            "relationships": relationships_list
        }
        
        return semantic_model_output
