from abc import ABC, abstractmethod
from typing import List, Optional
from domain import Asset, AssetType


class ILocalStorageRepository(ABC):
    """
    Interface para o gerenciamento de arquivos locais no projeto da Game Engine.
    """
    @abstractmethod
    def get_local_project_path(self) -> str:
        """Retorna o caminho raiz do projeto local da Game Engine."""
        pass

    @abstractmethod
    def ensure_category_directory(self, asset_type: AssetType) -> str:
        """Garante que a subpasta apropriada (ex: Assets/Images) exista no disco e retorna seu caminho absoluto."""
        pass

    @abstractmethod
    def list_local_assets(self, asset_type: Optional[AssetType] = None) -> List[Asset]:
        """Lista assets existentes localmente na pasta do projeto."""
        pass

    @abstractmethod
    def file_exists(self, relative_or_abs_path: str) -> bool:
        """Verifica se determinado arquivo existe localmente."""
        pass
