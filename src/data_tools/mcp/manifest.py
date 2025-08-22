
from data_tools.core import settings
from data_tools.parser.manifest import ManifestLoader

manifest_loader = ManifestLoader(settings.PROJECT_BASE)
manifest_loader.load()

