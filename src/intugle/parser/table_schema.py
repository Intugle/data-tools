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

        # Start with the CREATE TABLE statement
        schema = f"CREATE TABLE {table_detail.table.name} -- {table_detail.table.description}"

        # Iterate through the columns of the table and create the column definitions
        columns_statements = [
            f"\"{column.name}\" {column.type}, -- {column.description}" for column in table_detail.table.columns
        ]

        # join the column definitions into a single string
        column_schema = "\n".join(columns_statements)

        # Add the column definitions to the schema
        schema += "\n(" + column_schema + "\n);"

        return schema

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
