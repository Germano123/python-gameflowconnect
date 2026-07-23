from typing import Optional
from domain import UserProfile
from adapters.database import LocalDatabase


class UserProfileUseCase:
    """
    Caso de Uso: Gerenciamento do Perfil de Usuário local.
    Associa e persiste metadados de perfil (nome de usuário, bio)
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
                    bio=row["bio"]
                )
        finally:
            conn.close()
        return None

    def save_profile(self, email: str, username: str, bio: str) -> UserProfile:
        """Salva ou atualiza as informações do perfil do usuário no SQLite."""
        conn = self._db.get_connection()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO user_profiles (email, username, bio) VALUES (?, ?, ?)",
                (email, username, bio)
            )
            conn.commit()
        finally:
            conn.close()
        return UserProfile(email=email, username=username, bio=bio)
