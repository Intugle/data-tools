from intugle.common.exception import errors
from intugle.models.manifest import Manifest


class TableSchema:
    """Class to generate and manage SQL table schemas based on a manifest."""

    def __init__(self, manifest: Manifest):
        """
        Initializes the TableSchema with a manifest.
        
        Args:
            manifest (Manifest): The manifest containing the details of the tables.
        """
        self.manifest = manifest
        self.table_schemas: dict[str, str] = {}

    def generate_table_schema(self, table_name: str) -> str:
        """Generate the SQL schema for a given table based on its details in the manifest.

        Args:
            table_name (str): The name of the table for which to generate the schema.

        Returns:
            str: The SQL schema definition for the table.
        """
        table_detail = self.manifest.sources.get(table_name)
        if not table_detail:
            raise errors.NotFoundError(f"Table {table_name} not found in manifest.")

        # 1. Define the SQL template with placeholders
        schema_template = "CREATE TABLE {table_name} -- {table_comment}\n(\n{definitions}\n);"

        # 2. Sanitize all dynamic parts that will go into the template
        params = {
            "table_name": table_detail.table.name,
            "table_comment": table_detail.table.description,
        }

        # Sanitize each column definition separately
        column_definitions = []
        for column in table_detail.table.columns:
            # Here we assume column.type is safe and doesn't come from user input.
            # If it can be user-defined, it needs its own validation.
            column_template = "    {column_name} {column_type} -- {column_comment}"
            column_params = {
                "column_name": column.name,
                "column_type": column.type,
                "column_comment": column.description,
            }
            column_definitions.append(column_template.format(**column_params))

        # Add foreign key constraints
        fk_definitions = []
        for relationship in self.manifest.relationships.values():
            if relationship.source.table == table_name:
                fk_template = "    FOREIGN KEY ({from_column}) REFERENCES {to_table}({to_column})"
                fk_params = {
                    "from_column": ','.join(relationship.source.columns),
                    "to_table": relationship.target.table,
                    "to_column": ','.join(relationship.target.columns),
                }
                fk_definitions.append(fk_template.format(**fk_params))

        # Join all definitions with a comma
        all_definitions = column_definitions + fk_definitions
        params["definitions"] = ",\n".join(all_definitions)

        # 3. Format the final schema string with the sanitized parameters
        return schema_template.format(**params)

    def get_table_schema(self, table_name: str):
        """Get the SQL schema for a specified table, generating it if not already cached.

        Args:
            table_name (str): The name of the table for which to retrieve the schema.

        Returns:
            str: The SQL schema definition for the table.
        """
        table_schema = self.table_schemas.get(table_name)

        if table_schema is None:
            table_schema = self.generate_table_schema(table_name)
            self.table_schemas[table_name] = table_schema

        return table_schema
    

    
