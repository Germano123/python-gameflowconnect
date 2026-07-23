import sqlite3
import os

class LocalDatabase:
    """
    Gerenciador do banco de dados local SQLite (gameflow_local.db).
    Utilizado por cada máquina para gerenciar cache de sincronização e status de assets.
    """
    DB_NAME = "gameflow_local.db"

    def __init__(self, data_dir: str = "data"):
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
            # Tabela de Projetos Vinculados Localmente
            conn.execute("""
            CREATE TABLE IF NOT EXISTS local_projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                drive_folder_id TEXT NOT NULL,
                local_path TEXT NOT NULL,
                owner TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """)

            # Tabela de Controle de Assets locais sincronizados
            conn.execute("""
            CREATE TABLE IF NOT EXISTS local_assets (
                id TEXT PRIMARY KEY, -- ID do arquivo no Google Drive
                project_id TEXT NOT NULL,
                name TEXT NOT NULL,
                mime_type TEXT,
                size INTEGER,
                local_path TEXT,
                status TEXT NOT NULL, -- 'SYNCHRONIZED', 'LOCAL_ONLY', 'OUT_OF_SYNC'
                last_sync TEXT,
                FOREIGN KEY(project_id) REFERENCES local_projects(id) ON DELETE CASCADE
            );
            """)

            # Tabela de Perfis de Usuário
            conn.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                email TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                bio TEXT
            );
            """)
            conn.commit()

