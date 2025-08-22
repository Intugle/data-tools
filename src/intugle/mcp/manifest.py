
from intugle.core import settings
from intugle.parser.manifest import ManifestLoader

manifest_loader = ManifestLoader(settings.PROJECT_BASE)
manifest_loader.load()

