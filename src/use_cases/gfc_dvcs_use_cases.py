import os
import json
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from domain import Commit, Lock, Snapshot, SnapshotState, Asset, SyncStatus
from adapters.database import LocalDatabase

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from adapters.google_drive_adapter import GoogleDriveAdapter


def calculate_file_hash(filepath: str) -> str:
    """Calcula o hash SHA256 de um arquivo local de forma eficiente."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Arquivo não encontrado para cálculo de hash: {filepath}")
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


class GFCDVCSUseCase:
    """
    Casos de uso principais para o sistema de versionamento distribuído (GFC-DVCS).
    Responsável por Commits, Locks, Sincronização Incremental por CAS e Reconstrução de Histórico.
    """
    def __init__(self, db_dir: str = "data"):
        self._db = LocalDatabase(data_dir=db_dir)

    def create_commit(
        self,
        workspace_id: str,
        local_path: str,
        message: str,
        author: str,
        drive_folder_id: str,
        drive_adapter: "GoogleDriveAdapter",
        active_branch: str = "main"
    ) -> Commit:
        """
        Cria um commit a partir de alterações locais detectadas no Workspace,
        carrega os novos objetos para a nuvem no CAS e atualiza o manifesto remoto.
        """
        # 1. Recuperar cabeça atual local da branch
        parent_hash = None
        conn = self._db.get_connection()
        try:
            row = conn.execute(
                "SELECT head_commit_hash FROM local_branches WHERE name = ? AND workspace_id = ?",
                (active_branch, workspace_id)
            ).fetchone()
            if row:
                parent_hash = row["head_commit_hash"]
        finally:
            conn.close()

        # 2. Rastrear alterações e gerar hashes
        changes = []
        # Para simular ou realizar as alterações, escaneamos a pasta local
        # Em produção, o watcher ou a UI passa a lista de alterações.
        # Aqui, escaneamos todos os arquivos da pasta do workspace (excluindo .gameflow e .git e venv)
        for root, dirs, files in os.walk(local_path):
            # Ignorar diretórios ocultos
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("venv", "build", "dist", "data")]
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, local_path)
                
                content_hash = calculate_file_hash(full_path)
                file_size = os.path.getsize(full_path)
                
                # Gerar ou recuperar UUID fixo para este arquivo
                asset_uuid = None
                conn = self._db.get_connection()
                try:
                    asset_row = conn.execute(
                        "SELECT uuid, content_hash, version_number FROM local_assets WHERE local_path = ? AND workspace_id = ?",
                        (full_path, workspace_id)
                    ).fetchone()
                    if asset_row:
                        asset_uuid = asset_row["uuid"]
                        old_hash = asset_row["content_hash"]
                        version = asset_row["version_number"]
                        # Se o hash mudou, incrementa a versão
                        if old_hash != content_hash:
                            version += 1
                            action = "MODIFY"
                        else:
                            # Sem modificação
                            continue
                    else:
                        asset_uuid = f"asset_{uuid.uuid4().hex[:8]}"
                        version = 1
                        action = "ADD"
                finally:
                    conn.close()

                # Upload do objeto para a nuvem se autenticado
                if drive_folder_id != "demo_folder" and drive_adapter and drive_adapter.is_authenticated():
                    try:
                        drive_adapter.upload_object(full_path, content_hash, drive_folder_id)
                    except Exception as e:
                        print(f"Erro ao carregar objeto CAS {content_hash} para o Drive: {e}")

                changes.append({
                    "asset_id": asset_uuid,
                    "logical_path": rel_path.replace("\\", "/"),
                    "action": action,
                    "object_hash": content_hash,
                    "version_number": version,
                    "size": file_size
                })

        # Se não há alterações, não criamos commit
        if not changes and parent_hash is not None:
            raise ValueError("Nenhuma alteração local detectada para criar commit.")

        # 3. Construir estrutura do Commit
        parents = [parent_hash] if parent_hash else []
        timestamp = datetime.now().isoformat()
        
        # O hash do commit é gerado a partir de metadados + lista de alterações
        commit_payload = {
            "parents": parents,
            "author": author,
            "timestamp": timestamp,
            "message": message,
            "changes": changes
        }
        commit_hash = hashlib.sha256(json.dumps(commit_payload, sort_keys=True).encode("utf-8")).hexdigest()
        
        commit = Commit(
            hash=commit_hash,
            parents=parents,
            author=author,
            timestamp=timestamp,
            message=message,
            changes=changes
        )

        # 4. Gravar arquivo JSON de metadados do commit local e remoto
        gameflow_dir = os.path.join(local_path, ".gameflow")
        commits_dir = os.path.join(gameflow_dir, "commits")
        os.makedirs(commits_dir, exist_ok=True)
        
        commit_filepath = os.path.join(commits_dir, f"{commit_hash}.json")
        with open(commit_filepath, "w", encoding="utf-8") as f:
            json.dump(commit_payload, f, indent=2)

        if drive_folder_id != "demo_folder" and drive_adapter and drive_adapter.is_authenticated():
            try:
                drive_adapter.write_metadata(drive_folder_id, "commits", f"{commit_hash}.json", commit_payload)
            except Exception as e:
                print(f"Erro ao salvar metadados do commit no Drive: {e}")

        # 5. Atualizar os cabeçalhos de branch localmente e no Drive
        conn = self._db.get_connection()
        try:
            # Atualizar branch local
            conn.execute(
                "INSERT OR REPLACE INTO local_branches (name, head_commit_hash, workspace_id) VALUES (?, ?, ?)",
                (active_branch, commit_hash, workspace_id)
            )
            
            # Atualizar indexador local de commits
            parents_str = ",".join(parents) if parents else ""
            conn.execute(
                "INSERT OR REPLACE INTO local_commits (hash, parents, author, message, timestamp, workspace_id) VALUES (?, ?, ?, ?, ?, ?)",
                (commit_hash, parents_str, author, message, timestamp, workspace_id)
            )
            
            # Atualizar/Inserir assets afetados no SQLite local
            for chg in changes:
                file_local_path = os.path.join(local_path, chg["logical_path"])
                conn.execute(
                    """
                    INSERT OR REPLACE INTO local_assets 
                    (id, workspace_id, name, mime_type, size, local_path, status, last_sync, uuid, content_hash, version_number, creator, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chg["asset_id"], workspace_id, os.path.basename(chg["logical_path"]), 
                        "application/octet-stream", chg["size"], file_local_path, 
                        SyncStatus.SYNCHRONIZED.value, timestamp, chg["asset_id"], 
                        chg["object_hash"], chg["version_number"], author, timestamp
                    )
                )
            conn.commit()
        finally:
            conn.close()

        # 6. Atualizar o manifesto global project.json remoto
        if drive_folder_id != "demo_folder" and drive_adapter and drive_adapter.is_authenticated():
            try:
                manifest = drive_adapter.read_metadata(drive_folder_id, "manifests", "project.json") or {
                    "project_id": workspace_id,
                    "active_branches": ["main"],
                    "heads": {},
                    "users": {}
                }
                if "heads" not in manifest:
                    manifest["heads"] = {}
                manifest["heads"][active_branch] = commit_hash
                manifest["users"][author] = {
                    "role": "Lead Programmer",
                    "last_seen": datetime.now().isoformat()
                }
                
                drive_adapter.write_metadata(drive_folder_id, "manifests", "project.json", manifest)
                
                # Copiar manifesto para a pasta .gameflow local
                manifests_dir = os.path.join(gameflow_dir, "manifests")
                os.makedirs(manifests_dir, exist_ok=True)
                with open(os.path.join(manifests_dir, "project.json"), "w", encoding="utf-8") as f:
                    json.dump(manifest, f, indent=2)
            except Exception as e:
                print(f"Erro ao atualizar o manifesto remoto project.json: {e}")

        return commit

    def acquire_lock(
        self,
        workspace_id: str,
        asset_uuid: str,
        user_email: str,
        drive_folder_id: str,
        drive_adapter: "GoogleDriveAdapter",
        duration_seconds: int = 7200
    ) -> Lock:
        """
        Adquire lock exclusivo temporário para um asset binário.
        Escreve o lock remoto no Google Drive para exclusão mútua e indexa no SQLite local.
        """
        now = datetime.now()
        expires = now + timedelta(seconds=duration_seconds)
        
        lock_payload = {
            "asset_id": asset_uuid,
            "owner": user_email,
            "locked_at": now.isoformat(),
            "expires_at": expires.isoformat(),
            "duration_seconds": duration_seconds
        }

        # 1. Verificar remotamente se existe um lock ativo
        if drive_folder_id != "demo_folder" and drive_adapter and drive_adapter.is_authenticated():
            try:
                existing_lock_data = drive_adapter.read_metadata(drive_folder_id, "locks", f"{asset_uuid}.json")
                if existing_lock_data:
                    # Checar expiração
                    expires_time = datetime.fromisoformat(existing_lock_data["expires_at"])
                    if expires_time > datetime.now() and existing_lock_data["owner"] != user_email:
                        raise PermissionError(
                            f"Arquivo bloqueado por {existing_lock_data['owner']} até {existing_lock_data['expires_at']}"
                        )
                
                # Se não há lock ou já expirou, adquire o lock no Drive
                drive_adapter.write_metadata(drive_folder_id, "locks", f"{asset_uuid}.json", lock_payload)
            except PermissionError:
                raise
            except Exception as e:
                print(f"Aviso ao consultar lock remoto no Drive: {e}")

        # 2. Gravar no cache local SQLite
        conn = self._db.get_connection()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO local_locks (asset_id, owner, locked_at, expires_at, workspace_id) VALUES (?, ?, ?, ?, ?)",
                (asset_uuid, user_email, now.isoformat(), expires.isoformat(), workspace_id)
            )
            conn.commit()
        finally:
            conn.close()

        return Lock(
            asset_id=asset_uuid,
            owner=user_email,
            locked_at=now.isoformat(),
            expires_at=expires.isoformat(),
            duration_seconds=duration_seconds
        )

    def release_lock(
        self,
        workspace_id: str,
        asset_uuid: str,
        drive_folder_id: str,
        drive_adapter: "GoogleDriveAdapter"
    ) -> bool:
        """Libera o lock exclusivo do asset binário."""
        # 1. Deletar arquivo remoto do Drive se autenticado
        if drive_folder_id != "demo_folder" and drive_adapter and drive_adapter.is_authenticated():
            try:
                # Na nossa implementação de GoogleDriveAdapter, deletamos reescrevendo com dados expirados 
                # ou mandando para o lixo. Para simplificar, escrevemos um objeto vazio ou expirado no lock
                # indicando liberação imediata.
                expired_lock = {
                    "asset_id": asset_uuid,
                    "owner": "system",
                    "locked_at": datetime.now().isoformat(),
                    "expires_at": (datetime.now() - timedelta(seconds=1)).isoformat(),
                    "duration_seconds": 0
                }
                drive_adapter.write_metadata(drive_folder_id, "locks", f"{asset_uuid}.json", expired_lock)
            except Exception as e:
                print(f"Erro ao remover lock remoto no Drive: {e}")

        # 2. Deletar localmente do SQLite
        conn = self._db.get_connection()
        try:
            conn.execute("DELETE FROM local_locks WHERE asset_id = ? AND workspace_id = ?", (asset_uuid, workspace_id))
            conn.commit()
        finally:
            conn.close()

        return True

    def sync_workspace(
        self,
        workspace_id: str,
        local_path: str,
        drive_folder_id: str,
        drive_adapter: "GoogleDriveAdapter",
        active_branch: str = "main"
    ) -> bool:
        """
        Sincroniza incrementalmente o workspace local a partir da cabeça da branch remota.
        """
        if drive_folder_id == "demo_folder":
            return True
        if not drive_adapter or not drive_adapter.is_authenticated():
            raise RuntimeError("Conexão com Google Drive inativa para sincronização.")

        # 1. Obter manifesto remoto project.json
        manifest = drive_adapter.read_metadata(drive_folder_id, "manifests", "project.json")
        if not manifest:
            # Sem manifesto remoto ainda, nada para sincronizar
            return False

        remote_head = manifest.get("heads", {}).get(active_branch)
        if not remote_head:
            # Sem commits remotos na branch
            return False

        # 2. Obter cabeça local atual
        local_head = None
        conn = self._db.get_connection()
        try:
            row = conn.execute(
                "SELECT head_commit_hash FROM local_branches WHERE name = ? AND workspace_id = ?",
                (active_branch, workspace_id)
            ).fetchone()
            if row:
                local_head = row["head_commit_hash"]
        finally:
            conn.close()

        if local_head == remote_head:
            # Já sincronizado!
            return True

        # 3. Baixar commits intermediários faltantes da árvore (Walk back)
        commits_to_apply = []
        current_hash = remote_head
        
        while current_hash and current_hash != local_head:
            # Tentar ler o arquivo localmente primeiro
            gameflow_dir = os.path.join(local_path, ".gameflow")
            commits_dir = os.path.join(gameflow_dir, "commits")
            os.makedirs(commits_dir, exist_ok=True)
            
            commit_data = None
            local_commit_filepath = os.path.join(commits_dir, f"{current_hash}.json")
            if os.path.exists(local_commit_filepath):
                with open(local_commit_filepath, "r", encoding="utf-8") as f:
                    commit_data = json.load(f)
            else:
                # Baixar metadados do commit do Drive
                commit_data = drive_adapter.read_metadata(drive_folder_id, "commits", f"{current_hash}.json")
                if not commit_data:
                    # Encadeamento quebrado
                    break
                # Salvar no diretório de commits local
                with open(local_commit_filepath, "w", encoding="utf-8") as f:
                    json.dump(commit_data, f, indent=2)

            commits_to_apply.insert(0, (current_hash, commit_data))
            
            # Subir na árvore
            parents = commit_data.get("parents", [])
            current_hash = parents[0] if parents else None

        # 4. Aplicar commits e baixar novos objetos CAS
        for commit_hash, data in commits_to_apply:
            author = data.get("author")
            timestamp = data.get("timestamp")
            message = data.get("message")
            changes = data.get("changes", [])

            for chg in changes:
                asset_uuid = chg["asset_id"]
                logical_path = chg["logical_path"]
                action = chg["action"]
                object_hash = chg["object_hash"]
                version = chg["version_number"]
                size = chg.get("size", 0)

                target_filepath = os.path.join(local_path, logical_path)
                os.makedirs(os.path.dirname(target_filepath), exist_ok=True)

                if action in ("ADD", "MODIFY"):
                    # Baixar do CAS
                    try:
                        drive_adapter.download_object(object_hash, drive_folder_id, target_filepath)
                    except Exception as e:
                        print(f"Erro ao baixar objeto CAS {object_hash} do Drive: {e}")
                        continue
                elif action == "DELETE":
                    if os.path.exists(target_filepath):
                        try:
                            os.remove(target_filepath)
                        except OSError:
                            pass

                # Atualizar índice SQLite local
                conn = self._db.get_connection()
                try:
                    if action == "DELETE":
                        conn.execute("DELETE FROM local_assets WHERE uuid = ? AND workspace_id = ?", (asset_uuid, workspace_id))
                    else:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO local_assets 
                            (id, workspace_id, name, mime_type, size, local_path, status, last_sync, uuid, content_hash, version_number, creator, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                asset_uuid, workspace_id, os.path.basename(logical_path), 
                                "application/octet-stream", size, target_filepath, 
                                SyncStatus.SYNCHRONIZED.value, timestamp, asset_uuid, 
                                object_hash, version, author, timestamp
                            )
                        )
                    
                    # Salvar índice local do commit
                    parents_str = ",".join(data.get("parents", []))
                    conn.execute(
                        "INSERT OR REPLACE INTO local_commits (hash, parents, author, message, timestamp, workspace_id) VALUES (?, ?, ?, ?, ?, ?)",
                        (commit_hash, parents_str, author, message, timestamp, workspace_id)
                    )
                    conn.commit()
                finally:
                    conn.close()

        # 5. Atualizar cabeça da branch local
        conn = self._db.get_connection()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO local_branches (name, head_commit_hash, workspace_id) VALUES (?, ?, ?)",
                (active_branch, remote_head, workspace_id)
            )
            conn.commit()
        finally:
            conn.close()

        return True

    def reconstruct_workspace_database(self, workspace_id: str, local_path: str) -> None:
        """
        Reconstrói os índices locais do SQLite a partir dos arquivos JSON de metadados em .gameflow/
        """
        gameflow_dir = os.path.join(local_path, ".gameflow")
        commits_dir = os.path.join(gameflow_dir, "commits")
        if not os.path.exists(commits_dir):
            return

        conn = self._db.get_connection()
        try:
            # Limpar dados antigos desse workspace
            conn.execute("DELETE FROM local_commits WHERE workspace_id = ?", (workspace_id,))
            conn.execute("DELETE FROM local_branches WHERE workspace_id = ?", (workspace_id,))
            conn.execute("DELETE FROM local_assets WHERE workspace_id = ?", (workspace_id,))

            # Ler commits do disco local e povoar SQLite
            for filename in os.listdir(commits_dir):
                if filename.endswith(".json"):
                    commit_hash = filename[:-5]
                    with open(os.path.join(commits_dir, filename), "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    parents_str = ",".join(data.get("parents", []))
                    author = data.get("author")
                    message = data.get("message")
                    timestamp = data.get("timestamp")

                    conn.execute(
                        "INSERT INTO local_commits (hash, parents, author, message, timestamp, workspace_id) VALUES (?, ?, ?, ?, ?, ?)",
                        (commit_hash, parents_str, author, message, timestamp, workspace_id)
                    )

                    # Atualizar tabela de assets a partir do commit mais recente
                    # (Uma lógica simplificada: reinserir os assets modificados)
                    for chg in data.get("changes", []):
                        asset_uuid = chg["asset_id"]
                        logical_path = chg["logical_path"]
                        action = chg["action"]
                        object_hash = chg["object_hash"]
                        version = chg["version_number"]
                        size = chg.get("size", 0)
                        file_local_path = os.path.join(local_path, logical_path)

                        if action == "DELETE":
                            conn.execute("DELETE FROM local_assets WHERE uuid = ? AND workspace_id = ?", (asset_uuid, workspace_id))
                        else:
                            conn.execute(
                                """
                                INSERT OR REPLACE INTO local_assets 
                                (id, workspace_id, name, mime_type, size, local_path, status, last_sync, uuid, content_hash, version_number, creator, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    asset_uuid, workspace_id, os.path.basename(logical_path), 
                                    "application/octet-stream", size, file_local_path, 
                                    SyncStatus.SYNCHRONIZED.value, timestamp, asset_uuid, 
                                    object_hash, version, author, timestamp
                                )
                            )

            # Reconstruir cabeça da branch (ler do manifesto project.json local se houver)
            manifest_path = os.path.join(gameflow_dir, "manifests", "project.json")
            if os.path.exists(manifest_path):
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                for branch, head in manifest.get("heads", {}).items():
                    conn.execute(
                        "INSERT OR REPLACE INTO local_branches (name, head_commit_hash, workspace_id) VALUES (?, ?, ?)",
                        (branch, head, workspace_id)
                    )

            conn.commit()
        finally:
            conn.close()
