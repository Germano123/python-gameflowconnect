import uuid
from typing import List, Optional
from domain import Project, ProjectNotification, Asset

class ProjectManagerUseCase:
    """
    Caso de Uso: Gerenciamento de Projetos e Colaboradores.
    Cuida da criação de projetos, convite de membros e emissão de alertas visuais de atualização de assets.
    """
    _in_memory_projects: List[Project] = []
    _in_memory_notifications: List[ProjectNotification] = []

    def __init__(self):
        if not self._in_memory_projects:
            # Projetos padrão iniciais para prototipagem/teste
            p1 = Project(
                id="proj_1",
                name="Cyberpunk RPG Indie",
                description="Projeto principal do jogo RPG 2D em Pixel Art",
                owner="dev_lead@gameflow.io",
                members=["artist_1@gameflow.io", "designer_2@gameflow.io"]
            )
            p2 = Project(
                id="proj_2",
                name="Space Explorer 3D",
                description="Jogo de exploração espacial em Low-Poly",
                owner="designer_1@gameflow.io",
                members=["dev_lead@gameflow.io"]
            )
            self._in_memory_projects.extend([p1, p2])

    def create_project(self, name: str, description: str, owner: str = "user@gameflow.io", local_path: Optional[str] = None) -> Project:
        proj_id = f"proj_{uuid.uuid4().hex[:6]}"
        new_proj = Project(
            id=proj_id,
            name=name,
            description=description,
            owner=owner,
            members=[owner],
            local_path=local_path
        )
        self._in_memory_projects.append(new_proj)
        return new_proj

    def share_project(self, project_id: str, member_email: str) -> bool:
        for p in self._in_memory_projects:
            if p.id == project_id:
                p.add_member(member_email)
                return True
        return False

    def list_projects(self) -> List[Project]:
        return ProjectManagerUseCase._in_memory_projects


    def get_project_by_id(self, project_id: str) -> Optional[Project]:
        for p in self._in_memory_projects:
            if p.id == project_id:
                return p
        return None

    def notify_asset_added(self, project_id: str, author: str, asset: Asset) -> ProjectNotification:
        notif_id = f"notif_{uuid.uuid4().hex[:6]}"
        message = f"{author} adicionou o asset '{asset.name}' no projeto."
        notification = ProjectNotification(
            id=notif_id,
            project_id=project_id,
            author=author,
            message=message,
            asset_name=asset.name
        )
        self._in_memory_notifications.insert(0, notification)

        # Attach asset to project entity
        proj = self.get_project_by_id(project_id)
        if proj:
            proj.attach_asset(asset)

        return notification

    def get_unread_notifications(self) -> List[ProjectNotification]:
        return [n for n in self._in_memory_notifications if not n.read]

    def mark_all_as_read(self) -> None:
        for n in self._in_memory_notifications:
            n.read = True
