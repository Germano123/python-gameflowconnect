from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from .asset import Asset

@dataclass
class ProjectNotification:
    """
    Entidade de domínio para Notificações de Atualização de Assets no Projeto.
    """
    id: str
    project_id: str
    author: str
    message: str
    asset_name: str
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    read: bool = False

@dataclass
class Project:
    """
    Entidade de domínio para Projetos no GameFlowConnect.
    Principal unidade de organização, sincronização e colaboração entre artistas e devs.
    """
    id: str
    name: str
    description: str
    owner: str
    drive_folder_id: str
    members: List[str] = field(default_factory=list)
    assets: List[Asset] = field(default_factory=list)
    local_path: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

    def add_member(self, member_identifier: str) -> None:
        if member_identifier not in self.members:
            self.members.append(member_identifier)

    def attach_asset(self, asset: Asset) -> None:
        self.assets.append(asset)
