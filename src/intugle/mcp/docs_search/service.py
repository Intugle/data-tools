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

    async def _get_github_api_items(self, session: aiohttp.ClientSession, url: str) -> List[dict]:
        """
        Fetches items from the GitHub API.

        Args:
            session (aiohttp.ClientSession): The HTTP session to use for the request.
            url (str): The GitHub API URL to fetch items from.

        Returns:
            List[dict]: A list of items from the GitHub API response.

        Raises:
            RuntimeError: If the API request fails or returns a non-200 status code.
        """
        async with session.get(url) as response:
            if response.status != 200:
                raise RuntimeError(f"Could not fetch {url}, status code: {response.status}")
            return await response.json()

    def _is_valid_markdown_file(self, item: dict) -> bool:
        """
        Checks if an item is a valid markdown file that should be included.

        Args:
            item (dict): A GitHub API item dictionary.

        Returns:
            bool: True if the item is a valid markdown file not in blacklist, False otherwise.
        """
        if item['type'] != 'file':
            return False
        
        if not (item['name'].endswith('.md') or item['name'].endswith('.mdx')):
            return False
        
        relative_path = item['path'].replace('docsite/docs/', '', 1)
        return relative_path not in self.BLACKLISTED_ROUTES

    def _extract_relative_path(self, item: dict) -> str:
        """
        Extracts the relative path from a GitHub API item.

        Args:
            item (dict): A GitHub API item dictionary.

        Returns:
            str: The relative path with 'docsite/docs/' prefix removed.
        """
        return item['path'].replace('docsite/docs/', '', 1)

    async def _process_github_item(self, session: aiohttp.ClientSession, item: dict) -> List[str]:
        """
        Processes a single GitHub API item (file or directory).

        Args:
            session (aiohttp.ClientSession): The HTTP session to use for recursive requests.
            item (dict): A GitHub API item dictionary.

        Returns:
            List[str]: A list of file paths. Returns a single-item list for files,
                      or recursively fetched paths for directories.
        """
        if self._is_valid_markdown_file(item):
            return [self._extract_relative_path(item)]
        elif item['type'] == 'dir':
            return await self._fetch_paths_recursively(session, item['url'])
        return []

    async def _fetch_paths_recursively(self, session: aiohttp.ClientSession, url: str) -> List[str]:
        """
        Recursively fetches file paths from the GitHub API.

        Args:
            session (aiohttp.ClientSession): The HTTP session to use for the request.
            url (str): The GitHub API URL to fetch paths from.

        Returns:
            List[str]: A list of relative documentation file paths, or error messages if the request fails.
        """
        try:
            items = await self._get_github_api_items(session, url)
            paths = []
            for item in items:
                paths.extend(await self._process_github_item(session, item))
            return paths
        except Exception as e:
            return [f"Error: Exception while fetching {url}: {e}"]

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
            results: List[str] = await asyncio.gather(*tasks)
            # Join the results with the separator; filter(None, results) handles any empty strings
            return "\n\n---\n\n".join(filter(None, results))

    async def _fetch_doc(self, session: aiohttp.ClientSession, path: str) -> str:
        """
        Fetches the content of a single documentation file from the GitHub raw URL.

        Args:
            session (aiohttp.ClientSession): The active asynchronous HTTP session.
            path (str): The requested documentation path, which is sanitized before use.

        Returns:
            str: The file content as a string if successful, or an error message string if it fails.
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
