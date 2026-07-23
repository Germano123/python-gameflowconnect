from dataclasses import dataclass
from typing import Optional


@dataclass
class UserProfile:
    """
    Entidade de domínio que representa o Perfil de Usuário local
    associado à conta de e-mail autenticada no Google Drive.
    """
    email: str
    username: str
    bio: str
    github_token: Optional[str] = None

