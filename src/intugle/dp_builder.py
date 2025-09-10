from typing import TYPE_CHECKING

from intugle.analysis.models import DataSet
from intugle.core import settings
from intugle.libs.smart_query_generator import SmartQueryGenerator
from intugle.libs.smart_query_generator.models.models import ETLModel, FieldDetailsModel, LinkModel
from intugle.libs.smart_query_generator.utils.join import Join
from intugle.parser.manifest import ManifestLoader

if TYPE_CHECKING:
    from intugle.models.resources.model import Column


class DataProductBuilder:
    """Generates data products based on the manifest and ETL configurations."""

    def __init__(self, project_base: str = settings.PROJECT_BASE):
        self.manifest_loader = ManifestLoader(project_base)
        self.manifest_loader.load()
        self.manifest = self.manifest_loader.manifest

        self.project_base = project_base

        self.field_details = self.get_all_field_details()

        # get the links from the manifest
        self.links = self.get_links()

        selected_fields = set(self.field_details.keys())
        self.join = Join(self.links, selected_fields)

        self.load_all()

    def load_all(self):
        sources = self.manifest.sources
        for source in sources.values():
            table_name = source.table.name
            details = source.table.details
            DataSet(data=details, name=table_name)

    def generate_query(self, etl: ETLModel) -> str:
        """Generates a SQL query based on the ETL model.

        Args:
            etl (ETLModel): The ETL model containing the configuration for the query.

        Returns:
            str: The generated SQL query.
        """
        etl = ETLModel.model_validate(etl)

        # get the field details fetcher function (Not required now as we are getting all field details)
        # and all field details
        field_details_fetcher = self.get_field_details_fetcher()

        # Generate the SQL query using the SmartQueryGenerator
        sql_builder = SmartQueryGenerator(etl, field_details_fetcher, self.links, self.field_details)
        sql_builder.build()
        sql_query = sql_builder.get_query()
        return sql_query
        
    def build(self, etl: ETLModel) -> DataSet:
        """Generates a dataset on the ETL model.

        Args:
            etl (ETLModel): The ETL model containing the configuration for the query.

        Returns:
            Dataset: The dataset.
        """
        etl = ETLModel.model_validate(etl)

        sql_query = self.generate_query(etl)

        data = {
            "path": sql_query,
            "type": "query"
        }
        print(etl.name)
        dataset = DataSet(data, etl.name)
        return dataset

    def get_all_field_details(self) -> dict[str, FieldDetailsModel]:
        """Fetches all field details from the manifest."""

        # get sources from the manifest
        sources = self.manifest.sources

        field_details: dict[str, FieldDetailsModel] = {}

        # iterate through each source and get the field details (all fields / columns)
        for source in sources.values():
            for column in source.table.columns:
                field_detail: FieldDetailsModel = FieldDetailsModel(
                    id=f"{source.table.name}.{column.name}",
                    name=column.name,
                    datatype_l1=column.type,
                    datatype_l2=column.category,
                    sql_code=f"\"{source.table.name}\".\"{column.name}\"",
                    is_pii=False,
                    asset_id=source.table.name,
                    asset_name=source.table.name,
                    asset_details={},
                    connection_id=source.schema,
                    connection_source_name="postgresql",
                    connection_credentials={},
                )
                field_details[field_detail.id] = field_detail

        return field_details

    def get_field_details_fetcher(self):
        """Returns field details fetcher from the manifest."""

        manifest = self.manifest

        def field_details_fetcher(ids: list[str]):
            table_columns: dict[str, list[str]] = {}

            # get table and column names from the ids
            for field in ids:
                table, column = field.split(".")
                if table not in table_columns:
                    table_columns[table] = []
                table_columns[table].append(column)

            sources = manifest.sources

            field_details: dict[str, FieldDetailsModel] = {}

            # iterate through each table and column to get the field details
            for table, columns in table_columns.items():
                table_detail = sources.get(table)
                if table_detail is None:
                    continue

                column_details: dict[str, Column] = {}
                for column in table_detail.table.columns:
                    column_details[column.name] = column

                for column in columns:
                    column_detail = column_details[column]
                    field_detail: FieldDetailsModel = FieldDetailsModel(
                        id=f"{table}.{column}",
                        name=column_detail.name,
                        datatype_l1=column_detail.type,
                        datatype_l2=column_detail.category,
                        sql_code=f"\"{table}\".\"{column}\"",
                        is_pii=False,
                        asset_id=table,
                        asset_name=table,
                        asset_details={},
                        connection_id=table_detail.schema,
                        connection_source_name="postgresql",
                        connection_credentials={},
                    )
                    field_details[field_detail.id] = field_detail

            return field_details

        return field_details_fetcher

    def get_links(self) -> list[LinkModel]:
        """Fetches the links from the manifest."""

        # get relationships from the manifest
        relationships = self.manifest.relationships
        links: list[LinkModel] = []

        # iterate through each relationship and create a LinkModel
        for relationship in relationships.values():
            links.append(relationship.link)
        return links

    def plot_graph(self, graph):
        self.join.plot_graph(graph)

    def plot_sources_graph(self):
        assets = {field.asset_id for field in self.field_details.values()}

        graph = self.join.generate_graph(list(assets), only_connected=False)

        self.plot_graph(graph)
    
