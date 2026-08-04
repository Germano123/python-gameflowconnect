import uuid
import os
import sqlite3
import json
from typing import List, Optional
from datetime import datetime
from domain import Workspace, WorkspaceNotification, Asset, SyncStatus, AssetType
from adapters.database import LocalDatabase

def _hide_folder(path: str) -> None:
    """Oculta a pasta no Windows definindo o atributo de arquivo FILE_ATTRIBUTE_HIDDEN."""
    if os.name == "nt":
        try:
            import ctypes
            # FILE_ATTRIBUTE_HIDDEN = 2
            ctypes.windll.kernel32.SetFileAttributesW(path, 2)
        except Exception:
            try:
                import subprocess
                subprocess.run(["attrib", "+h", path], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

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
        Cria um workspace localmente no SQLite, a estrutura correspondente no Google Drive,
        e gera as subpastas ocultas em .gameflow/ (objects, commits, branches, etc.).
        """
        ws_id = f"ws_{uuid.uuid4().hex[:6]}"
        
        # 1. Inicializar no Google Drive (remoto)
        drive_folder_id = "demo_folder"
        if drive_service and drive_service.is_authenticated:
            try:
                gameflow_root_id = drive_service.get_or_create_root_folder("GameFlow.app")
                drive_folder_id = drive_service.create_folder(name, parent_folder_id=gameflow_root_id)
                
                # Criar a pasta remota oculta .gameflow
                gameflow_folder_id = drive_service.create_folder(".gameflow", parent_folder_id=drive_folder_id)
                
                # Criar subpastas remotas do DVCS
                drive_service.create_folder("objects", parent_folder_id=gameflow_folder_id)
                drive_service.create_folder("commits", parent_folder_id=gameflow_folder_id)
                drive_service.create_folder("branches", parent_folder_id=gameflow_folder_id)
                manifests_folder_id = drive_service.create_folder("manifests", parent_folder_id=gameflow_folder_id)
                drive_service.create_folder("snapshots", parent_folder_id=gameflow_folder_id)
                drive_service.create_folder("users", parent_folder_id=gameflow_folder_id)
                drive_service.create_folder("locks", parent_folder_id=gameflow_folder_id)

                # Salvar manifesto inicial project.json remoto
                project_manifest = {
                    "project_id": ws_id,
                    "name": name,
                    "description": description,
                    "engine": engine,
                    "owner": owner,
                    "active_branches": ["main"],
                    "heads": {
                        "main": None
                    },
                    "users": {
                        owner: {
                            "role": "administrator",
                            "last_seen": datetime.now().isoformat()
                        }
                    }
                }
                drive_service.write_json_file(manifests_folder_id, "project.json", project_manifest)
                
                # Registrar no arquivo central gameflow.json
                drive_service.add_workspace_to_registry(ws_id, name, drive_folder_id)
            except Exception as e:
                print(f"Erro ao criar estrutura remota GFC-DVCS no Drive: {e}")

        # 2. Inicializar localmente
        from state import AppState
        path = local_path or os.path.abspath(os.path.join(AppState.local_base_dir, name))
        os.makedirs(path, exist_ok=True)

        # Criar a pasta oculta .gameflow e suas subpastas locais
        gameflow_dir = os.path.join(path, ".gameflow")
        for sub in ["objects", "commits", "branches", "manifests", "snapshots", "users", "locks"]:
            os.makedirs(os.path.join(gameflow_dir, sub), exist_ok=True)
        _hide_folder(gameflow_dir)

        # Escrever arquivos iniciais locais
        project_manifest = {
            "project_id": ws_id,
            "name": name,
            "description": description,
            "engine": engine,
            "owner": owner,
            "active_branches": ["main"],
            "heads": {
                "main": None
            },
            "users": {
                owner: {
                    "role": "administrator",
                    "last_seen": datetime.now().isoformat()
                }
            }
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
            with open(os.path.join(gameflow_dir, "manifests", "project.json"), "w", encoding="utf-8") as f:
                json.dump(project_manifest, f, indent=2, ensure_ascii=False)
            with open(os.path.join(gameflow_dir, "config.json"), "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar arquivos locais do GFC-DVCS: {e}")

        created_date = datetime.now().strftime("%Y-%m-%d")
        conn = self._db.get_connection()
        try:
            # Salvar Workspace local
            conn.execute(
                "INSERT INTO local_workspaces (id, name, description, engine, drive_folder_id, local_path, owner, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (ws_id, name, description, engine, drive_folder_id, path, owner, created_date)
            )
            # Salvar ponteiro de branch local inicial
            conn.execute(
                "INSERT INTO local_branches (name, head_commit_hash, workspace_id) VALUES (?, ?, ?)",
                ("main", None, ws_id)
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
                        _hide_folder(gameflow_dir)

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

                manifest_path = os.path.join(item_path, ".gameflow", "manifests", "project.json")
                if not os.path.exists(manifest_path):
                    manifest_path = os.path.join(item_path, ".gameflow", "manifest.json")
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, "r", encoding="utf-8") as f:
                            metadata = json.load(f)
                        
                        ws_id = metadata.get("project_id") or metadata.get("id")
                        ws_name = metadata.get("name", item)
                        ws_desc = metadata.get("description", "")
                        ws_engine = metadata.get("engine", "")
                        ws_owner = metadata.get("owner", "")
                        ws_drive_id = metadata.get("drive_folder_id")
                        if not ws_drive_id:
                            config_path = os.path.join(item_path, ".gameflow", "config.json")
                            if os.path.exists(config_path):
                                try:
                                    with open(config_path, "r", encoding="utf-8") as cf:
                                        config_data = json.load(cf)
                                        ws_drive_id = config_data.get("google_drive_folder_id")
                                except Exception:
                                    pass
                        if not ws_drive_id:
                            ws_drive_id = "demo_folder"

                        ws_created = metadata.get("created_at", datetime.now().strftime("%Y-%m-%d"))

                        if ws_id and ws_id not in existing_ids and ws_id not in ignored_ids:
                            conn.execute(
                                """
                                INSERT INTO local_workspaces (id, name, description, engine, owner, drive_folder_id, local_path, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (ws_id, ws_name, ws_desc, ws_engine, ws_owner, ws_drive_id, item_path, ws_created)
                            )
                            if "project_id" in metadata:
                                conn.execute(
                                    "INSERT OR IGNORE INTO local_branches (name, head_commit_hash, workspace_id) VALUES (?, ?, ?)",
                                    ("main", None, ws_id)
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
            if drive_service and drive_service.is_authenticated and drive_folder_id != "demo_folder" and user_email and owner and owner != user_email:
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

            # Remover do registro central gameflow.json
            if drive_service and drive_service.is_authenticated:
                try:
                    drive_service.remove_workspace_from_registry(workspace_id)
                except Exception as e:
                    print(f"Erro ao remover workspace do registro gameflow.json: {e}")

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

    def get_or_create_remote_subfolder_id(self, parent_folder_id: str, subpath: str, drive_service) -> Optional[str]:
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
                body = {
                    "name": part,
                    "mimeType": "application/vnd.google-apps.folder",
                    "parents": [current_id]
                }
                new_folder = drive_service._service.files().create(body=body, fields="id").execute(http=drive_service._get_http())
                current_id = new_folder.get("id")
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

        categories = self._load_categories(ws.local_path)

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

        # 2. Obter arquivos remotos da subpasta correspondente no Drive (com cache local)
        remote_assets = []
        remote_parent_id = self.get_remote_subfolder_id(ws.drive_folder_id, subpath, drive_service)

        import time
        now = time.time()
        cache = self._load_remote_cache(ws.local_path)
        cache_entry = cache.get("subpaths", {}).get(subpath, {})
        cache_time = cache_entry.get("timestamp", 0)

        # Se o cache for válido (menos de 30 segundos) e não for demo_folder
        if ws.drive_folder_id != "demo_folder" and now - cache_time < 30:
            files = cache_entry.get("files", [])
            # Carregar tracked_files para detecção de arquivos externos do Drive
            tracked_data = self._load_tracked_files(ws, drive_service)
            tracked_files = tracked_data.get("files", {})
            for f in files:
                name = f.get("name")
                if name == ".gameflow" or name in ["manifest.json", "config.json", "activity_log.json"]:
                    continue
                size = int(f.get("size", 0))
                fid = f.get("id")
                mime = f.get("mimeType")
                modified = f.get("modifiedTime", "")
                
                status = SyncStatus.REMOTE_ONLY
                if fid not in tracked_files:
                    status = SyncStatus.UNTRACKED_REMOTE
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
        elif drive_service and drive_service.is_authenticated and remote_parent_id and remote_parent_id != "demo_folder":
            try:
                query = f"'{remote_parent_id}' in parents and trashed = false"
                results = drive_service._service.files().list(q=query, fields="files(id, name, mimeType, size, modifiedTime)").execute(http=drive_service._get_http())
                files = results.get("files", [])
                # Carregar tracked_files para detecção de arquivos externos do Drive
                tracked_data = self._load_tracked_files(ws, drive_service)
                tracked_files = tracked_data.get("files", {})
                
                # Atualizar cache
                cache["subpaths"][subpath] = {
                    "timestamp": now,
                    "files": files
                }
                self._save_remote_cache(ws.local_path, cache)

                for f in files:
                    name = f.get("name")
                    if name == ".gameflow" or name in ["manifest.json", "config.json", "activity_log.json"]:
                        continue

                    size = int(f.get("size", 0))
                    fid = f.get("id")
                    mime = f.get("mimeType")
                    modified = f.get("modifiedTime", "")

                    status = SyncStatus.REMOTE_ONLY
                    if fid not in tracked_files:
                        status = SyncStatus.UNTRACKED_REMOTE
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

        # Aplicar as categorias resolvidas em cada asset
        for asset in remote_assets:
            rel_path = os.path.join(subpath, asset.name).replace("\\", "/")
            if rel_path.startswith("/"):
                rel_path = rel_path[1:]
            asset.category = categories.get(rel_path)

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

    def _load_categories(self, workspace_path: str) -> dict:
        path = os.path.join(workspace_path, ".gameflow", "categories.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_categories(self, workspace_path: str, categories: dict, drive_service, ws_drive_id: str) -> None:
        os.makedirs(os.path.join(workspace_path, ".gameflow"), exist_ok=True)
        path = os.path.join(workspace_path, ".gameflow", "categories.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(categories, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar categories.json local: {e}")

        # Ocultar pasta .gameflow local
        _hide_folder(os.path.join(workspace_path, ".gameflow"))

        # Sincronizar com o Drive se autenticado
        if drive_service and drive_service.is_authenticated and ws_drive_id != "demo_folder":
            try:
                gameflow_root_id = drive_service.get_or_create_root_folder("GameFlow.app")
                query = f"'{gameflow_root_id}' in parents and name = '{os.path.basename(workspace_path)}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
                ws_folder_results = drive_service._service.files().list(q=query, fields="files(id)").execute(http=drive_service._get_http())
                ws_files = ws_folder_results.get("files", [])
                if ws_files:
                    ws_folder_id = ws_files[0].get("id")
                    gf_folder_id = drive_service.find_file_in_folder(ws_folder_id, ".gameflow")
                    if not gf_folder_id:
                        gf_folder_id = drive_service.create_folder(".gameflow", parent_folder_id=ws_folder_id)
                    
                    from adapters.google_drive_adapter import GoogleDriveAdapter
                    adapter = GoogleDriveAdapter(drive_service)
                    adapter.write_metadata(ws_folder_id, ".gameflow", "categories.json", categories)
            except Exception as e:
                print(f"Erro ao sincronizar categories.json com Drive: {e}")

    def sync_categories_metadata(self, ws, drive_service) -> None:
        if not drive_service or not drive_service.is_authenticated or ws.drive_folder_id == "demo_folder":
            return
        try:
            gameflow_root_id = drive_service.get_or_create_root_folder("GameFlow.app")
            query = f"'{gameflow_root_id}' in parents and name = '{ws.name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            ws_folder_results = drive_service._service.files().list(q=query, fields="files(id)").execute(http=drive_service._get_http())
            ws_files = ws_folder_results.get("files", [])
            if ws_files:
                ws_folder_id = ws_files[0].get("id")
                gf_folder_id = drive_service.find_file_in_folder(ws_folder_id, ".gameflow")
                if gf_folder_id:
                    file_id = drive_service.find_file_in_folder(gf_folder_id, "categories.json")
                    if file_id:
                        remote_data = drive_service.read_json_file(file_id)
                        if remote_data:
                            local_gf = os.path.join(ws.local_path, ".gameflow")
                            os.makedirs(local_gf, exist_ok=True)
                            local_json_path = os.path.join(local_gf, "categories.json")
                            with open(local_json_path, "w", encoding="utf-8") as f:
                                json.dump(remote_data, f, indent=2, ensure_ascii=False)
                            _hide_folder(local_gf)
        except Exception as e:
            print(f"Erro ao sincronizar categories.json do Drive para local: {e}")

    def _load_remote_cache(self, local_path: str) -> dict:
        cache_path = os.path.join(local_path, ".gameflow", "remote_cache.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"subpaths": {}}

    def _save_remote_cache(self, local_path: str, cache_data: dict) -> None:
        local_gf = os.path.join(local_path, ".gameflow")
        os.makedirs(local_gf, exist_ok=True)
        cache_path = os.path.join(local_gf, "remote_cache.json")
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            _hide_folder(local_gf)
        except Exception as e:
            print(f"Erro ao salvar remote_cache.json: {e}")

    def sync_workspace_metadata(self, ws, drive_service, on_complete=None) -> None:
        """
        Sincroniza automaticamente a pasta .gameflow (metadados do sistema) com o Drive:
        - Sincroniza as categorias (categories.json).
        - Sincroniza os commits, branches e histórico do GFC-DVCS em background de forma transparente.
        - Executa o download automático de arquivos REMOTE_ONLY.
        - Utiliza cache local de 30 segundos para evitar acessos excessivos de rede.
        - Executa o callback on_complete quando a sincronização é finalizada com sucesso.
        """
        if not drive_service or not drive_service.is_authenticated or ws.drive_folder_id == "demo_folder":
            return

        import time
        last_sync_path = os.path.join(ws.local_path, ".gameflow", "last_sync.json")
        now = time.time()
        
        if os.path.exists(last_sync_path):
            try:
                with open(last_sync_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    last_time = data.get("last_metadata_sync", 0)
                    if now - last_time < 30: # 30 segundos de cooldown
                        return
            except Exception:
                pass

        # 1. Sincronizar categorias compartilhadas
        self.sync_categories_metadata(ws, drive_service)

        # 1.1 Sincronizar arquivos trackeados (tracked_files.json)
        try:
            gameflow_root_id = drive_service.get_or_create_root_folder("GameFlow.app")
            query = f"'{gameflow_root_id}' in parents and name = '{ws.name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
            ws_folder_results = drive_service._service.files().list(q=query, fields="files(id)").execute(http=drive_service._get_http())
            ws_files = ws_folder_results.get("files", [])
            if ws_files:
                ws_folder_id = ws_files[0].get("id")
                gf_folder_id = drive_service.find_file_in_folder(ws_folder_id, ".gameflow")
                if gf_folder_id:
                    file_id = drive_service.find_file_in_folder(gf_folder_id, "tracked_files.json")
                    if file_id:
                        remote_data = drive_service.read_json_file(file_id)
                        if remote_data:
                            local_gf = os.path.join(ws.local_path, ".gameflow")
                            os.makedirs(local_gf, exist_ok=True)
                            local_json_path = os.path.join(local_gf, "tracked_files.json")
                            with open(local_json_path, "w", encoding="utf-8") as f:
                                json.dump(remote_data, f, indent=2, ensure_ascii=False)
                            _hide_folder(local_gf)
        except Exception as e:
            print(f"Erro ao sincronizar tracked_files.json do Drive: {e}")

        # 2. Sincronizar commits e branches GFC-DVCS se for o caso
        manifest_path = os.path.join(ws.local_path, ".gameflow", "manifests", "project.json")
        if os.path.exists(manifest_path):
            try:
                from adapters.google_drive_adapter import GoogleDriveAdapter
                from use_cases.gfc_dvcs_use_cases import GFCDVCSUseCase
                
                drive_adapter = GoogleDriveAdapter(drive_service)
                dvcs = GFCDVCSUseCase()
                dvcs.sync_workspace(
                    workspace_id=ws.id,
                    local_path=ws.local_path,
                    drive_folder_id=ws.drive_folder_id,
                    drive_adapter=drive_adapter,
                    active_branch="main"
                )
                print(f"[Sync] Metadados GFC-DVCS do workspace {ws.name} (.gameflow/) sincronizados automaticamente.")
            except Exception as e:
                print(f"Erro ao sincronizar metadados GFC-DVCS em background: {e}")

        # 3. Baixar automaticamente os arquivos REMOTE_ONLY (que existem no Drive mas não localmente)
        try:
            self.auto_sync_local_files(ws.id, drive_service)
        except Exception as e:
            print(f"Erro ao baixar arquivos REMOTE_ONLY no auto-sync: {e}")

        # Gravar timestamp de sincronismo
        try:
            local_gf = os.path.join(ws.local_path, ".gameflow")
            os.makedirs(local_gf, exist_ok=True)
            with open(last_sync_path, "w", encoding="utf-8") as f:
                json.dump({"last_metadata_sync": now}, f)
            _hide_folder(local_gf)
        except Exception:
            pass

        if on_complete:
            try:
                on_complete()
            except Exception as e:
                print(f"Erro ao executar callback de sincronização: {e}")

    def auto_sync_local_files(self, workspace_id: str, drive_service) -> bool:
        """
        Varre recursivamente o workspace e realiza o download de todos os arquivos REMOTE_ONLY
        (existentes no Drive mas faltantes localmente).
        """
        ws = self.get_workspace_by_id(workspace_id)
        if not ws or not ws.local_path or not drive_service or not drive_service.is_authenticated or ws.drive_folder_id == "demo_folder":
            return False

        def scan_and_download(subpath: str) -> bool:
            # Forçar bypass do cache para garantir a listagem real do Drive no auto-sync
            cache_path = os.path.join(ws.local_path, ".gameflow", "remote_cache.json")
            if os.path.exists(cache_path):
                try:
                    # Invalidar temporariamente a entrada deste subpath para obter dados atualizados
                    with open(cache_path, "r", encoding="utf-8") as f:
                        cache = json.load(f)
                    if subpath in cache.get("subpaths", {}):
                        cache["subpaths"][subpath]["timestamp"] = 0
                    with open(cache_path, "w", encoding="utf-8") as f:
                        json.dump(cache, f)
                except Exception:
                    pass

            assets = self.get_workspace_assets_sync_status(workspace_id, drive_service, subpath)
            success = True
            for asset in assets:
                if asset.mime_type == "application/vnd.google-apps.folder":
                    child_subpath = os.path.join(subpath, asset.name).replace("\\", "/")
                    if not scan_and_download(child_subpath):
                        success = False
                elif asset.status == SyncStatus.REMOTE_ONLY or asset.status == SyncStatus.UNTRACKED_REMOTE:
                    print(f"[Auto-Sync] Baixando arquivo REMOTE_ONLY/UNTRACKED_REMOTE: {asset.name} em {subpath}")
                    if not self.sync_asset(workspace_id, asset, drive_service, None, subpath):
                        success = False
            return success

        return scan_and_download("")

    def _load_tracked_files(self, ws, drive_service) -> dict:
        local_gf = os.path.join(ws.local_path, ".gameflow")
        local_path = os.path.join(local_gf, "tracked_files.json")
        if os.path.exists(local_path):
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"files": {}}

    def _save_tracked_files(self, ws, tracked_data: dict, drive_service) -> None:
        local_gf = os.path.join(ws.local_path, ".gameflow")
        os.makedirs(local_gf, exist_ok=True)
        local_path = os.path.join(local_gf, "tracked_files.json")
        try:
            with open(local_path, "w", encoding="utf-8") as f:
                json.dump(tracked_data, f, indent=2, ensure_ascii=False)
            _hide_folder(local_gf)
            
            if drive_service and drive_service.is_authenticated and ws.drive_folder_id != "demo_folder":
                from adapters.google_drive_adapter import GoogleDriveAdapter
                gameflow_root_id = drive_service.get_or_create_root_folder("GameFlow.app")
                query = f"'{gameflow_root_id}' in parents and name = '{ws.name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
                ws_folder_results = drive_service._service.files().list(q=query, fields="files(id)").execute(http=drive_service._get_http())
                ws_files = ws_folder_results.get("files", [])
                if ws_files:
                    ws_folder_id = ws_files[0].get("id")
                    adapter = GoogleDriveAdapter(drive_service)
                    adapter.write_metadata(ws_folder_id, ".gameflow", "tracked_files.json", tracked_data)
        except Exception as e:
            print(f"Erro ao salvar tracked_files.json: {e}")

    def mark_file_as_tracked(self, workspace_id: str, drive_file_id: str, path_name: str, drive_service) -> None:
        ws = self.get_workspace_by_id(workspace_id)
        if not ws or not ws.local_path or not drive_file_id:
            return
        
        from datetime import datetime
        tracked_data = self._load_tracked_files(ws, drive_service)
        if "files" not in tracked_data:
            tracked_data["files"] = {}
            
        tracked_data["files"][drive_file_id] = {
            "name": path_name,
            "tracked_at": datetime.now().isoformat()
        }
        self._save_tracked_files(ws, tracked_data, drive_service)

    def set_item_category(self, workspace_id: str, item_subpath: str, item_name: str, category: Optional[str], drive_service) -> bool:
        ws = self.get_workspace_by_id(workspace_id)
        if not ws or not ws.local_path:
            return False

        categories = self._load_categories(ws.local_path)
        rel_path = os.path.join(item_subpath, item_name).replace("\\", "/")
        if rel_path.startswith("/"):
            rel_path = rel_path[1:]

        if category:
            categories[rel_path] = category
        else:
            categories.pop(rel_path, None)

        self._save_categories(ws.local_path, categories, drive_service, ws.drive_folder_id)

        # Atualizar cache local no banco
        conn = self._db.get_connection()
        try:
            conn.execute("UPDATE local_assets SET category = ? WHERE workspace_id = ? AND name = ?", (category, workspace_id, item_name))
            conn.commit()
        finally:
            conn.close()
        return True

    def sync_folder(self, workspace_id: str, folder_name: str, drive_service, author_email: str, subpath: str = "") -> bool:
        """
        Sincroniza recursivamente todos os arquivos e subpastas de uma pasta específica.
        - Obtém a listagem do status de sincronização daquela pasta específica.
        - Executa o download/upload recursivo em profundidade (DFS).
        """
        ws = self.get_workspace_by_id(workspace_id)
        if not ws or not ws.local_path:
            return False

        if ws.drive_folder_id == "demo_folder":
            print(f"[Sync] Sincronização de pasta '{folder_name}' ignorada (modo offline/demo_folder).")
            return True

        # 1. Garantir que a própria pasta está criada/sincronizada no Drive
        folder_asset = Asset(
            id=None,
            name=folder_name,
            mime_type="application/vnd.google-apps.folder",
            status=SyncStatus.LOCAL_ONLY
        )
        
        parent_id = self.get_remote_subfolder_id(ws.drive_folder_id, subpath, drive_service)
        if parent_id and parent_id != "demo_folder" and drive_service and drive_service.is_authenticated:
            try:
                query = f"'{parent_id}' in parents and name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
                results = drive_service._service.files().list(q=query, fields="files(id)").execute(http=drive_service._get_http())
                files = results.get("files", [])
                if files:
                    folder_asset.id = files[0].get("id")
                    folder_asset.status = SyncStatus.SYNCHRONIZED
            except Exception as e:
                print(f"Erro ao verificar existência da pasta no Drive: {e}")

        # Sincroniza a pasta em si (criando-a caso seja LOCAL_ONLY)
        self.sync_asset(workspace_id, folder_asset, drive_service, author_email, subpath)

        # Caminho relativo atualizado da pasta que está sendo sincronizada
        current_subpath = os.path.join(subpath, folder_name).replace("\\", "/")
        if current_subpath.startswith("/"):
            current_subpath = current_subpath[1:]

        # 1. Obter a lista de assets dentro da pasta
        assets = self.get_workspace_assets_sync_status(workspace_id, drive_service, current_subpath)
        
        success = True
        for asset in assets:
            if asset.mime_type == "application/vnd.google-apps.folder":
                # É uma subpasta. Sincroniza recursivamente.
                sub_success = self.sync_folder(workspace_id, asset.name, drive_service, author_email, current_subpath)
                if not sub_success:
                    success = False
            else:
                # É um arquivo. Sincroniza individualmente.
                file_success = self.sync_asset(workspace_id, asset, drive_service, author_email, current_subpath)
                if not file_success:
                    success = False
        return success

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

        # Se já está sincronizado, não há nada a fazer, retorna sucesso
        if asset.status == SyncStatus.SYNCHRONIZED:
            return True

        # Sincronização de arquivo da nuvem para o local
        if (asset.status == SyncStatus.REMOTE_ONLY or asset.status == SyncStatus.UNTRACKED_REMOTE) and drive_service and drive_service.is_authenticated and ws.drive_folder_id != "demo_folder":
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
                # Registrar tracking no arquivo de metadados
                self.mark_file_as_tracked(workspace_id, asset.id, os.path.join(subpath, asset.name).replace("\\", "/"), drive_service)
                return True
            except Exception as e:
                print(f"Erro ao baixar asset no sync: {e}")
                return False

        # Sincronização de arquivo local para a nuvem
        elif asset.status == SyncStatus.LOCAL_ONLY and drive_service and drive_service.is_authenticated and ws.drive_folder_id != "demo_folder":
            try:
                parent_id = self.get_or_create_remote_subfolder_id(ws.drive_folder_id, subpath, drive_service)
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
                    self.mark_file_as_tracked(workspace_id, uploaded_id, os.path.join(subpath, asset.name).replace("\\", "/"), drive_service)
                    return True
            except Exception as e:
                print(f"Erro ao enviar asset no sync: {e}")
                return False

        print(f"[Sync] Aviso: nenhuma ação de sincronização executada para o asset '{asset.name}' (status: {asset.status}). Verifique se o Drive está conectado ou se o projeto está no modo demo.")
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
            parent_id = self.get_or_create_remote_subfolder_id(ws.drive_folder_id, subpath, drive_service)
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
            self.mark_file_as_tracked(workspace_id, uploaded_id, os.path.join(subpath, filename).replace("\\", "/"), drive_service)
            return True
        except Exception as e:
            print(f"Erro no upload do asset inserido: {e}")
            return False

    def sync_workspaces_with_registry(self, drive_service, user_email: str) -> None:
        """
        Sincroniza a lista de workspaces local SQLite com o registro remoto gameflow.json no Google Drive.
        - Se uma pasta remota foi excluída/movida para a lixeira no Drive, apaga o workspace localmente.
        - Se um projeto no gameflow.json remoto não existe localmente (e não está nos ignorados),
          importa-o automaticamente.
        """
        if not drive_service or not drive_service.is_authenticated or not user_email:
            return

        try:
            # 1. Obter registro central do Drive
            registry = drive_service.read_gameflow_registry()
            remote_workspaces = registry.get("workspaces", [])
            remote_ids = {w.get("id") for w in remote_workspaces}

            # 2. Obter workspaces locais
            conn = self._db.get_connection()
            try:
                cursor = conn.execute("SELECT id, name, drive_folder_id FROM local_workspaces")
                local_workspaces = cursor.fetchall()
                
                cursor = conn.execute("SELECT id FROM ignored_workspaces")
                ignored_ids = {row["id"] for row in cursor.fetchall()}
            finally:
                conn.close()

            local_ids = {w["id"] for w in local_workspaces}

            # A. DETECÇÃO E LIMPEZA DE PASTAS REMOTAS EXCLUÍDAS DO DRIVE
            for local_ws in local_workspaces:
                ws_id = local_ws["id"]
                folder_id = local_ws["drive_folder_id"]
                
                # Pular remoção automática se for workspace demo_folder
                if folder_id == "demo_folder":
                    continue

                # Se não existe mais no gameflow.json remoto OU a pasta foi deletada/enviada para a lixeira no Drive
                if ws_id not in remote_ids or not drive_service.check_folder_exists(folder_id):
                    print(f"[Sync] Workspace '{local_ws['name']}' ({ws_id}) foi excluído ou está inacessível no Drive. Removendo localmente.")
                    self.delete_workspace(ws_id, drive_service, user_email)  # Remove do banco e limpa pasta local física

            # B. AUTO-IMPORTAÇÃO DE PROJETOS COMPARTILHADOS/NOVOS NO REGISTRO
            for remote_ws in remote_workspaces:
                ws_id = remote_ws.get("id")
                folder_id = remote_ws.get("drive_folder_id")
                name = remote_ws.get("name", "Workspace Compartilhado")
                
                if ws_id and ws_id not in local_ids and ws_id not in ignored_ids:
                    # Verificar se a pasta do projeto ainda existe no Drive antes de importar
                    if drive_service.check_folder_exists(folder_id):
                        # Encontrar o manifesto remoto na pasta (primeiro tenta legado, depois o novo unificado em .gameflow/manifests/project.json)
                        manifest_file_id = drive_service.find_file_in_folder(folder_id, "manifest.json")
                        if not manifest_file_id:
                            try:
                                gameflow_folder_id = drive_service.find_file_in_folder(folder_id, ".gameflow")
                                if gameflow_folder_id:
                                    manifests_folder_id = drive_service.find_file_in_folder(gameflow_folder_id, "manifests")
                                    if manifests_folder_id:
                                        manifest_file_id = drive_service.find_file_in_folder(manifests_folder_id, "project.json")
                            except Exception:
                                pass

                        if manifest_file_id:
                            try:
                                metadata = drive_service.read_json_file(manifest_file_id)
                                members = metadata.get("members", [])
                                if "users" in metadata and not members:
                                    members = list(metadata["users"].keys())
                                
                                # Apenas importar se o usuário atual for membro participante
                                if user_email in members:
                                    print(f"[Sync] Novo workspace descoberto no registro: '{name}' ({ws_id}). Autocadastrando.")
                                    desc = metadata.get("description", "")
                                    engine = metadata.get("engine", "Godot")
                                    owner = metadata.get("owner", "")
                                    created_date = metadata.get("created_at", datetime.now().strftime("%Y-%m-%d"))

                                    from state import AppState
                                    local_path = os.path.abspath(os.path.join(AppState.local_base_dir, name))
                                    os.makedirs(local_path, exist_ok=True)
                                    
                                    # Criar pasta .gameflow local e salvar manifesto
                                    gameflow_dir = os.path.join(local_path, ".gameflow")
                                    os.makedirs(gameflow_dir, exist_ok=True)
                                    _hide_folder(gameflow_dir)
                                    
                                    is_unified = "project_id" in metadata
                                    if is_unified:
                                        os.makedirs(os.path.join(gameflow_dir, "manifests"), exist_ok=True)
                                        for sub in ["objects", "commits", "branches", "snapshots", "users", "locks"]:
                                            os.makedirs(os.path.join(gameflow_dir, sub), exist_ok=True)
                                        manifest_save_path = os.path.join(gameflow_dir, "manifests", "project.json")
                                    else:
                                        manifest_save_path = os.path.join(gameflow_dir, "manifest.json")

                                    with open(manifest_save_path, "w", encoding="utf-8") as f:
                                        json.dump(metadata, f, indent=2, ensure_ascii=False)
                                        
                                    config_data = {
                                        "workspace_id": ws_id,
                                        "engine": engine,
                                        "google_drive_folder_id": folder_id,
                                        "preferencias": {"auto_sync": False, "intervalo_sync_minutos": 15}
                                    }
                                    with open(os.path.join(gameflow_dir, "config.json"), "w", encoding="utf-8") as f:
                                        json.dump(config_data, f, indent=2, ensure_ascii=False)

                                    # Registrar no banco local
                                    conn = self._db.get_connection()
                                    try:
                                        conn.execute(
                                            "INSERT INTO local_workspaces (id, name, description, engine, drive_folder_id, local_path, owner, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                            (ws_id, name, desc, engine, folder_id, local_path, owner, created_date)
                                        )
                                        if is_unified:
                                            conn.execute(
                                                "INSERT OR IGNORE INTO local_branches (name, head_commit_hash, workspace_id) VALUES (?, ?, ?)",
                                                ("main", None, ws_id)
                                            )
                                        conn.commit()
                                    finally:
                                        conn.close()
                            except Exception as ex:
                                print(f"[Sync] Erro ao importar workspace remoto {ws_id}: {ex}")

            # C. ATUALIZAR REGISTRO REMOTO COM WORKSPACES LOCAIS QUE NÃO ESTÃO LÁ
            registry_updated = False
            for local_ws in local_workspaces:
                ws_id = local_ws["id"]
                if ws_id not in remote_ids:
                    ws_detail = self.get_workspace_by_id(ws_id)
                    if ws_detail and ws_detail.owner == user_email:
                        print(f"[Sync] Registrando workspace local '{ws_detail.name}' no gameflow.json remoto.")
                        workspaces = registry.setdefault("workspaces", [])
                        workspaces.append({
                            "id": ws_id,
                            "name": ws_detail.name,
                            "drive_folder_id": ws_detail.drive_folder_id,
                            "owner": user_email,
                            "created_at": ws_detail.created_at
                        })
                        remote_ids.add(ws_id)
                        registry_updated = True
            
            if registry_updated:
                drive_service.write_gameflow_registry(registry)

        except Exception as e:
            print(f"Erro no motor de sincronização com o registro Drive: {e}")



