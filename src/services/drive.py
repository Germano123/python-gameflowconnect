"""
DriveService — Encapsulates all Google Drive API interactions.
"""
import os
import json
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaInMemoryUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]

TOKEN_PATH = os.path.join("data", "token.json")
CREDENTIALS_PATH = os.path.join("data", "credentials.json")



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

            os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
            with open(TOKEN_PATH, "w") as token:
                token.write(creds.to_json())


        self._creds = creds
        self._service = build("drive", "v3", credentials=self._creds)
        return True

    @property
    def is_authenticated(self) -> bool:
        return self._creds is not None and self._creds.valid

    # ------------------------------------------------------------------ #
    # File Operations
    # ------------------------------------------------------------------ #

    def list_files(self, page_size: int = 20) -> list[dict]:
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
    # Shared Project & Folder Management (Decentralized Sync)
    # ------------------------------------------------------------------ #

    def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> str:
        self._require_auth()
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        if parent_folder_id:
            file_metadata["parents"] = [parent_folder_id]

        file = self._service.files().create(body=file_metadata, fields="id").execute()
        return file.get("id")

    def share_folder(self, folder_id: str, email: str, role: str = "writer") -> dict:
        self._require_auth()
        user_permission = {
            "type": "user",
            "role": role,
            "emailAddress": email
        }
        return self._service.permissions().create(
            fileId=folder_id,
            body=user_permission,
            fields="id"
        ).execute()

    def search_shared_projects(self) -> list[dict]:
        """
        Searches for shared folders that contain 'project_metadata.json' shared with the user.
        """
        self._require_auth()
        query = "name = 'project_metadata.json' and sharedWithMe = true"
        results = self._service.files().list(q=query, fields="files(id, name, parents)").execute()
        return results.get("files", [])

    def read_json_file(self, file_id: str) -> dict:
        self._require_auth()
        request = self._service.files().get_media(fileId=file_id)
        content_bytes = request.execute()
        return json.loads(content_bytes.decode("utf-8"))

    def write_json_file(self, folder_id: str, filename: str, content: dict, file_id: Optional[str] = None) -> str:
        self._require_auth()
        media = MediaInMemoryUpload(
            json.dumps(content, indent=2).encode("utf-8"),
            mimetype="application/json"
        )
        if file_id:
            self._service.files().update(
                fileId=file_id,
                media_body=media,
                fields="id"
            ).execute()
            return file_id
        else:
            file_metadata = {
                "name": filename,
                "parents": [folder_id]
            }
            file = self._service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id"
            ).execute()
            return file.get("id")

    def find_file_in_folder(self, folder_id: str, filename: str) -> Optional[str]:
        self._require_auth()
        query = f"'{folder_id}' in parents and name = '{filename}' and trashed = false"
        results = self._service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get("files", [])
        return files[0].get("id") if files else None

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _require_auth(self) -> None:
        if not self._service:
            raise RuntimeError(
                "DriveService is not authenticated. Call authenticate() first."
            )
