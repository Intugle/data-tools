import asyncio
import os

from typing import Any, Dict, List, Optional

import aiohttp


class DocsSearchService:
    """
    Service for searching Intugle's documentation.

    This class provides methods to list available documentation file paths
    and fetch their content from the GitHub repository using asynchronous HTTP requests.
    """

    BASE_URL: str = "https://raw.githubusercontent.com/Intugle/data-tools/main/docsite/docs/"
    API_URL: str = "https://api.github.com/repos/Intugle/data-tools/contents/docsite/docs"
    BLACKLISTED_ROUTES: List[str] = ["mcp-server.md", "vibe-coding.md"]

    def __init__(self) -> None:
        """
        Initializes the DocsSearchService and sets up the internal path cache.
        """
        self._doc_paths: Optional[List[str]] = None

    def _sanitize_path(self, path: str) -> Optional[str]:
        """
        Sanitize a relative documentation path to prevent path traversal attacks.

        This method checks for absolute paths, path traversal sequences ('..'),
        and enforces allowed file extensions (.md, .mdx).

        Args:
            path (str): The relative path to sanitize.

        Returns:
            Optional[str]: The sanitized path if valid and safe, otherwise None.
        """
        # Reject absolute paths immediately
        if os.path.isabs(path):
            return None

        # Normalize the path (removes //, etc.)
        normalized_path: str = os.path.normpath(path)

        # Ensure it does not traverse outside allowed directory or use backslashes
        if normalized_path.startswith("..") or "\\" in normalized_path:
            return None

        # Enforce allowed file extensions
        if not (normalized_path.endswith(".md") or normalized_path.endswith(".mdx")):
            return None

        return normalized_path

    async def list_doc_paths(self) -> List[str]:
        """
        Fetches and returns a list of all documentation file paths from the GitHub repository.

        The result is cached in self._doc_paths to avoid repeated GitHub API calls.
        Errors during fetching will return a list containing an error string.

        Returns:
            List[str]: A list of relative documentation paths (e.g., "intro.md").
        """
        if self._doc_paths is None:
            async with aiohttp.ClientSession() as session:
                self._doc_paths = await self._fetch_paths_recursively(session, self.API_URL)
        return self._doc_paths

    async def _fetch_paths_recursively(self, session: aiohttp.ClientSession, url: str) -> List[str]:
        """
        Recursively fetches file paths from the GitHub API content endpoint.

        Args:
            session (aiohttp.ClientSession): The active asynchronous HTTP session.
            url (str): The GitHub API URL for the directory content.

        Returns:
            List[str]: A list of relative paths found under the given URL, or a list
                       containing an error string if the fetch fails.
        """
        paths: List[str] = []
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return [f"Error: Could not fetch {url}, status code: {response.status}"]

                items: List[Dict[str, Any]] = await response.json()

                for item in items:
                    if item['type'] == 'file' and (item['name'].endswith('.md') or item['name'].endswith('.mdx')):
                        # Strip the docsite/docs/ prefix to get the relative path
                        relative_path: str = item['path'].replace('docsite/docs/', '', 1)
                        if relative_path not in self.BLACKLISTED_ROUTES:
                            paths.append(relative_path)
                    elif item['type'] == 'dir':
                        # Recursively fetch paths in subdirectories
                        paths.extend(await self._fetch_paths_recursively(session, item['url']))
        except Exception as e:
            return [f"Error: Exception while fetching {url}: {e}"]

        return paths

    async def search_docs(self, paths: List[str]) -> str:
        """
        Fetches and concatenates content from a list of documentation paths.

        This method concurrently fetches content for all provided paths and joins
        them with a separator. Invalid paths are filtered out.

        Args:
            paths (List[str]): A list of markdown file paths (e.g., ["intro.md", "core-concepts/semantic-model.md"]).

        Returns:
            str: The concatenated content of the documentation files, separated by "\n\n---\n\n".
                 Error messages for failed fetches are included in the concatenated string.
        """
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_doc(session, path) for path in paths]
            # Use asyncio.gather to run all fetch tasks concurrently
            results: List[Optional[str]] = await asyncio.gather(*tasks)
            # Filter(None, results) removes any None values returned by _fetch_doc
            return "\n\n---\n\n".join(filter(None, results))

    async def _fetch_doc(self, session: aiohttp.ClientSession, path: str) -> Optional[str]:
        """
        Fetches the content of a single documentation file from the GitHub raw URL.

        Args:
            session (aiohttp.ClientSession): The active asynchronous HTTP session.
            path (str): The requested documentation path, which is sanitized before use.

        Returns:The file content as a string if successful, or None
        """
        sanitized_path: Optional[str] = self._sanitize_path(path)
        if sanitized_path is None:
            # Return error string to be included in the search_docs result
            return f"Error: Invalid path {path}"

        url: str = f"{self.BASE_URL}{sanitized_path}"
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    return f"Error: Could not fetch {url}, status code: {response.status}"
        except Exception as e:
            return f"Error: Exception while fetching {url}: {e}"


docs_search_service = DocsSearchService()
