from typing import List, Optional
from use_cases.interfaces import IAssetStorageRepository
from domain import Asset, AssetType


class GoogleDriveAdapter(IAssetStorageRepository):
    """
    Adaptador concreto para o Google Drive implementando a interface IAssetStorageRepository (DIP & LSP).
    """
    def __init__(self, drive_service=None):
        if drive_service is None:
            from services.drive import DriveService
            self._service = DriveService()
        else:
            self._service = drive_service

    def is_authenticated(self) -> bool:
        return self._service.is_authenticated

    def list_assets(self, page_size: int = 50, asset_type: Optional[AssetType] = None) -> List[Asset]:
        raw_files = self._service.list_files(page_size=page_size)
        assets = []

        for item in raw_files:
            asset = Asset(
                id=item.get("id"),
                name=item.get("name", "Sem nome"),
                mime_type=item.get("mimeType"),
                size=int(item["size"]) if "size" in item and item["size"] else None,
                modified_time=item.get("modifiedTime")
            )
            if asset_type is None or asset.asset_type == asset_type:
                assets.append(asset)

        return assets

    def upload_asset(self, local_path: str, remote_folder_id: Optional[str] = None) -> str:
        return self._service.upload_file(local_path, drive_folder_id=remote_folder_id)

    def download_asset(self, asset_id: str, destination_path: str) -> str:
        return self._service.download_file(asset_id, destination_path)

    # ------------------------------------------------------------------ #
    # GFC-DVCS Extension (CAS & Metadata)
    # ------------------------------------------------------------------ #

    def _get_or_create_subfolder(self, workspace_folder_id: str, subfolder_name: str) -> str:
        gameflow_id = self._service.find_file_in_folder(workspace_folder_id, ".gameflow")
        if not gameflow_id:
            gameflow_id = self._service.create_folder(".gameflow", parent_folder_id=workspace_folder_id)
        
        subfolder_id = self._service.find_file_in_folder(gameflow_id, subfolder_name)
        if not subfolder_id:
            subfolder_id = self._service.create_folder(subfolder_name, parent_folder_id=gameflow_id)
        
        return subfolder_id

    def upload_object(self, local_path: str, content_hash: str, workspace_folder_id: str) -> str:
        objects_folder_id = self._get_or_create_subfolder(workspace_folder_id, "objects")
        existing_id = self._service.find_file_in_folder(objects_folder_id, content_hash)
        if existing_id:
            return existing_id
        
        import tempfile
        import shutil
        import os
        
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, content_hash)
        shutil.copy2(local_path, temp_file_path)
        try:
            file_id = self._service.upload_file(temp_file_path, drive_folder_id=objects_folder_id)
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        return file_id

    def download_object(self, content_hash: str, workspace_folder_id: str, destination_path: str) -> str:
        objects_folder_id = self._get_or_create_subfolder(workspace_folder_id, "objects")
        file_id = self._service.find_file_in_folder(objects_folder_id, content_hash)
        if not file_id:
            raise FileNotFoundError(f"Objeto {content_hash} não encontrado no Google Drive remoto.")
        
        return self._service.download_file(file_id, destination_path)

    def write_metadata(self, workspace_folder_id: str, subfolder_name: str, filename: str, content: dict) -> str:
        folder_id = self._get_or_create_subfolder(workspace_folder_id, subfolder_name)
        existing_id = self._service.find_file_in_folder(folder_id, filename)
        return self._service.write_json_file(folder_id, filename, content, file_id=existing_id)

    def read_metadata(self, workspace_folder_id: str, subfolder_name: str, filename: str) -> Optional[dict]:
        folder_id = self._get_or_create_subfolder(workspace_folder_id, subfolder_name)
        file_id = self._service.find_file_in_folder(folder_id, filename)
        if not file_id:
            return None
        return self._service.read_json_file(file_id)

    def list_metadata_files(self, workspace_folder_id: str, subfolder_name: str) -> List[dict]:
        folder_id = self._get_or_create_subfolder(workspace_folder_id, subfolder_name)
        query = f"'{folder_id}' in parents and trashed = false"
        results = self._service._service.files().list(
            q=query, 
            fields="files(id, name)"
        ).execute(http=self._service._get_http())
        return results.get("files", [])

