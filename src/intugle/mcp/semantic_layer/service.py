from intugle.common.exception import errors
from intugle.mcp.manifest import manifest_loader

# from intugle.core import settings
# from intugle.parser.manifest import ManifestLoader
from intugle.parser.table_schema import TableSchema


class SemanticLayerService:
    def __init__(self):
        # manifest_loader = ManifestLoader(settings.PROJECT_BASE)
        # manifest_loader.load()
        self.manifest = manifest_loader.manifest

        self.table_schema = TableSchema(self.manifest)

    def get_tables(self) -> list[dict]:
        """
        Fetches all the tables and their technical description for a subscription.

        Returns:
            list[dict]: List of tables along with their technical description.
        """
        sources = self.manifest.sources

        tables = []
        for source in sources.values():
            table_info = {
                "table_name": source.table.name,
                "table_description": source.table.description,
            }
            tables.append(table_info)

        return tables

    def get_schema(self, tables: list[str]) -> dict[str, str]:
        """
        Fetches the schema along with some sample rows for given database table names.

        Args:
            tables (dict[str, str]): List of table names to fetch the schema.

        Raises:
            Exception: If the table names are not found in the manifest.
        """
        schemas = {}

        for table in tables:
            try:
                schema = self.table_schema.get_table_schema(table)
                schemas[table] = schema
            except errors.NotFoundError:
                ...
        
        return schemas


semantic_layer_service = SemanticLayerService()
