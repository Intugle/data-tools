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

    def _get_column_definitions(self, table_detail) -> list[str]:
        """Generate SQL column definitions for a table.

        Args:
            table_detail: The table detail object from the manifest.

        Returns:
            list[str]: A list of formatted column definition strings.
        """
        column_definitions = []
        for column in table_detail.table.columns:
            column_template = "    {column_name} {column_type} -- {column_comment}"
            column_params = {
                "column_name": column.name,
                "column_type": column.type,
                "column_comment": column.description,
            }
            column_definitions.append(column_template.format(**column_params))
        return column_definitions

    def _get_foreign_key_definitions(self, table_name: str) -> list[str]:
        """Generate SQL foreign key constraint definitions for a table.

        Args:
            table_name (str): The name of the table to get foreign keys for.

        Returns:
            list[str]: A list of formatted foreign key constraint strings.
        """
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

    def _assemble_schema_sql(self, table_detail, column_definitions: list[str], fk_definitions: list[str]) -> str:
        """Assemble the final SQL CREATE TABLE statement.

        Args:
            table_detail: The table detail object from the manifest.
            column_definitions (list[str]): List of column definition strings.
            fk_definitions (list[str]): List of foreign key constraint strings.

        Returns:
            str: The complete SQL CREATE TABLE statement.
        """
        schema_template = "CREATE TABLE {table_name} -- {table_comment}\n(\n{definitions}\n);"
        
        params = {
            "table_name": table_detail.table.name,
            "table_comment": table_detail.table.description,
        }
        
        all_definitions = column_definitions + fk_definitions
        params["definitions"] = ",\n".join(all_definitions)
        
        return schema_template.format(**params)

    def generate_table_schema(self, table_name: str) -> str:
        """Generate the SQL schema for a given table based on its details in the manifest.

        Args:
            table_name (str): The name of the table for which to generate the schema.

        Returns:
            str: The SQL schema definition for the table.

        Raises:
            NotFoundError: If the table is not found in the manifest.
        """
        table_detail = self.manifest.sources.get(table_name)
        if not table_detail:
            raise errors.NotFoundError(f"Table {table_name} not found in manifest.")

        column_definitions = self._get_column_definitions(table_detail)
        fk_definitions = self._get_foreign_key_definitions(table_name)
        
        return self._assemble_schema_sql(table_detail, column_definitions, fk_definitions)

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
    

    
