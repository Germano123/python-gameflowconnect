import uuid
import os
import sqlite3
from typing import List, Optional
from datetime import datetime
from domain import Project, ProjectNotification, Asset, SyncStatus, AssetType
from adapters.database import LocalDatabase

class ProjectManagerUseCase:
    """
    Caso de Uso: Orquestração Descentralizada de Projetos.
    Utiliza SQLite local (gameflow_local.db) para cache de sincronização rápida,
    e o Google Drive como repositório compartilhado (sem servidor intermediário).
    """

    def __init__(self, db_dir: str = "data"):
        self._db = LocalDatabase(data_dir=db_dir)

    def create_project(self, name: str, description: str, owner: str, drive_service, local_path: Optional[str] = None) -> Project:
        """
        Cria um projeto localmente no SQLite e cria a pasta correspondente no Google Drive,
        gravando o manifesto 'project_metadata.json'.
        """
        proj_id = f"proj_{uuid.uuid4().hex[:6]}"
        
        # 1. Criar pasta no Google Drive
        drive_folder_id = "demo_folder"
        if drive_service and drive_service.is_authenticated:
            try:
                drive_folder_id = drive_service.create_folder(f"GameFlow - {name}")
                # Salvar manifesto inicial no Drive
                metadata = {
                    "id": proj_id,
                    "name": name,
                    "description": description,
                    "owner": owner,
                    "members": [owner],
                    "created_at": datetime.now().strftime("%Y-%m-%d")
                }
                drive_service.write_json_file(drive_folder_id, "project_metadata.json", metadata)
            except Exception as e:
                # Fallback em caso de erro na API do Drive
                print(f"Erro ao criar pasta no Drive: {e}")

        # 2. Gravar no SQLite Local
        path = local_path or os.path.abspath(f"./GameProjects/{name}")
        os.makedirs(path, exist_ok=True)

        # Criar pasta oculta .gameflow e connection.json localmente
        gameflow_dir = os.path.join(path, ".gameflow")
        os.makedirs(gameflow_dir, exist_ok=True)
        import json
        config_data = {
            "project_id": proj_id,
            "name": name,
            "description": description,
            "drive_folder_id": drive_folder_id,
            "owner": owner,
            "created_at": datetime.now().strftime("%Y-%m-%d"),
            "members": [owner]
        }
        try:
            with open(os.path.join(gameflow_dir, "connection.json"), "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar arquivo .gameflow/connection.json local: {e}")

        created_date = datetime.now().strftime("%Y-%m-%d")
        conn = self._db.get_connection()
        try:
            conn.execute(
                "INSERT INTO local_projects (id, name, description, drive_folder_id, local_path, owner, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (proj_id, name, description, drive_folder_id, path, owner, created_date)
            )
            conn.commit()
        finally:
            conn.close()

        return Project(
            id=proj_id,
            name=name,
            description=description,
            owner=owner,
            drive_folder_id=drive_folder_id,
            members=[owner],
            local_path=path,
            created_at=created_date
        )

    def share_project(self, project_id: str, member_email: str, drive_service) -> bool:
        """
        Adiciona um colaborador ao projeto local, atualiza o manifesto no Drive
        e compartilha a pasta do Drive com o e-mail do convidado via API.
        """
        proj = self.get_project_by_id(project_id)
        if not proj:
            return False

        # 1. Compartilhar pasta no Drive via permissões
        if drive_service and drive_service.is_authenticated and proj.drive_folder_id != "demo_folder":
            try:
                # Adicionar permissão ao e-mail no Drive
                drive_service.share_folder(proj.drive_folder_id, member_email, role="writer")
                
                # Ler, atualizar e gravar manifesto de metadados no Drive
                meta_id = drive_service.find_file_in_folder(proj.drive_folder_id, "project_metadata.json")
                metadata = {}
                if meta_id:
                    metadata = drive_service.read_json_file(meta_id)
                
                members = metadata.get("members", [])
                if member_email not in members:
                    members.append(member_email)
                metadata["members"] = members
                
                drive_service.write_json_file(proj.drive_folder_id, "project_metadata.json", metadata, file_id=meta_id)
            except Exception as e:
                print(f"Erro ao compartilhar no Drive: {e}")
                return False

        # 2. Registrar novo membro na entidade local e atualizar o connection.json
        proj.add_member(member_email)
        if proj.local_path:
            gameflow_dir = os.path.join(proj.local_path, ".gameflow")
            if os.path.exists(gameflow_dir):
                conn_path = os.path.join(gameflow_dir, "connection.json")
                import json
                try:
                    config = {}
                    if os.path.exists(conn_path):
                        with open(conn_path, "r", encoding="utf-8") as f:
                            config = json.load(f)
                    
                    members = config.get("members", [])
                    if member_email not in members:
                        members.append(member_email)
                    config["members"] = members
                    
                    with open(conn_path, "w", encoding="utf-8") as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    print(f"Erro ao salvar arquivo .gameflow/connection.json local: {e}")
        return True


    def discover_shared_projects(self, user_email: str, drive_service) -> List[Project]:
        """
        Faz uma varredura nas pastas compartilhadas do Google Drive buscando manifestos
        de projetos do GameFlow, e os adiciona ao SQLite local caso não estejam cadastrados.
        """
        discovered = []
        if not drive_service or not drive_service.is_authenticated:
            return discovered

        try:
            # Buscar arquivos 'project_metadata.json' compartilhados comigo
            shared_files = drive_service.search_shared_projects()
            for file_info in shared_files:
                file_id = file_info.get("id")
                parents = file_info.get("parents")
                if not parents:
                    continue
                drive_folder_id = parents[0]

                # Ler o manifesto do projeto
                metadata = drive_service.read_json_file(file_id)
                proj_id = metadata.get("id")
                members = metadata.get("members", [])

                # Verificar se o usuário faz parte dos membros e se já não está registrado localmente
                if user_email in members:
                    existing = self.get_project_by_id(proj_id)
                    if not existing:
                        # Adicionar automaticamente ao SQLite local com caminho temporário/padrão
                        name = metadata.get("name", "Projeto Compartilhado")
                        desc = metadata.get("description", "")
                        owner = metadata.get("owner", "")
                        created_date = metadata.get("created_at", datetime.now().strftime("%Y-%m-%d"))
                        local_path = os.path.abspath(f"./GameProjects/{name}")

                        conn = self._db.get_connection()
                        try:
                            conn.execute(
                                "INSERT INTO local_projects (id, name, description, drive_folder_id, local_path, owner, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                (proj_id, name, desc, drive_folder_id, local_path, owner, created_date)
                            )
                            conn.commit()
                        finally:
                            conn.close()

                        discovered.append(Project(
                            id=proj_id,
                            name=name,
                            description=desc,
                            owner=owner,
                            drive_folder_id=drive_folder_id,
                            members=members,
                            local_path=local_path,
                            created_at=created_date
                        ))
        except Exception as e:
            print(f"Erro ao descobrir projetos compartilhados: {e}")

        return discovered

    def list_projects(self) -> List[Project]:
        """Retorna todos os projetos registrados no SQLite local."""
        projects = []
        conn = self._db.get_connection()
        try:
            cursor = conn.execute("SELECT * FROM local_projects")
            for row in cursor.fetchall():
                # Obter assets cadastrados localmente
                assets = self._list_local_assets(row["id"])
                
                projects.append(Project(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    drive_folder_id=row["drive_folder_id"],
                    owner=row["owner"],
                    local_path=row["local_path"],
                    created_at=row["created_at"],
                    assets=assets
                ))
        finally:
            conn.close()
        return projects

    def get_project_by_id(self, project_id: str) -> Optional[Project]:
        conn = self._db.get_connection()
        try:
            row = conn.execute("SELECT * FROM local_projects WHERE id = ?", (project_id,)).fetchone()
            if row:
                assets = self._list_local_assets(project_id)
                return Project(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    drive_folder_id=row["drive_folder_id"],
                    owner=row["owner"],
                    local_path=row["local_path"],
                    created_at=row["created_at"],
                    assets=assets
                )
        finally:
            conn.close()
        return None

    def delete_project(self, project_id: str) -> bool:
        """Exclui o projeto localmente no SQLite."""
        conn = self._db.get_connection()
        try:
            conn.execute("DELETE FROM local_projects WHERE id = ?", (project_id,))
            conn.commit()
        finally:
            conn.close()
        return True

    def notify_asset_added(self, project_id: str, author: str, asset: Asset, drive_service) -> ProjectNotification:
        """
        Adiciona o asset ao banco local SQLite, atualiza a lista de assets no projeto,
        grava um novo evento de notificação em 'activity_log.json' no Google Drive do projeto,
        gerando alertas para a equipe conectada.
        """
        notif_id = f"notif_{uuid.uuid4().hex[:6]}"
        message = f"{author} adicionou o asset '{asset.name}'."
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        notification = ProjectNotification(
            id=notif_id,
            project_id=project_id,
            author=author,
            message=message,
            asset_name=asset.name,
            timestamp=timestamp
        )

        # 1. Salvar asset no SQLite local
        asset_id = asset.id or f"asset_{uuid.uuid4().hex[:6]}"
        conn = self._db.get_connection()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO local_assets (id, project_id, name, mime_type, size, local_path, status, last_sync) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (asset_id, project_id, asset.name, asset.mime_type, asset.size, asset.local_path, "SYNCHRONIZED", timestamp)
            )
            conn.commit()
        finally:
            conn.close()

        # 2. Registrar no activity_log.json do Google Drive para alertar colaboradores
        proj = self.get_project_by_id(project_id)
        if proj and drive_service and drive_service.is_authenticated and proj.drive_folder_id != "demo_folder":
            try:
                log_file_id = drive_service.find_file_in_folder(proj.drive_folder_id, "activity_log.json")
                log_data = []
                if log_file_id:
                    log_data = drive_service.read_json_file(log_file_id)
                
                log_data.append({
                    "id": notif_id,
                    "author": author,
                    "message": message,
                    "asset_name": asset.name,
                    "timestamp": timestamp
                })
                drive_service.write_json_file(proj.drive_folder_id, "activity_log.json", log_data, file_id=log_file_id)
            except Exception as e:
                print(f"Erro ao salvar log no Drive: {e}")

        return notification

    def get_unread_notifications(self, drive_service, projects: List[Project]) -> List[ProjectNotification]:
        """
        Consulta o 'activity_log.json' de todos os projetos ativos no Drive
        e retorna alertas visuais de assets novos enviados por colaboradores.
        """
        notifications = []
        if not drive_service or not drive_service.is_authenticated:
            return notifications

        for proj in projects:
            if proj.drive_folder_id == "demo_folder":
                continue
            try:
                log_file_id = drive_service.find_file_in_folder(proj.drive_folder_id, "activity_log.json")
                if log_file_id:
                    logs = drive_service.read_json_file(log_file_id)
                    for log in logs:
                        notifications.append(ProjectNotification(
                            id=log.get("id"),
                            project_id=proj.id,
                            author=log.get("author"),
                            message=f"[{proj.name}] {log.get('message')}",
                            asset_name=log.get("asset_name"),
                            timestamp=log.get("timestamp"),
                            read=False
                        ))
            except Exception as e:
                print(f"Erro ao ler notificações do projeto {proj.name}: {e}")

        # Ordenar por data mais recente
        notifications.sort(key=lambda x: x.timestamp, reverse=True)
        return notifications

    # ------------------------------------------------------------------ #
    # Métodos Auxiliares
    # ------------------------------------------------------------------ #

    def _list_local_assets(self, project_id: str) -> List[Asset]:
        assets = []
        conn = self._db.get_connection()
        try:
            cursor = conn.execute("SELECT * FROM local_assets WHERE project_id = ?", (project_id,))
            for row in cursor.fetchall():
                assets.append(Asset(
                    id=row["id"],
                    name=row["name"],
                    mime_type=row["mime_type"],
                    size=row["size"],
                    local_path=row["local_path"],
                    status=SyncStatus.SYNCHRONIZED
                ))
        finally:
            conn.close()
        return assets
