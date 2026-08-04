import sqlite3
import os

class LocalDatabase:
    """
    Gerenciador do banco de dados local SQLite (gameflow_local.db).
    Utilizado por cada máquina para gerenciar cache de sincronização de Workspaces.
    """
    DB_NAME = "gameflow_local.db"

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            import sys
            if getattr(sys, "frozen", False):
                if os.name == "nt":
                    local_appdata = os.environ.get("LOCALAPPDATA")
                    if local_appdata:
                        self._data_dir = os.path.join(local_appdata, "GameFlowConnect")
                    else:
                        self._data_dir = os.path.expanduser("~/.gameflowconnect")
                else:
                    self._data_dir = os.path.expanduser("~/.gameflowconnect")
            else:
                base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
                self._data_dir = os.path.join(base_dir, "data")
        else:
            self._data_dir = data_dir


        os.makedirs(self._data_dir, exist_ok=True)
        self._db_path = os.path.join(self._data_dir, self.DB_NAME)
        self.initialize_tables()


    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def initialize_tables(self) -> None:
        with self.get_connection() as conn:
            # 1. Criar tabela de Workspaces (Conforme doc.md)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS local_workspaces (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                engine TEXT NOT NULL,
                drive_folder_id TEXT NOT NULL,
                local_path TEXT NOT NULL,
                owner TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """)

            # 2. Criar tabela de Assets vinculados a Workspaces
            conn.execute("""
            CREATE TABLE IF NOT EXISTS local_assets (
                id TEXT PRIMARY KEY, -- ID do arquivo no Google Drive (pode ser opcional para CAS)
                workspace_id TEXT NOT NULL,
                name TEXT NOT NULL,
                mime_type TEXT,
                size INTEGER,
                local_path TEXT,
                status TEXT NOT NULL, -- 'SYNCHRONIZED', 'LOCAL_ONLY', 'OUT_OF_SYNC'
                last_sync TEXT,
                uuid TEXT,
                content_hash TEXT,
                version_number INTEGER DEFAULT 1,
                creator TEXT,
                created_at TEXT,
                category TEXT,
                FOREIGN KEY(workspace_id) REFERENCES local_workspaces(id) ON DELETE CASCADE
            );
            """)

            # 3. Tabela de Perfis de Usuário
            conn.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                email TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                bio TEXT,
                github_token TEXT
            );
            """)

            # 4. Tabela de Workspaces ignorados/excluídos para evitar redescobri-los automaticamente do Drive
            conn.execute("""
            CREATE TABLE IF NOT EXISTS ignored_workspaces (
                id TEXT PRIMARY KEY
            );
            """)

            # 5. Novas tabelas GFC-DVCS
            conn.execute("""
            CREATE TABLE IF NOT EXISTS local_commits (
                hash TEXT PRIMARY KEY,
                parents TEXT, -- string separada por virgulas
                author TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                FOREIGN KEY(workspace_id) REFERENCES local_workspaces(id) ON DELETE CASCADE
            );
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS local_branches (
                name TEXT NOT NULL,
                head_commit_hash TEXT,
                workspace_id TEXT NOT NULL,
                PRIMARY KEY (name, workspace_id),
                FOREIGN KEY(workspace_id) REFERENCES local_workspaces(id) ON DELETE CASCADE
            );
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS local_locks (
                asset_id TEXT PRIMARY KEY,
                owner TEXT NOT NULL,
                locked_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                FOREIGN KEY(workspace_id) REFERENCES local_workspaces(id) ON DELETE CASCADE
            );
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS local_snapshots (
                id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                state TEXT NOT NULL,
                author TEXT NOT NULL,
                description TEXT,
                timestamp TEXT NOT NULL,
                changes TEXT, -- JSON string
                FOREIGN KEY(workspace_id) REFERENCES local_workspaces(id) ON DELETE CASCADE
            );
            """)

            # Adicionar colunas novas caso o banco já existisse
            for col, col_type in [("uuid", "TEXT"), ("content_hash", "TEXT"), ("version_number", "INTEGER DEFAULT 1"), ("creator", "TEXT"), ("created_at", "TEXT"), ("category", "TEXT")]:
                try:
                    conn.execute(f"ALTER TABLE local_assets ADD COLUMN {col} {col_type};")
                except sqlite3.OperationalError:
                    pass

            try:
                conn.execute("ALTER TABLE user_profiles ADD COLUMN github_token TEXT;")
            except sqlite3.OperationalError:
                pass

            # 4. Executar migração de dados antigos de local_projects -> local_workspaces (se existir)
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='local_projects'")
            if cursor.fetchone():
                try:
                    # Copiar projetos existentes
                    projects = conn.execute("SELECT * FROM local_projects").fetchall()
                    for p in projects:
                        conn.execute(
                            "INSERT OR IGNORE INTO local_workspaces (id, name, description, engine, drive_folder_id, local_path, owner, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (p["id"], p["name"], p["description"], "Godot", p["drive_folder_id"], p["local_path"], p["owner"], p["created_at"])
                        )

                    # Copiar assets existentes
                    assets = conn.execute("SELECT * FROM sqlite_master WHERE type='table' AND name='local_assets'").fetchone()
                    if assets:
                        # Tentar alterar coluna project_id para workspace_id na migração de assets
                        # Como alterar tabelas/chaves estrangeiras no SQLite é complexo,
                        # se a tabela antiga continha project_id, nós apenas lemos e reinserimos.
                        # Verificando se a tabela local_assets tem a coluna project_id
                        columns = [col[1] for col in conn.execute("PRAGMA table_info(local_assets)").fetchall()]
                        if "project_id" in columns:
                            old_assets = conn.execute("SELECT * FROM local_assets").fetchall()
                            # Dropar tabela de assets antiga
                            conn.execute("DROP TABLE local_assets")
                            # Recriar com workspace_id
                            conn.execute("""
                            CREATE TABLE IF NOT EXISTS local_assets (
                                id TEXT PRIMARY KEY,
                                workspace_id TEXT NOT NULL,
                                name TEXT NOT NULL,
                                mime_type TEXT,
                                size INTEGER,
                                local_path TEXT,
                                status TEXT NOT NULL,
                                last_sync TEXT,
                                FOREIGN KEY(workspace_id) REFERENCES local_workspaces(id) ON DELETE CASCADE
                            );
                            """)
                            for a in old_assets:
                                conn.execute(
                                    "INSERT OR IGNORE INTO local_assets (id, workspace_id, name, mime_type, size, local_path, status, last_sync) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                    (a["id"], a["project_id"], a["name"], a["mime_type"], a["size"], a["local_path"], a["status"], a["last_sync"])
                                )

                    # Dropar tabela antiga de projetos
                    conn.execute("DROP TABLE local_projects")
                    print("Migração de local_projects para local_workspaces concluída com sucesso!")
                except Exception as e:
                    print(f"Aviso durante migração SQLite: {e}")

            conn.commit()
