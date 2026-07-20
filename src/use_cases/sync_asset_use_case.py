import os
from typing import Optional
from use_cases.interfaces import IAssetStorageRepository, ILocalStorageRepository
from domain import Asset, SyncStatus


class SyncAssetUseCase:
    """
    Caso de Uso: Sincronização de Asset Individual ou em Lote.
    Responsável por realizar o download seguro de um asset remoto para a pasta da Game Engine
    ou o upload de um arquivo local para o storage remoto.
    """
    def __init__(self, remote_repo: IAssetStorageRepository, local_repo: ILocalStorageRepository):
        self._remote_repo = remote_repo
        self._local_repo = local_repo

    def download_to_engine(self, asset: Asset) -> str:
        """
        Baixa o asset para a subpasta correspondente da Engine (ex: Assets/Images/hero.png).
        """
        if not asset.id:
            raise ValueError("O asset remoto precisa ter um ID para ser baixado.")

        target_dir = self._local_repo.ensure_category_directory(asset.asset_type)
        destination_path = os.path.join(target_dir, asset.name)

        saved_path = self._remote_repo.download_asset(asset.id, destination_path)
        asset.local_path = saved_path
        asset.status = SyncStatus.SYNCHRONIZED
        return saved_path

    def upload_from_local(self, local_file_path: str, remote_folder_id: Optional[str] = None) -> str:
        """
        Envia um asset do disco local para o repositório remoto.
        """
        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f"Arquivo local não encontrado: {local_file_path}")

        file_id = self._remote_repo.upload_asset(local_file_path, remote_folder_id)
        return file_id
