from data_tools.parser.manifest import ManifestLoader

PROJECT_BASE = "/home/juhel-phanju/Documents/backup/MIGRATION/codes/poc/dbt/ecom/ecom/models"


def test_manifet():
    manifest_loader = ManifestLoader(PROJECT_BASE)
    manifest_loader.load()

    assert manifest_loader.manifest is not None
