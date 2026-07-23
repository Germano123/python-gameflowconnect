from dataclasses import dataclass

@dataclass
class UserProfile:
    """
    Entidade de domínio que representa o Perfil de Usuário local
    associado à conta de e-mail autenticada no Google Drive.
    """
    email: str
    username: str
    bio: str
