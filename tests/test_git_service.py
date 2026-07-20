"""
Unit tests for GitService.

Uses unittest.mock to patch PyGithub calls — no real network needed.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import MagicMock, patch


class TestGitServiceInit:
    """Tests for GitService initialization and authentication."""

    @patch("services.git_connection.Github")
    @patch("services.git_connection.Auth.Token")
    def test_connect_called_on_init(self, mock_auth_token, mock_github):
        """Should authenticate immediately on instantiation."""
        from services.git_connection import GitService

        service = GitService(token="ghp_faketoken")

        mock_auth_token.assert_called_once_with("ghp_faketoken")
        mock_github.assert_called_once()
        assert service._client is not None

    @patch("services.git_connection.Github")
    @patch("services.git_connection.Auth.Token")
    def test_close_sets_client_none(self, mock_auth_token, mock_github):
        """close() should disconnect and set _client to None."""
        from services.git_connection import GitService

        service = GitService(token="ghp_faketoken")
        service.close()

        assert service._client is None


class TestGitServiceGetRepos:
    """Tests for GitService.get_repos() and get_repo_names()."""

    def _make_service(self):
        """Returns a GitService with a mocked Github client."""
        with patch("services.git_connection.Github"), patch("services.git_connection.Auth.Token"):
            from services.git_connection import GitService
            service = GitService(token="ghp_faketoken")

        mock_repo_1 = MagicMock()
        mock_repo_1.name = "game-assets"
        mock_repo_2 = MagicMock()
        mock_repo_2.name = "engine-core"

        mock_client = MagicMock()
        mock_client.get_user.return_value.get_repos.return_value = [mock_repo_1, mock_repo_2]
        service._client = mock_client

        return service

    def test_get_repos_returns_list(self):
        """Should return a list of repository objects."""
        service = self._make_service()
        repos = service.get_repos()
        assert isinstance(repos, list)
        assert len(repos) == 2

    def test_get_repo_names_returns_strings(self):
        """get_repo_names() should return a list of name strings."""
        service = self._make_service()
        names = service.get_repo_names()
        assert names == ["game-assets", "engine-core"]

    def test_get_repos_raises_when_not_connected(self):
        """Should raise RuntimeError when _client is None."""
        with patch("services.git_connection.Github"), patch("services.git_connection.Auth.Token"):
            from services.git_connection import GitService
            service = GitService(token="ghp_faketoken")

        service._client = None
        with pytest.raises(RuntimeError, match="not authenticated"):
            service.get_repos()


class TestGitServiceContextManager:
    """Tests for GitService used as a context manager."""

    @patch("services.git_connection.Github")
    @patch("services.git_connection.Auth.Token")
    def test_context_manager_closes_on_exit(self, mock_auth_token, mock_github):
        """with statement should call close() on exit."""
        from services.git_connection import GitService

        with GitService(token="ghp_faketoken") as service:
            assert service._client is not None

        assert service._client is None
