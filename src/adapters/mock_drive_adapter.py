from typing import List, Optional
from use_cases.interfaces import IAssetStorageRepository
from domain import Asset, AssetType
from services.demo import MockDriveService


class MockDriveAdapter(IAssetStorageRepository):
    """
    Adaptador Mock para o modo de demonstração implementando IAssetStorageRepository (LSP).
    """
    def __init__(self, mock_service: Optional[MockDriveService] = None):
        self._service = mock_service or MockDriveService()

    def is_authenticated(self) -> bool:
        return True

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
