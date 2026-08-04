from enum import Enum, auto

class AssetType(Enum):
    IMAGE = "image"
    DOCUMENT = "document"
    MODEL_3D = "model_3d"
    OTHER = "other"

class SyncStatus(Enum):
    LOCAL_ONLY = "local_only"
    REMOTE_ONLY = "remote_only"
    SYNCHRONIZED = "synchronized"
    OUT_OF_SYNC = "out_of_sync"
    UNTRACKED_REMOTE = "untracked_remote"

class UserRole(Enum):
    GAME_DESIGNER = "game_designer"
    LEAD_PROGRAMMER = "lead_programmer"
    LEAD_ARTIST = "lead_artist"
    LEVEL_DESIGNER = "level_designer"
    ADMINISTRATOR = "administrator"

class SnapshotState(Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MERGED = "merged"

