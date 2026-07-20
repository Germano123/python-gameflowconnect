"""
DriveService — Encapsulates all Google Drive API interactions.

Usage:
    service = DriveService()
    service.authenticate()
    files = service.list_files()
    file_id = service.upload_file("path/to/asset.png")
"""
import os
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# Full Drive scope — if modifying, delete token.json.
SCOPES = ["https://www.googleapis.com/auth/drive"]

TOKEN_PATH = "token.json"
CREDENTIALS_PATH = "credentials.json"


class DriveService:
    """
    Manages authentication and file operations with Google Drive API v3.
    """
    def __init__(self):
        self._creds: Optional[Credentials] = None
        self._service = None

    # ------------------------------------------------------------------ #
    # Authentication
    # ------------------------------------------------------------------ #

    def authenticate(self) -> bool:
        """
        Authenticates the user via OAuth2.

        Loads existing credentials from `token.json` if available,
        refreshes them if expired, or launches the OAuth consent flow.

        Returns:
            bool: True if authentication was successful.
        """
        creds = None
        if os.path.exists(TOKEN_PATH):
            try:
                creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
            except Exception:
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    # If invalid_grant or token expired/revoked, remove stale token.json and reset
                    if os.path.exists(TOKEN_PATH):
                        try:
                            os.remove(TOKEN_PATH)
                        except OSError:
                            pass
                    creds = None

            if not creds:
                if not os.path.exists(CREDENTIALS_PATH):
                    raise FileNotFoundError(
                        f"Arquivo de credenciais OAuth não encontrado: '{CREDENTIALS_PATH}'. "
                        "Copie o arquivo credentials.json baixado do Google Cloud Console para a raiz do projeto."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_PATH, SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(TOKEN_PATH, "w") as token:
                token.write(creds.to_json())

        self._creds = creds
        self._service = build("drive", "v3", credentials=self._creds)
        return True


    @property
    def is_authenticated(self) -> bool:
        """Returns True if the service has valid credentials."""
        return self._creds is not None and self._creds.valid

    # ------------------------------------------------------------------ #
    # File Operations
    # ------------------------------------------------------------------ #

    def list_files(self, page_size: int = 20) -> list[dict]:
        """
        Lists files in the user's Google Drive.

        Args:
            page_size (int): Maximum number of files to return.

        Returns:
            list[dict]: A list of dicts with 'id', 'name', 'mimeType', 'size'.

        Raises:
            RuntimeError: If not authenticated.
            HttpError: On API failure.
        """
        self._require_auth()
        try:
            results = (
                self._service.files()
                .list(
                    pageSize=page_size,
                    fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)",
                )
                .execute()
            )
            return results.get("files", [])
        except HttpError as error:
            raise HttpError(
                resp=error.resp,
                content=error.content,
                uri=f"list_files — {error.uri}",
            )

    def upload_file(self, local_path: str, drive_folder_id: Optional[str] = None) -> str:
        """
        Uploads a local file to Google Drive.

        Args:
            local_path (str): The absolute or relative path to the file to upload.
            drive_folder_id (str, optional): The ID of the Drive folder to upload into.

        Returns:
            str: The file ID of the uploaded file.

        Raises:
            FileNotFoundError: If `local_path` does not exist.
            RuntimeError: If not authenticated.
            HttpError: On API failure.
        """
        self._require_auth()
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"File not found: {local_path}")

        file_name = os.path.basename(local_path)
        file_metadata = {"name": file_name}
        if drive_folder_id:
            file_metadata["parents"] = [drive_folder_id]

        try:
            media = MediaFileUpload(local_path, mimetype="*/*", resumable=True)
            file = (
                self._service.files()
                .create(body=file_metadata, media_body=media, fields="id")
                .execute()
            )
            return file.get("id")
        except HttpError as error:
            raise HttpError(
                resp=error.resp,
                content=error.content,
                uri=f"upload_file({local_path}) — {error.uri}",
            )

    def download_file(self, file_id: str, destination_path: str) -> str:
        """
        Downloads a file from Google Drive.

        Args:
            file_id (str): The Drive file ID to download.
            destination_path (str): Local path to save the downloaded file.

        Returns:
            str: The destination path where the file was saved.

        Raises:
            RuntimeError: If not authenticated.
            HttpError: On API failure.
        """
        self._require_auth()
        try:
            request = self._service.files().get_media(fileId=file_id)
            with open(destination_path, "wb") as f:
                f.write(request.execute())
            return destination_path
        except HttpError as error:
            raise HttpError(
                resp=error.resp,
                content=error.content,
                uri=f"download_file({file_id}) — {error.uri}",
            )

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _require_auth(self) -> None:
        """Raises RuntimeError if the service is not authenticated."""
        if not self._service:
            raise RuntimeError(
                "DriveService is not authenticated. Call authenticate() first."
            )
