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
