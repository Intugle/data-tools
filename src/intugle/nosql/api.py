from typing import Dict, Any, Optional
from intugle.nosql.source import NoSQLSource
from intugle.nosql.parser import NoSQLParser
from intugle.nosql.inference import infer_schema


class NoSQLToRelationalParser:
    """
    High-level orchestrator for converting NoSQL data to relational formats.
    """

    def __init__(self, source: NoSQLSource, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            source: A configured NoSQLSource (e.g., MongoSource)
            config: Configuration dict for table renaming, PK overrides, etc.
        """
        self.source = source
        self.config = config or {}
        self._parsed_tables: Optional[Dict[str, Any]] = None

    def infer_model(self) -> Dict[str, Any]:
        """
        Peeks at the source data to infer the schema and relationships.

        Returns:
            Dict containing the inferred schema structure.
        """
        # Fetch a sample from the source (iterator)
        # We assume the source handles sampling limits internally if configured
        sample_data = list(self.source.get_data())

        # Use our existing inference logic
        schema = infer_schema(sample_data)
        return schema

    def run(self) -> None:
        """
        Executes the full parsing pipeline: fetch -> parse.
        Stores results in memory (self._parsed_tables).
        """
        # Note: For V1, we load source data into memory.
        # Future optimization: Implement chunked streaming here.
        all_data = list(self.source.get_data())

        # Initialize the core parser with our config
        # (Assuming NoSQLParser accepts config in __init__ from Phase 5)
        parser = NoSQLParser(config=self.config)

        self._parsed_tables = parser.parse(all_data)

    def write(self, target: Any) -> None:
        """
        Writes the parsed tables to the specified target.

        Args:
            target: An instance of a Target (e.g., ParquetTarget)
        """
        if self._parsed_tables is None:
            # Auto-run if not already run
            self.run()

        target.write(self._parsed_tables)
