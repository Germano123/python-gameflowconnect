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

def get_data_filepath(filename: str) -> str:
    import sys
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, filename)

TOKEN_PATH = get_data_filepath("token.json")
CREDENTIALS_PATH = get_data_filepath("credentials.json")




class DriveService:
    """
    Manages authentication and file operations with Google Drive API v3.
    """
    def __init__(self):
        self._creds: Optional[Credentials] = None
        self._service = None

    def _load_env_file(self) -> None:
        import sys
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            
        env_path = os.path.join(base_dir, ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            key, val = line.split("=", 1)
                            val = val.strip().strip('"').strip("'")
                            os.environ[key.strip()] = val
            except Exception as e:
                print(f"Erro ao carregar arquivo .env: {e}")

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
                # 1. Tentar carregar credenciais do .env local (desenvolvimento)
                self._load_env_file()
                
                client_id = os.environ.get("GOOGLE_CLIENT_ID")
                project_id = os.environ.get("GOOGLE_PROJECT_ID")
                client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
                auth_uri = os.environ.get("GOOGLE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth")
                token_uri = os.environ.get("GOOGLE_TOKEN_URI", "https://oauth2.googleapis.com/token")
                auth_provider_cert_url = os.environ.get("GOOGLE_AUTH_PROVIDER_CERT_URL", "https://www.googleapis.com/oauth2/v1/certs")
                redirect_uris = os.environ.get("GOOGLE_REDIRECT_URIS", "http://localhost").split(",")

                # 2. Se nao estiverem no ambiente, carregar as credenciais embutidas compiladas (producao)
                if not client_id or not client_secret:
                    try:
                        from services.config import get_credentials
                        baked = get_credentials()
                        client_id = baked.get("client_id")
                        project_id = baked.get("project_id")
                        client_secret = baked.get("client_secret")
                        auth_uri = baked.get("auth_uri", auth_uri)
                        token_uri = baked.get("token_uri", token_uri)
                        auth_provider_cert_url = baked.get("auth_provider_cert_url", auth_provider_cert_url)
                        redirect_uris = baked.get("redirect_uris", redirect_uris)
                    except ImportError:
                        pass

                # 3. Se ainda assim nao houver credenciais, falhar
                if not client_id or not client_secret:
                    raise ValueError(
                        "Credenciais do Google Drive nao encontradas! "
                        "Em desenvolvimento, configure GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET no arquivo .env. "
                        "Em producao, certifique-se de compilar utilizando o script build_exe.py."
                    )

                client_config = {
                    "installed": {
                        "client_id": client_id,
                        "project_id": project_id,
                        "auth_uri": auth_uri,
                        "token_uri": token_uri,
                        "auth_provider_x509_cert_url": auth_provider_cert_url,
                        "client_secret": client_secret,
                        "redirect_uris": redirect_uris
                    }
                }
                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
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

    def _get_http(self):
        from google_auth_httplib2 import AuthorizedHttp
        import httplib2
        return AuthorizedHttp(self._creds, http=httplib2.Http())

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
                .execute(http=self._get_http())
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
                .execute(http=self._get_http())
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
                f.write(request.execute(http=self._get_http()))
            return destination_path
        except HttpError as error:
            raise HttpError(
                resp=error.resp,
                content=error.content,
                uri=f"download_file({file_id}) — {error.uri}",
            )

    def get_or_create_root_folder(self, folder_name: str = "GameFlow.app") -> str:
        self._require_auth()
        query = f"'root' in parents and name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = self._service.files().list(q=query, fields="files(id)").execute(http=self._get_http())
        files = results.get("files", [])
        if files:
            return files[0].get("id")
        return self.create_folder(folder_name, parent_folder_id="root")

    def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> str:
        self._require_auth()
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        if parent_folder_id:
            file_metadata["parents"] = [parent_folder_id]

        file = self._service.files().create(body=file_metadata, fields="id").execute(http=self._get_http())
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
        ).execute(http=self._get_http())

    def search_shared_projects(self) -> list[dict]:
        """
        Searches for shared folders that contain 'manifest.json' shared with the user.
        """
        self._require_auth()
        query = "name = 'manifest.json' and trashed = false"
        results = self._service.files().list(q=query, fields="files(id, name, parents)").execute(http=self._get_http())
        return results.get("files", [])



    def read_json_file(self, file_id: str) -> dict:
        self._require_auth()
        request = self._service.files().get_media(fileId=file_id)
        content_bytes = request.execute(http=self._get_http())
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
            ).execute(http=self._get_http())
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
            ).execute(http=self._get_http())
            return file.get("id")

    def find_file_in_folder(self, folder_id: str, filename: str) -> Optional[str]:
        self._require_auth()
        query = f"'{folder_id}' in parents and name = '{filename}' and trashed = false"
        results = self._service.files().list(q=query, fields="files(id, name)").execute(http=self._get_http())
        files = results.get("files", [])
        return files[0].get("id") if files else None

    def check_folder_exists(self, folder_id: str) -> bool:
        self._require_auth()
        try:
            folder = self._service.files().get(fileId=folder_id, fields="id, trashed").execute(http=self._get_http())
            return not folder.get("trashed", False)
        except Exception:
            return False

    def _get_or_create_registry_folder(self) -> str:
        root_id = self.get_or_create_root_folder("GameFlow.app")
        gameflow_folder_id = self.find_file_in_folder(root_id, ".gameflow")
        if not gameflow_folder_id:
            gameflow_folder_id = self.create_folder(".gameflow", parent_folder_id=root_id)
        return gameflow_folder_id

    def read_gameflow_registry(self) -> dict:
        self._require_auth()
        try:
            registry_folder_id = self._get_or_create_registry_folder()
            file_id = self.find_file_in_folder(registry_folder_id, "gameflow.json")
            if file_id:
                return self.read_json_file(file_id)
        except Exception as e:
            print(f"Erro ao ler registro gameflow.json: {e}")
        return {"version": "1.0.0", "workspaces": []}

    def write_gameflow_registry(self, registry: dict) -> None:
        self._require_auth()
        try:
            registry_folder_id = self._get_or_create_registry_folder()
            file_id = self.find_file_in_folder(registry_folder_id, "gameflow.json")
            registry["version"] = "1.0.0"
            from datetime import datetime
            registry["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.write_json_file(registry_folder_id, "gameflow.json", registry, file_id=file_id)
        except Exception as e:
            print(f"Erro ao escrever no registro gameflow.json: {e}")

    def add_workspace_to_registry(self, ws_id: str, name: str, folder_id: str) -> None:
        self._require_auth()
        try:
            registry = self.read_gameflow_registry()
            workspaces = registry.setdefault("workspaces", [])
            if not any(w.get("id") == ws_id for w in workspaces):
                from datetime import datetime
                workspaces.append({
                    "id": ws_id,
                    "name": name,
                    "drive_folder_id": folder_id,
                    "owner": self.get_user_email(),
                    "created_at": datetime.now().strftime("%Y-%m-%d")
                })
                self.write_gameflow_registry(registry)
        except Exception as e:
            print(f"Erro ao adicionar workspace ao registro: {e}")

    def remove_workspace_from_registry(self, ws_id: str) -> None:
        self._require_auth()
        try:
            registry = self.read_gameflow_registry()
            workspaces = registry.get("workspaces", [])
            filtered = [w for w in workspaces if w.get("id") != ws_id]
            if len(filtered) != len(workspaces):
                registry["workspaces"] = filtered
                self.write_gameflow_registry(registry)
        except Exception as e:
            print(f"Erro ao remover workspace do registro: {e}")

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _require_auth(self) -> None:
        if not self._service:
            raise RuntimeError(
                "DriveService is not authenticated. Call authenticate() first."
            )

    def get_user_email(self) -> str:
        """
        Retorna o e-mail do usuário autenticado no Google Drive.
        """
        self._require_auth()
        try:
            about = self._service.about().get(fields="user(emailAddress)").execute(http=self._get_http())
            return about.get("user", {}).get("emailAddress", "")
        except Exception as e:
            print(f"Erro ao obter e-mail do Google Drive: {e}")
            return "user@gameflow.io"

