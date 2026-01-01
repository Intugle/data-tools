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

        # 1. Fetch definitions using helper methods
        column_definitions = self._get_column_definitions(table_detail)
        fk_definitions = self._get_foreign_key_definitions(table_name)

        # 2. Assemble the final schema
        all_definitions = column_definitions + fk_definitions
        definitions_str = ",\n".join(all_definitions)

        schema_template = "CREATE TABLE {table_name} -- {table_comment}\n(\n{definitions}\n);"
        
        return schema_template.format(
            table_name=table_detail.table.name,
            table_comment=table_detail.table.description,
            definitions=definitions_str
        )

    def _get_column_definitions(self, table_detail) -> list[str]:
        """Helper method to generate column definition strings."""
        column_definitions = []
        for column in table_detail.table.columns:
            # Here we assume column.type is safe and doesn't come from user input.
            column_template = "    {column_name} {column_type} -- {column_comment}"
            column_params = {
                "column_name": column.name,
                "column_type": column.type,
                "column_comment": column.description,
            }
            column_definitions.append(column_template.format(**column_params))
        return column_definitions

    def _get_foreign_key_definitions(self, table_name: str) -> list[str]:
        """Helper method to generate foreign key constraint strings."""
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
        return fk_definitions

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