from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class Commit:
    """
    Entidade de domínio pura representando um Commit no GFC-DVCS (DAG).
    """
    hash: str
    parents: List[str]
    author: str
    timestamp: str
    message: str
    changes: List[Dict[str, Any]] = field(default_factory=list)
