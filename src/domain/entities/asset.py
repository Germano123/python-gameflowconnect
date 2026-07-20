from dataclasses import dataclass
from typing import Optional
import os
from ..enums import AssetType, SyncStatus

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tga", ".bmp", ".webp"}
DOCUMENT_EXTENSIONS = {".txt", ".md", ".pdf", ".doc", ".docx", ".json"}
MODEL_3D_EXTENSIONS = {".fbx", ".obj", ".blend", ".gltf", ".glb"}

@dataclass
class Asset:
    """
    Pure Domain Entity representing a Game Asset.
    Independent of frameworks, UI, or specific Cloud APIs.
    """
    name: str
    id: Optional[str] = None
    mime_type: Optional[str] = None
    size: Optional[int] = None
    modified_time: Optional[str] = None
    local_path: Optional[str] = None
    status: SyncStatus = SyncStatus.REMOTE_ONLY

    @property
    def extension(self) -> str:
        _, ext = os.path.splitext(self.name)
        return ext.lower()

    @property
    def asset_type(self) -> AssetType:
        ext = self.extension
        if ext in IMAGE_EXTENSIONS or (self.mime_type and self.mime_type.startswith("image/")):
            return AssetType.IMAGE
        if ext in DOCUMENT_EXTENSIONS or (self.mime_type and ("text" in self.mime_type or "pdf" in self.mime_type)):
            return AssetType.DOCUMENT
        if ext in MODEL_3D_EXTENSIONS:
            return AssetType.MODEL_3D
        return AssetType.OTHER

    @property
    def formatted_size(self) -> str:
        if self.size is None:
            return "—"
        n = self.size
        if n < 1024:
            return f"{n} B"
        if n < 1024**2:
            return f"{n/1024:.1f} KB"
        if n < 1024**3:
            return f"{n/1024**2:.1f} MB"
        return f"{n/1024**3:.1f} GB"
