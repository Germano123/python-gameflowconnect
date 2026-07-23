import uuid
import os
import sqlite3
import json
from typing import List, Optional
from datetime import datetime
from domain import Workspace, WorkspaceNotification, Asset, SyncStatus, AssetType
from adapters.database import LocalDatabase

class WorkspaceManagerUseCase:
    """
    Caso de Uso: Gestão de Workspaces (Conforme especificações doc.md).
    Utiliza SQLite local (gameflow_local.db) para cache de sincronização,
    e o Google Drive como repositório compartilhado (sem servidor intermediário).
    """

    def __init__(self, db_dir: str = "data"):
        self._db = LocalDatabase(data_dir=db_dir)

    def create_workspace(self, name: str, description: str, engine: str, owner: str, drive_service, local_path: Optional[str] = None) -> Workspace:
        """
        Cria um workspace localmente no SQLite, pasta correspondente no Google Drive,
        e gera a pasta oculta .gameflow com manifest.json e config.json.
        """
        ws_id = f"ws_{uuid.uuid4().hex[:6]}"
        
        # 1. Criar pasta no Google Drive
        drive_folder_id = "demo_folder"
        if drive_service and drive_service.is_authenticated:
            try:
                drive_folder_id = drive_service.create_folder(f"GameFlow - {name}")
                # Salvar manifesto inicial no Drive (project_metadata.json foi substituído por manifest.json)
                metadata = {
                    "id": ws_id,
                    "name": name,
                    "description": description,
                    "engine": engine,
                    "owner": owner,
                    "members": [owner],
                    "created_at": datetime.now().strftime("%Y-%m-%d"),
                    "drive_folder_id": drive_folder_id
                }
                drive_service.write_json_file(drive_folder_id, "manifest.json", metadata)
            except Exception as e:
                print(f"Erro ao criar pasta no Drive: {e}")

        # 2. Gravar localmente
        path = local_path or os.path.abspath(f"./GameProjects/{name}")
        os.makedirs(path, exist_ok=True)

        # Criar a pasta oculta .gameflow e os manifestos
        gameflow_dir = os.path.join(path, ".gameflow")
        os.makedirs(gameflow_dir, exist_ok=True)

        manifest_data = {
            "id": ws_id,
            "name": name,
            "description": description,
            "engine": engine,
            "owner": owner,
            "members": [owner],
            "created_at": datetime.now().strftime("%Y-%m-%d"),
            "drive_folder_id": drive_folder_id
        }
        config_data = {
            "workspace_id": ws_id,
            "engine": engine,
            "google_drive_folder_id": drive_folder_id,
            "preferencias": {
                "auto_sync": False,
                "intervalo_sync_minutos": 15
            }
        }

        try:
            with open(os.path.join(gameflow_dir, "manifest.json"), "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2, ensure_ascii=False)
            with open(os.path.join(gameflow_dir, "config.json"), "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar arquivos .gameflow locais: {e}")

        created_date = datetime.now().strftime("%Y-%m-%d")
        conn = self._db.get_connection()
        try:
            conn.execute(
                "INSERT INTO local_workspaces (id, name, description, engine, drive_folder_id, local_path, owner, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (ws_id, name, description, engine, drive_folder_id, path, owner, created_date)
            )
            conn.commit()
        finally:
            conn.close()

        return Workspace(
            id=ws_id,
            name=name,
            description=description,
            engine=engine,
            owner=owner,
            drive_folder_id=drive_folder_id,
            members=[owner],
            local_path=path,
            created_at=created_date
        )

    def share_workspace(self, workspace_id: str, member_email: str, drive_service) -> bool:
        """
        Adiciona um colaborador ao workspace local, atualiza o manifesto no Drive
        e compartilha a pasta do Drive com o e-mail do convidado via API.
        """
        ws = self.get_workspace_by_id(workspace_id)
        if not ws:
            return False

        # 1. Compartilhar pasta no Drive via permissões
        if drive_service and drive_service.is_authenticated and ws.drive_folder_id != "demo_folder":
            try:
                drive_service.share_folder(ws.drive_folder_id, member_email, role="writer")
                
                # Ler, atualizar e gravar manifest.json no Drive
                meta_id = drive_service.find_file_in_folder(ws.drive_folder_id, "manifest.json")
                metadata = {}
                if meta_id:
                    metadata = drive_service.read_json_file(meta_id)
                
                members = metadata.get("members", [])
                if member_email not in members:
                    members.append(member_email)
                metadata["members"] = members
                
                drive_service.write_json_file(ws.drive_folder_id, "manifest.json", metadata, file_id=meta_id)
            except Exception as e:
                print(f"Erro ao compartilhar no Drive: {e}")
                return False

        # 2. Registrar novo membro no Workspace local e atualizar o manifest.json
        ws.add_member(member_email)
        if ws.local_path:
            gameflow_dir = os.path.join(ws.local_path, ".gameflow")
            if os.path.exists(gameflow_dir):
                manifest_path = os.path.join(gameflow_dir, "manifest.json")
                try:
                    config = {}
                    if os.path.exists(manifest_path):
                        with open(manifest_path, "r", encoding="utf-8") as f:
                            config = json.load(f)
                    
                    members = config.get("members", [])
                    if member_email not in members:
                        members.append(member_email)
                    config["members"] = members
                    
                    with open(manifest_path, "w", encoding="utf-8") as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    print(f"Erro ao salvar manifest.json local: {e}")
        return True

    def discover_shared_workspaces(self, user_email: str, drive_service) -> List[Workspace]:
        """
        Faz uma varredura no Google Drive buscando 'manifest.json' compartilhados com o usuário.
        Registra-os localmente no SQLite.
        """
        discovered = []
        if not drive_service or not drive_service.is_authenticated:
            return discovered

        try:
            query = "name = 'manifest.json' and trashed = false"
            results = drive_service._service.files().list(q=query, fields="files(id, name, parents)").execute()
            shared_files = results.get("files", [])


            for file_info in shared_files:
                file_id = file_info.get("id")
                parents = file_info.get("parents")
                if not parents:
                    continue
                drive_folder_id = parents[0]

                # Ler o manifesto do workspace
                metadata = drive_service.read_json_file(file_id)
                ws_id = metadata.get("id")
                members = metadata.get("members", [])

                if user_email in members:
                    existing = self.get_workspace_by_id(ws_id)
                    if not existing:
                        name = metadata.get("name", "Workspace Compartilhado")
                        desc = metadata.get("description", "")
                        engine = metadata.get("engine", "Godot")
                        owner = metadata.get("owner", "")
                        created_date = metadata.get("created_at", datetime.now().strftime("%Y-%m-%d"))
                        local_path = os.path.abspath(f"./GameProjects/{name}")

                        conn = self._db.get_connection()
                        try:
                            conn.execute(
                                "INSERT INTO local_workspaces (id, name, description, engine, drive_folder_id, local_path, owner, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                (ws_id, name, desc, engine, drive_folder_id, local_path, owner, created_date)
                            )
                            conn.commit()
                        finally:
                            conn.close()

                        discovered.append(Workspace(
                            id=ws_id,
                            name=name,
                            description=desc,
                            engine=engine,
                            owner=owner,
                            drive_folder_id=drive_folder_id,
                            members=members,
                            local_path=local_path,
                            created_at=created_date
                        ))
        except Exception as e:
            print(f"Erro ao descobrir workspaces compartilhados: {e}")

        return discovered

    def list_workspaces(self) -> List[Workspace]:
        """Retorna todos os workspaces registrados no SQLite local."""
        workspaces = []
        conn = self._db.get_connection()
        try:
            cursor = conn.execute("SELECT * FROM local_workspaces")
            for row in cursor.fetchall():
                assets = self._list_local_assets(row["id"])
                
                workspaces.append(Workspace(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    engine=row["engine"],
                    owner=row["owner"],
                    drive_folder_id=row["drive_folder_id"],
                    local_path=row["local_path"],
                    created_at=row["created_at"],
                    assets=assets
                ))
        finally:
            conn.close()
        return workspaces

    def get_workspace_by_id(self, workspace_id: str) -> Optional[Workspace]:
        conn = self._db.get_connection()
        try:
            row = conn.execute("SELECT * FROM local_workspaces WHERE id = ?", (workspace_id,)).fetchone()
            if row:
                assets = self._list_local_assets(workspace_id)
                return Workspace(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    engine=row["engine"],
                    owner=row["owner"],
                    drive_folder_id=row["drive_folder_id"],
                    local_path=row["local_path"],
                    created_at=row["created_at"],
                    assets=assets
                )
        finally:
            conn.close()
        return None

    def delete_workspace(self, workspace_id: str) -> bool:
        """Exclui o workspace localmente no SQLite."""
        conn = self._db.get_connection()
        try:
            conn.execute("DELETE FROM local_workspaces WHERE id = ?", (workspace_id,))
            conn.commit()
        finally:
            conn.close()
        return True

    def notify_asset_added(self, workspace_id: str, author: str, asset: Asset, drive_service) -> WorkspaceNotification:
        """
        Adiciona o asset ao banco local SQLite, atualiza a lista de assets,
        e grava um novo evento de notificação em 'activity_log.json' no Google Drive do workspace.
        """
        notif_id = f"notif_{uuid.uuid4().hex[:6]}"
        message = f"{author} adicionou o asset '{asset.name}'."
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        notification = WorkspaceNotification(
            id=notif_id,
            workspace_id=workspace_id,
            author=author,
            message=message,
            asset_name=asset.name,
            timestamp=timestamp
        )

        asset_id = asset.id or f"asset_{uuid.uuid4().hex[:6]}"
        conn = self._db.get_connection()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO local_assets (id, workspace_id, name, mime_type, size, local_path, status, last_sync) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (asset_id, workspace_id, asset.name, asset.mime_type, asset.size, asset.local_path, "SYNCHRONIZED", timestamp)
            )
            conn.commit()
        finally:
            conn.close()

        ws = self.get_workspace_by_id(workspace_id)
        if ws and drive_service and drive_service.is_authenticated and ws.drive_folder_id != "demo_folder":
            try:
                log_file_id = drive_service.find_file_in_folder(ws.drive_folder_id, "activity_log.json")
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
                drive_service.write_json_file(ws.drive_folder_id, "activity_log.json", log_data, file_id=log_file_id)
            except Exception as e:
                print(f"Erro ao salvar log no Drive: {e}")

        return notification

    def get_unread_notifications(self, drive_service, workspaces: List[Workspace]) -> List[WorkspaceNotification]:
        """
        Consulta o 'activity_log.json' de todos os workspaces ativos no Drive
        e retorna alertas visuais de assets novos.
        """
        notifications = []
        if not drive_service or not drive_service.is_authenticated:
            return notifications

        for ws in workspaces:
            if ws.drive_folder_id == "demo_folder":
                continue
            try:
                log_file_id = drive_service.find_file_in_folder(ws.drive_folder_id, "activity_log.json")
                if log_file_id:
                    logs = drive_service.read_json_file(log_file_id)
                    for log in logs:
                        notifications.append(WorkspaceNotification(
                            id=log.get("id"),
                            workspace_id=ws.id,
                            author=log.get("author"),
                            message=f"[{ws.name}] {log.get('message')}",
                            asset_name=log.get("asset_name"),
                            timestamp=log.get("timestamp"),
                            read=False
                        ))
            except Exception as e:
                print(f"Erro ao ler notificações do workspace {ws.name}: {e}")

        notifications.sort(key=lambda x: x.timestamp, reverse=True)
        return notifications

    def _list_local_assets(self, workspace_id: str) -> List[Asset]:
        assets = []
        conn = self._db.get_connection()
        try:
            cursor = conn.execute("SELECT * FROM local_assets WHERE workspace_id = ?", (workspace_id,))
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

    def get_workspace_assets_sync_status(self, workspace_id: str, drive_service) -> List[Asset]:
        """
        Retorna a lista unificada de assets detectados localmente no diretório do workspace
        e remotamente no Google Drive, com seus respectivos status (SYNCHRONIZED, REMOTE_ONLY, LOCAL_ONLY).
        """
        ws = self.get_workspace_by_id(workspace_id)
        if not ws:
            return []

        # 1. Escanear arquivos locais no workspace (excluindo .gameflow)
        local_files = {}
        if ws.local_path and os.path.exists(ws.local_path):
            for root, dirs, files in os.walk(ws.local_path):
                if ".gameflow" in root:
                    continue
                for f in files:
                    full_path = os.path.join(root, f)
                    try:
                        size = os.path.getsize(full_path)
                        local_files[f] = {
                            "path": full_path,
                            "size": size
                        }
                    except Exception:
                        pass

        # 2. Obter arquivos remotos da pasta correspondente no Google Drive
        remote_assets = []
        if drive_service and drive_service.is_authenticated and ws.drive_folder_id != "demo_folder":
            try:
                query = f"'{ws.drive_folder_id}' in parents and trashed = false"
                results = drive_service._service.files().list(q=query, fields="files(id, name, mimeType, size, modifiedTime)").execute()
                files = results.get("files", [])
                for f in files:
                    name = f.get("name")
                    if name in ["manifest.json", "config.json", "activity_log.json"]:
                        continue

                    size = int(f.get("size", 0))
                    fid = f.get("id")
                    mime = f.get("mimeType")
                    modified = f.get("modifiedTime", "")

                    status = SyncStatus.REMOTE_ONLY
                    local_path = None
                    if name in local_files:
                        status = SyncStatus.SYNCHRONIZED
                        local_path = local_files[name]["path"]
                        # Remove da lista local para sabermos quais são apenas locais
                        del local_files[name]

                    remote_assets.append(Asset(
                        id=fid,
                        name=name,
                        mime_type=mime,
                        size=size,
                        local_path=local_path,
                        status=status,
                        modified_time=modified
                    ))
            except Exception as e:
                print(f"Erro ao obter arquivos remotos no sync status: {e}")

        # 3. Adicionar arquivos locais pendentes de envio
        for name, info in local_files.items():
            remote_assets.append(Asset(
                id=None,
                name=name,
                mime_type="application/octet-stream",
                size=info["size"],
                local_path=info["path"],
                status=SyncStatus.LOCAL_ONLY,
                modified_time=datetime.now().strftime("%Y-%m-%d")
            ))

        return remote_assets

    def sync_asset(self, workspace_id: str, asset: Asset, drive_service, author_email: str) -> bool:
        """
        Sincroniza um asset individual:
        - REMOTE_ONLY (Nuvem): baixa do Drive para a pasta local do workspace.
        - LOCAL_ONLY (Local): envia do local para a pasta do Drive e emite notificação.
        """
        ws = self.get_workspace_by_id(workspace_id)
        if not ws:
            return False

        # Sincronização de arquivo da nuvem para o local
        if asset.status == SyncStatus.REMOTE_ONLY and drive_service and drive_service.is_authenticated:
            try:
                dest_path = os.path.join(ws.local_path, asset.name)
                # Baixar usando a API do Drive
                request = drive_service._service.files().get_media(fileId=asset.id)
                with open(dest_path, "wb") as f:
                    f.write(request.execute())
                
                # Salvar no SQLite local
                conn = self._db.get_connection()
                try:
                    conn.execute(
                        "INSERT OR REPLACE INTO local_assets (id, workspace_id, name, mime_type, size, local_path, status, last_sync) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (asset.id, workspace_id, asset.name, asset.mime_type, asset.size, dest_path, "SYNCHRONIZED", datetime.now().strftime("%Y-%m-%d %H:%M"))
                    )
                    conn.commit()
                finally:
                    conn.close()
                return True
            except Exception as e:
                print(f"Erro ao baixar asset no sync: {e}")
                return False

        # Sincronização de arquivo local para a nuvem
        elif asset.status == SyncStatus.LOCAL_ONLY and drive_service and drive_service.is_authenticated:
            try:
                # Fazer upload para a pasta correspondente no Drive
                from googleapiclient.http import MediaFileUpload
                file_metadata = {
                    'name': asset.name,
                    'parents': [ws.drive_folder_id]
                }
                media = MediaFileUpload(asset.local_path, mimetype=asset.mime_type or 'application/octet-stream', resumable=True)
                file = drive_service._service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                uploaded_id = file.get('id')

                # Notificar equipe e registrar no SQLite local
                asset.id = uploaded_id
                self.notify_asset_added(workspace_id, author_email, asset, drive_service)
                return True
            except Exception as e:
                print(f"Erro ao enviar asset no sync: {e}")
                return False

        return False

