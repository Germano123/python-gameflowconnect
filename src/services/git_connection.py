"""
GitService — Encapsulates all GitHub API interactions.

Usage:
    service = GitService(token="your_token")
    repos = service.get_repos()
"""
from github import Github, Auth
from github.Repository import Repository
from typing import Optional


class GitService:
    """
    Manages authentication and operations with the GitHub API.

    Args:
        token (str): A GitHub Personal Access Token (PAT).
    """
    def __init__(self, token: str):
        self._token = token
        self._client: Optional[Github] = None
        self._connect()

    def _connect(self) -> None:
        """Authenticates with the GitHub API using the provided token."""
        auth = Auth.Token(self._token)
        self._client = Github(auth=auth)

    def get_repos(self) -> list[Repository]:
        """
        Returns a list of repositories accessible by the authenticated user.

        Returns:
            list[Repository]: A list of GitHub repository objects.

        Raises:
            RuntimeError: If the client is not authenticated.
        """
        if not self._client:
            raise RuntimeError("GitService is not authenticated.")
        return list(self._client.get_user().get_repos())

    def get_repo_names(self) -> list[str]:
        """
        Returns a list of repository names for the authenticated user.

        Returns:
            list[str]: Repository names.
        """
        return [repo.name for repo in self.get_repos()]

    def close(self) -> None:
        """Closes the GitHub API connection."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
