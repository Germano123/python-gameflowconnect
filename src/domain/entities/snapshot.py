from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime
from ..enums import SnapshotState

@dataclass
class Snapshot:
    """
    Entidade de domínio representando um Snapshot local (Workspace staging).
    Modificações locais temporárias que passam pelo fluxo de aprovação antes de virarem commits.
    """
    id: str
    workspace_id: str
    author: str
    description: str
    state: SnapshotState = SnapshotState.DRAFT
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    changes: List[Dict[str, Any]] = field(default_factory=list)
