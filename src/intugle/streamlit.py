
from intugle.analysis.models import DataSet
from intugle.core import settings
from intugle.exporters import CSVExporter
from intugle.parser.manifest import ManifestLoader


class StreamlitApp:

    def __init__(self, project_base: str = settings.PROJECT_BASE):
        self.manifest_loader = ManifestLoader(project_base)
        self.manifest_loader.load()
        self.manifest = self.manifest_loader.manifest

        self.project_base = project_base

        self.load_all()

    def load_all(self):
        sources = self.manifest.sources
        for source in sources.values():
            table_name = source.table.name
            details = source.table.details
            DataSet(data=details, name=table_name)

    def export_analysis_to_csv(self):
        """Exports the analysis results to CSV files."""
        exporter = CSVExporter(self.manifest, self.project_base)
        exporter.export_all()
        print("Succesfulluy exported analysis results to CSV files.")

    
