"""
Unit tests for DriveService.

These tests use unittest.mock to patch Google API calls so no real
network connection or credentials are needed.
"""
import pytest
import sys
import os

# Make src importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import MagicMock, patch, mock_open


class TestDriveServiceAuthentication:
    """Tests for DriveService.authenticate()."""

    @patch("services.drive.os.path.exists", return_value=True)
    @patch("services.drive.Credentials.from_authorized_user_file")
    @patch("services.drive.build")
    def test_authenticate_loads_existing_token(self, mock_build, mock_creds_from_file, mock_exists):
        """Should load credentials from token.json when it exists and is valid."""
        from services.drive import DriveService

        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds_from_file.return_value = mock_creds

        service = DriveService()
        result = service.authenticate()

        assert result is True
        assert service.is_authenticated is True
        mock_creds_from_file.assert_called_once()
        mock_build.assert_called_once_with("drive", "v3", credentials=mock_creds)

    @patch("services.drive.os.path.exists", return_value=False)
    @patch("services.drive.InstalledAppFlow.from_client_secrets_file")
    @patch("services.drive.build")
    def test_authenticate_launches_oauth_when_no_token(self, mock_build, mock_flow_cls, mock_exists):
        """Should launch OAuth flow when token.json does not exist."""
        from services.drive import DriveService

        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.to_json.return_value = "{}"

        mock_flow = MagicMock()
        mock_flow.run_local_server.return_value = mock_creds
        mock_flow_cls.return_value = mock_flow

        with patch("builtins.open", mock_open()):
            service = DriveService()
            result = service.authenticate()

        assert result is True
        mock_flow.run_local_server.assert_called_once_with(port=0)


class TestDriveServiceListFiles:
    """Tests for DriveService.list_files()."""

    def _make_authenticated_service(self):
        """Helper: returns a DriveService with a mocked internal _service."""
        from services.drive import DriveService
        svc = DriveService()
        svc._creds = MagicMock(valid=True)
        svc._service = MagicMock()
        return svc

    def test_list_files_returns_list(self):
        """Should return a list of file dicts."""
        svc = self._make_authenticated_service()
        fake_files = [
            {"id": "1", "name": "asset.png", "mimeType": "image/png", "size": "1024", "modifiedTime": "2024-01-01"},
        ]
        svc._service.files.return_value.list.return_value.execute.return_value = {
            "files": fake_files
        }

        result = svc.list_files()
        assert result == fake_files

    def test_list_files_returns_empty_list_when_none(self):
        """Should return an empty list when Drive has no files."""
        svc = self._make_authenticated_service()
        svc._service.files.return_value.list.return_value.execute.return_value = {}
        result = svc.list_files()
        assert result == []

    def test_list_files_raises_when_not_authenticated(self):
        """Should raise RuntimeError if called before authenticate()."""
        from services.drive import DriveService
        svc = DriveService()
        with pytest.raises(RuntimeError, match="not authenticated"):
            svc.list_files()


class TestDriveServiceUpload:
    """Tests for DriveService.upload_file()."""

    def _make_authenticated_service(self):
        from services.drive import DriveService
        svc = DriveService()
        svc._creds = MagicMock(valid=True)
        svc._service = MagicMock()
        return svc

    def test_upload_raises_when_file_not_found(self):
        """Should raise FileNotFoundError for a non-existent path."""
        svc = self._make_authenticated_service()
        with pytest.raises(FileNotFoundError):
            svc.upload_file("/nonexistent/path/file.txt")

    @patch("services.drive.os.path.exists", return_value=True)
    @patch("services.drive.MediaFileUpload")
    def test_upload_returns_file_id(self, mock_media, mock_exists):
        """Should return the Drive file ID on successful upload."""
        svc = self._make_authenticated_service()
        svc._service.files.return_value.create.return_value.execute.return_value = {"id": "abc123"}

        file_id = svc.upload_file("/fake/asset.png")
        assert file_id == "abc123"
