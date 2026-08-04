import os
from typing import List, Optional
from use_cases.interfaces import ILocalStorageRepository
from domain import Asset, AssetType, SyncStatus


class LocalFileAdapter(ILocalStorageRepository):
    """
    Adaptador de Sistema de Arquivos Local para gerenciar arquivos na pasta da Game Engine.
    """
    CATEGORY_FOLDERS = {
        AssetType.IMAGE: "Assets/Images",
        AssetType.DOCUMENT: "Assets/Docs",
        AssetType.MODEL_3D: "Assets/Models",
        AssetType.OTHER: "Assets/Misc"
    }

    def __init__(self, project_path: str):
        self._project_path = project_path

    def get_local_project_path(self) -> str:
        return self._project_path

    def ensure_category_directory(self, asset_type: AssetType) -> str:
        sub_folder = self.CATEGORY_FOLDERS.get(asset_type, "Assets/Misc")
        full_path = os.path.join(self._project_path, sub_folder)
        os.makedirs(full_path, exist_ok=True)
        return full_path

    def list_local_assets(self, asset_type: Optional[AssetType] = None) -> List[Asset]:
        sub_folder = self.CATEGORY_FOLDERS.get(asset_type) if asset_type else "Assets"
        target_dir = os.path.join(self._project_path, sub_folder)
        if not os.path.exists(target_dir):
            return []

        assets = []
        for root, _, files in os.walk(target_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                stat = os.stat(abs_path)
                asset = Asset(
                    name=file,
                    size=stat.st_size,
                    local_path=abs_path,
                    status=SyncStatus.LOCAL_ONLY
                )
                if asset_type is None or asset.asset_type == asset_type:
                    assets.append(asset)
        return assets

    def file_exists(self, relative_or_abs_path: str) -> bool:
        if os.path.isabs(relative_or_abs_path):
            return os.path.exists(relative_or_abs_path)
        return os.path.exists(os.path.join(self._project_path, relative_or_abs_path))
