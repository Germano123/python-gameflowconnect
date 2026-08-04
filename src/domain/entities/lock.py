from dataclasses import dataclass

@dataclass
class Lock:
    """
    Entidade de domínio representando um Lock exclusivo em um arquivo binário.
    """
    asset_id: str
    owner: str
    locked_at: str
    expires_at: str
    duration_seconds: int = 7200
