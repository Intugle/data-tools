
from intugle.analysis.models import DataSet
from intugle.core import settings
from intugle.exporters import CSVExporter
from intugle.libs.smart_query_generator.models.models import FieldDetailsModel, LinkModel
from intugle.libs.smart_query_generator.utils.join import Join
from intugle.parser.manifest import ManifestLoader


class StreamlitApp:

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
        
        self.datasets: dict[str, DataSet] = {}

        self.load_all()

    def load_all(self):
        sources = self.manifest.sources
        for source in sources.values():
            table_name = source.table.name
            details = source.table.details
            dataset = DataSet(data=details, name=table_name)
            self.datasets[table_name] = dataset

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

    def get_links(self) -> list[LinkModel]:
        """Fetches the links from the manifest."""

        # get relationships from the manifest
        relationships = self.manifest.relationships
        links: list[LinkModel] = []

        # iterate through each relationship and create a LinkModel
        for relationship in relationships.values():
            links.append(relationship.link)
        return links

    def export_analysis_to_csv(self):
        """Exports the analysis results to CSV files."""
        exporter = CSVExporter(self.manifest, self.project_base)
        exporter.export_all()

    
