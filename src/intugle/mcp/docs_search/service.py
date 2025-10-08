
import asyncio
import aiohttp
from typing import List

class DocsSearchService:
    """
    Service for searching Intugle's documentation.
    """

    BASE_URL = "https://raw.githubusercontent.com/Intugle/data-tools/main/docsite/docs/"

    async def search_docs(self, paths: List[str]) -> str:
        """
        Fetches and concatenates content from a list of documentation paths.

        Args:
            paths (List[str]): A list of markdown file paths (e.g., ["intro.md", "core-concepts/semantic-model.md"])

        Returns:
            str: The concatenated content of the documentation files.
        """
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_doc(session, path) for path in paths]
            results = await asyncio.gather(*tasks)
            return "\n\n---\n\n".join(filter(None, results))

    async def _fetch_doc(self, session: aiohttp.ClientSession, path: str) -> str | None:
        """
        Fetches a single documentation file.
        """
        url = f"{self.BASE_URL}{path}"
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    # Optionally log an error here
                    return f"Error: Could not fetch {url}, status code: {response.status}"
        except Exception as e:
            # Optionally log the exception
            return f"Error: Exception while fetching {url}: {e}"

docs_search_service = DocsSearchService()
