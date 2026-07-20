from typing import List, Optional
from use_cases.interfaces import IAssetStorageRepository, ILocalStorageRepository
from domain import Asset, AssetType, SyncStatus


class ListAssetsUseCase:
    """
    Caso de Uso: Listagem e Cruzamento de Status de Assets.
    Orquestra a listagem dos assets remotos e locais, calculando o status de sincronização (SyncStatus).
    """
    def __init__(self, remote_repo: IAssetStorageRepository, local_repo: Optional[ILocalStorageRepository] = None):
        self._remote_repo = remote_repo
        self._local_repo = local_repo

    def execute(self, asset_type: Optional[AssetType] = None) -> List[Asset]:
        if not self._remote_repo.is_authenticated():
            return []

        remote_assets = self._remote_repo.list_assets(page_size=50, asset_type=asset_type)

        if not self._local_repo:
            return remote_assets

        for asset in remote_assets:
            target_dir = self._local_repo.ensure_category_directory(asset.asset_type)
            import os
            expected_local_file = os.path.join(target_dir, asset.name)
            if os.path.exists(expected_local_file):
                asset.local_path = expected_local_file
                asset.status = SyncStatus.SYNCHRONIZED
            else:
                asset.status = SyncStatus.REMOTE_ONLY

        return remote_assets
