
from intugle.core import settings
from intugle.parser.manifest import ManifestLoader

manifest_loader = ManifestLoader(settings.MODELS_DIR)
manifest_loader.load()

