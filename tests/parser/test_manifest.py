from data_tools.core import settings
from data_tools.parser.manifest import ManifestLoader


def test_manifet():
    manifest_loader = ManifestLoader(settings.PROJECT_BASE)
    manifest_loader.load()

    assert manifest_loader.manifest is not None
