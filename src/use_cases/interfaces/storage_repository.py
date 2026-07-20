from abc import ABC, abstractmethod
from typing import List, Optional
from domain import Asset, AssetType


class IAssetStorageRepository(ABC):
    """
    Interface para o repositório de armazenamento remoto de assets (DIP / ISP).
    """
    @abstractmethod
    def is_authenticated(self) -> bool:
        """Verifica se o repositório remoto está autenticado."""
        pass

    @abstractmethod
    def list_assets(self, page_size: int = 50, asset_type: Optional[AssetType] = None) -> List[Asset]:
        """Lista assets remotos, opcionalmente filtrados por tipo de asset."""
        pass

    @abstractmethod
    def upload_asset(self, local_path: str, remote_folder_id: Optional[str] = None) -> str:
        """Envia um arquivo local para o armazenamento remoto e retorna seu ID."""
        pass

    @abstractmethod
    def download_asset(self, asset_id: str, destination_path: str) -> str:
        """Baixa um asset remoto para o caminho de destino local."""
        pass
