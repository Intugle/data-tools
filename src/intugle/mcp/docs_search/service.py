
import asyncio
import os

from typing import List

import aiohttp


class DocsSearchService:
    """
    Service for searching Intugle's documentation.
    """

    BASE_URL = "https://raw.githubusercontent.com/Intugle/data-tools/main/docsite/docs/"
    API_URL = "https://api.github.com/repos/Intugle/data-tools/contents/docsite/docs"
    BLACKLISTED_ROUTES = ["mcp-server.md", "vibe-coding.md"]

    def __init__(self):
        self._doc_paths = None

    def _sanitize_path(self, path: str) -> str | None:
        """
        Sanitizes a relative path to prevent path traversal attacks.
        Returns the original path if it's safe, otherwise None.
        """
    
        # Reject absolute paths immediately
        if os.path.isabs(path):
            return None
    
        # Normalize the path (removes ../, //, etc.)
        normalized_path = os.path.normpath(path)
    
        # Ensure it does not traverse outside allowed directory
        if normalized_path.startswith("..") or "\\" in normalized_path:
            return None
    
        # Optionally, you could enforce allowed file extensions
        if not (normalized_path.endswith(".md") or normalized_path.endswith(".mdx")):
            return None
    
        return normalized_path

    async def list_doc_paths(self) -> List[str]:
        """
        Fetches and returns a list of all documentation file paths from the GitHub repository.
        Caches the result to avoid repeated API calls.
        """
        if self._doc_paths is None:
            async with aiohttp.ClientSession() as session:
                self._doc_paths = await self._fetch_paths_recursively(session, self.API_URL)
        return self._doc_paths

    async def _fetch_paths_recursively(self, session: aiohttp.ClientSession, url: str) -> List[str]:
        """
        Recursively fetches file paths from the GitHub API.
        """
        paths = []
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    # Optionally log an error here
                    return [f"Error: Could not fetch {url}, status code: {response.status}"]
                
                items = await response.json()
                
                for item in items:
                    if item['type'] == 'file' and (item['name'].endswith('.md') or item['name'].endswith('.mdx')):
                        relative_path = item['path'].replace('docsite/docs/', '', 1)
                        if relative_path not in self.BLACKLISTED_ROUTES:
                            paths.append(relative_path)
                    elif item['type'] == 'dir':
                        paths.extend(await self._fetch_paths_recursively(session, item['url']))
        except Exception as e:
            # Optionally log the exception
            return [f"Error: Exception while fetching {url}: {e}"]
        
        return paths

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
        sanitized_path = self._sanitize_path(path)
        if sanitized_path is None:
            return f"Error: Invalid path {path}"
        
        url = f"{self.BASE_URL}{sanitized_path}"
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
