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
        from state import AppState
        path = local_path or os.path.abspath(os.path.join(AppState.local_base_dir, name))

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
            shared_files = drive_service.search_shared_projects()


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
                    # Verificar se está ignorado
                    conn = self._db.get_connection()
                    try:
                        cursor = conn.execute("SELECT 1 FROM ignored_workspaces WHERE id = ?", (ws_id,))
                        ignored = cursor.fetchone() is not None
                    finally:
                        conn.close()

                    if ignored:
                        continue

                    existing = self.get_workspace_by_id(ws_id)
                    if not existing:

                        name = metadata.get("name", "Workspace Compartilhado")
                        desc = metadata.get("description", "")
                        engine = metadata.get("engine", "Godot")
                        owner = metadata.get("owner", "")
                        created_date = metadata.get("created_at", datetime.now().strftime("%Y-%m-%d"))

                        from state import AppState
                        local_path = os.path.abspath(os.path.join(AppState.local_base_dir, name))


                        # Criar pasta física local do workspace
                        os.makedirs(local_path, exist_ok=True)
                        gameflow_dir = os.path.join(local_path, ".gameflow")
                        os.makedirs(gameflow_dir, exist_ok=True)

                        # Criar manifest.json se não existir
                        manifest_path = os.path.join(gameflow_dir, "manifest.json")
                        if not os.path.exists(manifest_path):
                            import json
                            manifest_data = {
                                "id": ws_id,
                                "name": name,
                                "description": desc,
                                "engine": engine,
                                "owner": owner,
                                "created_at": created_date,
                                "drive_folder_id": drive_folder_id,
                                "members": members
                            }
                            with open(manifest_path, "w", encoding="utf-8") as f:
                                json.dump(manifest_data, f, indent=4, ensure_ascii=False)

                        # Criar config.json se não existir
                        config_path = os.path.join(gameflow_dir, "config.json")
                        if not os.path.exists(config_path):
                            import json
                            config_data = {
                                "workspace_id": ws_id,
                                "engine": engine,
                                "google_drive_folder_id": drive_folder_id,
                                "preferencias": {
                                    "auto_sync": False,
                                    "intervalo_sync_minutos": 15
                                }
                            }
                            with open(config_path, "w", encoding="utf-8") as f:
                                json.dump(config_data, f, indent=4, ensure_ascii=False)

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

    def scan_and_import_local_workspaces(self, local_base_dir: str) -> List[Workspace]:
        """
        Percorre o diretório base local em busca de subpastas que já contenham a pasta oculta '.gameflow'
        com um 'manifest.json' válido. Se encontrar, e o workspace não estiver cadastrado no banco SQLite local,
        cadastra-o automaticamente no banco local.
        """
        imported = []
        if not local_base_dir or not os.path.exists(local_base_dir):
            return imported

        conn = self._db.get_connection()
        try:
            # 1. Obter IDs dos workspaces já registrados ou ignorados para evitar duplicidade
            existing_ids = set()
            cursor = conn.execute("SELECT id FROM local_workspaces")
            for row in cursor.fetchall():
                existing_ids.add(row["id"])
                
            ignored_ids = set()
            try:
                cursor = conn.execute("SELECT workspace_id FROM ignored_workspaces")
                for row in cursor.fetchall():
                    ignored_ids.add(row["workspace_id"])
            except sqlite3.OperationalError:
                pass 

            # 2. Percorrer subpastas do diretório base
            for item in os.listdir(local_base_dir):
                item_path = os.path.join(local_base_dir, item)
                if not os.path.isdir(item_path):
                    continue

                manifest_path = os.path.join(item_path, ".gameflow", "manifest.json")
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, "r", encoding="utf-8") as f:
                            metadata = json.load(f)
                        
                        ws_id = metadata.get("id")
                        ws_name = metadata.get("name", item)
                        ws_desc = metadata.get("description", "")
                        ws_engine = metadata.get("engine", "")
                        ws_owner = metadata.get("owner", "")
                        ws_drive_id = metadata.get("drive_folder_id")
                        ws_created = metadata.get("created_at", datetime.now().strftime("%Y-%m-%d"))

                        if ws_id and ws_id not in existing_ids and ws_id not in ignored_ids:
                            conn.execute(
                                """
                                INSERT INTO local_workspaces (id, name, description, engine, owner, drive_folder_id, local_path, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (ws_id, ws_name, ws_desc, ws_engine, ws_owner, ws_drive_id, item_path, ws_created)
                            )
                            conn.commit()
                            existing_ids.add(ws_id)
                            
                            imported.append(Workspace(
                                id=ws_id,
                                name=ws_name,
                                description=ws_desc,
                                engine=ws_engine,
                                owner=ws_owner,
                                drive_folder_id=ws_drive_id,
                                local_path=item_path,
                                created_at=ws_created,
                                assets=[]
                            ))
                    except Exception as e:
                        print(f"Erro ao ler/importar workspace em {item_path}: {e}")
        finally:
            conn.close()
        return imported

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

    def delete_workspace(self, workspace_id: str, drive_service=None, user_email: str = None) -> bool:
        """Exclui o workspace localmente no SQLite, deleta a pasta física e marca como ignorado."""
        conn = self._db.get_connection()
        try:
            # Obter local_path, drive_folder_id e owner antes de deletar
            cursor = conn.execute("SELECT local_path, drive_folder_id, owner FROM local_workspaces WHERE id = ?", (workspace_id,))
            row = cursor.fetchone()
            local_path = row["local_path"] if row else None
            drive_folder_id = row["drive_folder_id"] if row else None
            owner = row["owner"] if row else None

            # Se o usuário for convidado, tentar removê-lo da participação no Drive
            if drive_service and drive_service.is_authenticated and user_email and owner and owner != user_email:
                try:
                    # Encontrar o arquivo manifest.json remoto
                    manifest_file_id = drive_service.find_file_in_folder(drive_folder_id, "manifest.json")
                    if manifest_file_id:
                        metadata = drive_service.read_json_file(manifest_file_id)
                        members = metadata.get("members", [])
                        if user_email in members:
                            members.remove(user_email)
                            metadata["members"] = members
                            # Gravar manifest.json atualizado no Drive
                            drive_service.write_json_file(drive_folder_id, "manifest.json", metadata, file_id=manifest_file_id)
                            print(f"[Drive] Removido o usuário {user_email} da lista de membros remota do workspace {workspace_id}.")
                except Exception as e:
                    print(f"Erro ao tentar remover participação do convidado no Drive: {e}")

            # Deletar assets e workspace
            conn.execute("DELETE FROM local_assets WHERE workspace_id = ?", (workspace_id,))
            conn.execute("DELETE FROM local_workspaces WHERE id = ?", (workspace_id,))
            
            # Adicionar na lista de ignorados para evitar redescoberta automática do Drive
            conn.execute("INSERT OR REPLACE INTO ignored_workspaces (id) VALUES (?)", (workspace_id,))
            conn.commit()

            # Deletar pasta local física (.gameflow e arquivos)
            if local_path and os.path.exists(local_path):
                import shutil
                try:
                    shutil.rmtree(local_path)
                except Exception as e:
                    print(f"Erro ao remover pasta física local na exclusão: {e}")
        finally:
            conn.close()
        return True

    def unignore_workspace(self, workspace_id: str) -> None:
        """Remove o workspace da lista de ignorados quando importado ou aceito manualmente."""
        conn = self._db.get_connection()
        try:
            conn.execute("DELETE FROM ignored_workspaces WHERE id = ?", (workspace_id,))
            conn.commit()
        finally:
            conn.close()


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

    def get_remote_subfolder_id(self, parent_folder_id: str, subpath: str, drive_service) -> Optional[str]:
        if not subpath:
            return parent_folder_id
        if not drive_service or not drive_service.is_authenticated or parent_folder_id == "demo_folder":
            return "demo_folder"

        parts = [p for p in subpath.replace("\\", "/").split("/") if p]
        current_id = parent_folder_id
        for part in parts:
            query = f"'{current_id}' in parents and name = '{part}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            results = drive_service._service.files().list(q=query, fields="files(id)").execute(http=drive_service._get_http())
            files = results.get("files", [])
            if files:
                current_id = files[0].get("id")
            else:
                return None
        return current_id

    def get_workspace_assets_sync_status(self, workspace_id: str, drive_service, subpath: str = "") -> List[Asset]:
        """
        Retorna a lista unificada de assets e pastas detectados localmente no diretório do workspace (dentro de subpath)
        e remotamente no Google Drive, mapeando os status correspondentes.
        """
        ws = self.get_workspace_by_id(workspace_id)
        if not ws or not ws.local_path:
            return []

        target_dir = os.path.join(ws.local_path, subpath)
        os.makedirs(target_dir, exist_ok=True)

        # 1. Escanear diretório local atual
        local_files = {}
        for entry in os.scandir(target_dir):
            if entry.name == ".gameflow":
                continue
            if entry.is_dir():
                local_files[entry.name] = {
                    "is_dir": True,
                    "path": entry.path,
                    "size": 0
                }
            else:
                local_files[entry.name] = {
                    "is_dir": False,
                    "path": entry.path,
                    "size": entry.stat().st_size
                }

        # 2. Obter arquivos remotos da subpasta correspondente no Drive
        remote_assets = []
        remote_parent_id = self.get_remote_subfolder_id(ws.drive_folder_id, subpath, drive_service)

        if drive_service and drive_service.is_authenticated and remote_parent_id:
            try:
                query = f"'{remote_parent_id}' in parents and trashed = false"
                results = drive_service._service.files().list(q=query, fields="files(id, name, mimeType, size, modifiedTime)").execute(http=drive_service._get_http())
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
                print(f"Erro ao obter arquivos remotos no subpath {subpath}: {e}")

        # 3. Adicionar arquivos locais pendentes de envio
        for name, info in local_files.items():
            mime = "application/vnd.google-apps.folder" if info["is_dir"] else "application/octet-stream"
            remote_assets.append(Asset(
                id=None,
                name=name,
                mime_type=mime,
                size=info["size"],
                local_path=info["path"],
                status=SyncStatus.LOCAL_ONLY,
                modified_time=datetime.now().strftime("%Y-%m-%d %H:%M")
            ))

        # Ordenar pastas primeiro, depois arquivos
        remote_assets.sort(key=lambda x: (x.mime_type != "application/vnd.google-apps.folder", x.name.lower()))
        return remote_assets

    def create_workspace_folder(self, workspace_id: str, subpath: str, folder_name: str, drive_service) -> bool:
        """Cria um diretório local e remoto na estrutura de subpastas."""
        ws = self.get_workspace_by_id(workspace_id)
        if not ws or not ws.local_path:
            return False

        # Criar localmente
        local_dir = os.path.join(ws.local_path, subpath, folder_name)
        os.makedirs(local_dir, exist_ok=True)

        # Criar no Drive
        if drive_service and drive_service.is_authenticated and ws.drive_folder_id != "demo_folder":
            try:
                parent_id = self.get_remote_subfolder_id(ws.drive_folder_id, subpath, drive_service)
                if parent_id:
                    # Verificar se já existe remoto
                    query = f"'{parent_id}' in parents and name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
                    results = drive_service._service.files().list(q=query, fields="files(id)").execute(http=drive_service._get_http())
                    if not results.get("files"):
                        body = {
                            "name": folder_name,
                            "mimeType": "application/vnd.google-apps.folder",
                            "parents": [parent_id]
                        }
                        drive_service._service.files().create(body=body).execute(http=drive_service._get_http())
            except Exception as e:
                print(f"Erro ao criar pasta remota no Drive: {e}")
        return True

    def rename_workspace_item(self, workspace_id: str, subpath: str, old_name: str, new_name: str, drive_service) -> bool:
        """Renomeia um arquivo ou pasta local e atualiza correspondência remota se houver."""
        ws = self.get_workspace_by_id(workspace_id)
        if not ws or not ws.local_path:
            return False

        local_old = os.path.join(ws.local_path, subpath, old_name)
        local_new = os.path.join(ws.local_path, subpath, new_name)

        if os.path.exists(local_old):
            try:
                os.rename(local_old, local_new)
            except Exception as e:
                print(f"Erro ao renomear item localmente: {e}")
                return False

        # Renomear no Drive
        if drive_service and drive_service.is_authenticated and ws.drive_folder_id != "demo_folder":
            try:
                parent_id = self.get_remote_subfolder_id(ws.drive_folder_id, subpath, drive_service)
                if parent_id:
                    query = f"'{parent_id}' in parents and name = '{old_name}' and trashed = false"
                    results = drive_service._service.files().list(q=query, fields="files(id)").execute(http=drive_service._get_http())
                    files = results.get("files", [])
                    if files:
                        fid = files[0].get("id")
                        drive_service._service.files().update(fileId=fid, body={"name": new_name}).execute(http=drive_service._get_http())
            except Exception as e:
                print(f"Erro ao renomear item no Drive: {e}")
        return True

    def delete_workspace_item(self, workspace_id: str, subpath: str, name: str, drive_service) -> bool:
        """Remove arquivo ou diretório localmente e envia comando de exclusão/lixeira no Drive."""
        ws = self.get_workspace_by_id(workspace_id)
        if not ws or not ws.local_path:
            return False

        local_path = os.path.join(ws.local_path, subpath, name)
        if os.path.exists(local_path):
            try:
                if os.path.isdir(local_path):
                    import shutil
                    shutil.rmtree(local_path)
                else:
                    os.remove(local_path)
            except Exception as e:
                print(f"Erro ao remover local: {e}")
                return False

        # Remover no SQLite local cache
        conn = self._db.get_connection()
        try:
            conn.execute("DELETE FROM local_assets WHERE workspace_id = ? AND name = ?", (workspace_id, name))
            conn.commit()
        finally:
            conn.close()

        # Enviar para lixeira no Drive
        if drive_service and drive_service.is_authenticated and ws.drive_folder_id != "demo_folder":
            try:
                parent_id = self.get_remote_subfolder_id(ws.drive_folder_id, subpath, drive_service)
                if parent_id:
                    query = f"'{parent_id}' in parents and name = '{name}' and trashed = false"
                    results = drive_service._service.files().list(q=query, fields="files(id)").execute(http=drive_service._get_http())
                    files = results.get("files", [])
                    if files:
                        fid = files[0].get("id")
                        drive_service._service.files().update(fileId=fid, body={"trashed": True}).execute(http=drive_service._get_http())
            except Exception as e:
                print(f"Erro ao mandar item para a lixeira no Drive: {e}")
        return True

    def move_workspace_item(self, workspace_id: str, source_subpath: str, dest_subpath: str, name: str, drive_service) -> bool:
        """Move o arquivo localmente e reorganiza as pastas correspondentes no Drive."""
        ws = self.get_workspace_by_id(workspace_id)
        if not ws or not ws.local_path:
            return False

        local_src = os.path.join(ws.local_path, source_subpath, name)
        local_dest_dir = os.path.join(ws.local_path, dest_subpath)
        local_dest = os.path.join(local_dest_dir, name)

        os.makedirs(local_dest_dir, exist_ok=True)
        if os.path.exists(local_src):
            try:
                import shutil
                shutil.move(local_src, local_dest)
            except Exception as e:
                print(f"Erro ao mover arquivo localmente: {e}")
                return False

        # Atualizar no SQLite local cache
        conn = self._db.get_connection()
        try:
            conn.execute("UPDATE local_assets SET local_path = ? WHERE workspace_id = ? AND name = ?", (local_dest, workspace_id, name))
            conn.commit()
        finally:
            conn.close()

        # Mover no Drive
        if drive_service and drive_service.is_authenticated and ws.drive_folder_id != "demo_folder":
            try:
                src_parent_id = self.get_remote_subfolder_id(ws.drive_folder_id, source_subpath, drive_service)
                dest_parent_id = self.get_remote_subfolder_id(ws.drive_folder_id, dest_subpath, drive_service)

                if src_parent_id and dest_parent_id:
                    query = f"'{src_parent_id}' in parents and name = '{name}' and trashed = false"
                    results = drive_service._service.files().list(q=query, fields="files(id)").execute(http=drive_service._get_http())
                    files = results.get("files", [])
                    if files:
                        fid = files[0].get("id")
                        # Mover mudando a referência de parents no Drive
                        drive_service._service.files().update(
                            fileId=fid,
                            addParents=dest_parent_id,
                            removeParents=src_parent_id,
                            fields="id, parents"
                        ).execute(http=drive_service._get_http())
            except Exception as e:
                print(f"Erro ao mover no Drive: {e}")
        return True

    def sync_asset(self, workspace_id: str, asset: Asset, drive_service, author_email: str, subpath: str = "") -> bool:
        """
        Sincroniza um asset individual no subcaminho atual:
        - REMOTE_ONLY (Nuvem): baixa do Drive para a pasta local.
        - LOCAL_ONLY (Local): envia do local para a pasta do Drive.
        """
        ws = self.get_workspace_by_id(workspace_id)
        if not ws or not ws.local_path:
            return False

        # Sincronização de arquivo da nuvem para o local
        if asset.status == SyncStatus.REMOTE_ONLY and drive_service and drive_service.is_authenticated:
            try:
                dest_path = os.path.join(ws.local_path, subpath, asset.name)
                request = drive_service._service.files().get_media(fileId=asset.id)
                with open(dest_path, "wb") as f:
                    f.write(request.execute(http=drive_service._get_http()))
                
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
                parent_id = self.get_remote_subfolder_id(ws.drive_folder_id, subpath, drive_service)
                if not parent_id:
                    return False

                if asset.mime_type == "application/vnd.google-apps.folder":
                    # Criar pasta no Drive
                    body = {
                        "name": asset.name,
                        "mimeType": "application/vnd.google-apps.folder",
                        "parents": [parent_id]
                    }
                    drive_service._service.files().create(body=body).execute(http=drive_service._get_http())
                    return True
                else:
                    # Enviar arquivo
                    from googleapiclient.http import MediaFileUpload
                    file_metadata = {
                        'name': asset.name,
                        'parents': [parent_id]
                    }
                    media = MediaFileUpload(asset.local_path, mimetype=asset.mime_type or 'application/octet-stream', resumable=True)
                    file = drive_service._service.files().create(body=file_metadata, media_body=media, fields='id').execute(http=drive_service._get_http())
                    uploaded_id = file.get('id')

                    asset.id = uploaded_id
                    self.notify_asset_added(workspace_id, author_email, asset, drive_service)
                    return True
            except Exception as e:
                print(f"Erro ao enviar asset no sync: {e}")
                return False

        return False

    def upload_and_notify_asset(self, workspace_id: str, subpath: str, filename: str, local_path: str, drive_service, author_email: str) -> bool:
        """
        Realiza o upload real de um arquivo de documentos ou mídias para a subpasta no Google Drive,
        registra o asset no SQLite local e emite uma notificação em lote para a equipe.
        """
        ws = self.get_workspace_by_id(workspace_id)
        if not ws:
            return False
        try:
            parent_id = self.get_remote_subfolder_id(ws.drive_folder_id, subpath, drive_service)
            if not parent_id:
                return False

            # Enviar arquivo
            from googleapiclient.http import MediaFileUpload
            file_metadata = {
                'name': filename,
                'parents': [parent_id]
            }
            
            import mimetypes
            mime_type, _ = mimetypes.guess_type(local_path)
            if not mime_type:
                mime_type = "application/octet-stream"

            media = MediaFileUpload(local_path, mimetype=mime_type, resumable=True)
            file = drive_service._service.files().create(body=file_metadata, media_body=media, fields='id, size, mimeType').execute(http=drive_service._get_http())
            uploaded_id = file.get('id')

            # Anexar no SQLite local cache
            size = int(file.get("size", 0)) or os.path.getsize(local_path)
            mime = file.get("mimeType", mime_type)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

            conn = self._db.get_connection()
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO local_assets (id, workspace_id, name, mime_type, size, local_path, status, last_sync) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (uploaded_id, workspace_id, filename, mime, size, local_path, "SYNCHRONIZED", timestamp)
                )
                conn.commit()
            finally:
                conn.close()

            # Enviar alerta/notificação de equipe
            from domain import Asset
            asset = Asset(id=uploaded_id, name=filename, mime_type=mime, size=size, local_path=local_path)
            self.notify_asset_added(workspace_id, author_email, asset, drive_service)
            return True
        except Exception as e:
            print(f"Erro no upload do asset inserido: {e}")
            return False



