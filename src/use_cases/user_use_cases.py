from typing import Optional
from domain import UserProfile
from adapters.database import LocalDatabase


class UserProfileUseCase:
    """
    Caso de Uso: Gerenciamento do Perfil de Usuário local.
    Associa e persiste metadados de perfil (nome de usuário, bio, github_token)
    ao e-mail de autenticação ativo no Google Drive.
    """
    def __init__(self, db_dir: str = "data"):
        self._db = LocalDatabase(data_dir=db_dir)

    def get_profile(self, email: str) -> Optional[UserProfile]:
        """Recupera o perfil associado ao e-mail do SQLite."""
        conn = self._db.get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM user_profiles WHERE email = ?", (email,)
            ).fetchone()
            if row:
                return UserProfile(
                    email=row["email"],
                    username=row["username"],
                    bio=row["bio"],
                    github_token=row["github_token"]
                )
        finally:
            conn.close()
        return None

    def get_last_active_profile(self) -> Optional[UserProfile]:
        """Recupera o último perfil ativo registrado no SQLite local."""
        conn = self._db.get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM user_profiles LIMIT 1"
            ).fetchone()
            if row:
                return UserProfile(
                    email=row["email"],
                    username=row["username"],
                    bio=row["bio"],
                    github_token=row["github_token"]
                )
        finally:
            conn.close()
        return None

    def save_profile(self, email: str, username: str, bio: str, github_token: Optional[str] = None) -> UserProfile:
        """Salva ou atualiza as informações do perfil do usuário no SQLite."""
        conn = self._db.get_connection()
        try:
            # Manter o github_token anterior caso não tenha sido fornecido
            existing_token = None
            if github_token is None:
                row = conn.execute("SELECT github_token FROM user_profiles WHERE email = ?", (email,)).fetchone()
                if row:
                    existing_token = row["github_token"]
            else:
                existing_token = github_token

            conn.execute(
                "INSERT OR REPLACE INTO user_profiles (email, username, bio, github_token) VALUES (?, ?, ?, ?)",
                (email, username, bio, existing_token)
            )
            conn.commit()
        finally:
            conn.close()
        return UserProfile(email=email, username=username, bio=bio, github_token=existing_token)
