from intugle.core import settings
from intugle.core.llms.embeddings import Embeddings
from intugle.core.semantic_search.crud import SemanticSearchCRUD
from intugle.core.semantic_search.semantic_search import HybridDenseLateSearch
from intugle.parser.manifest import ManifestLoader


class SemanticSearch:
    def __init__(
        self, project_base: str = settings.PROJECT_BASE, collection_name: str = settings.VECTOR_COLLECTION_NAME
    ):
        self.manifest_loader = ManifestLoader(project_base)
        self.manifest_loader.load()
        self.manifest = self.manifest_loader.manifest
        self.collection_name = collection_name

        self.project_base = project_base

    def get_column_details(self):
        sources = self.manifest.sources
        models = self.manifest.models

        column_details = []
        for source in sources.values():
            table = source.table
            for column in table.columns:
                column_detail = {
                    "id": f"{table.name}.{column.name}",
                    "column_name": column.name,
                    "column_glossary": column.description,
                    "column_tags": column.tags,
                }
                column_details.append(column_detail)

        for model in models.values():
            for column in model.columns:
                column_detail = {
                    "id": f"{table.name}.{column.name}",
                    "column_name": column.name,
                    "column_glossary": column.description,
                    "column_tags": column.tags,
                }
                column_details.append(column_detail)

        return column_details

    async def initiaize(self):
        embeddings = Embeddings("azure_openai:ada")
        semantic_search_crud = SemanticSearchCRUD(self.collection_name, [embeddings])
        column_details = self.get_column_details()
        await semantic_search_crud.initialize(column_details)

    async def search(self, query):
        embeddings = Embeddings("azure_openai:ada")
        semantic_search = HybridDenseLateSearch(self.collection_name, embeddings)

        data = await semantic_search.search(query)
        return data
