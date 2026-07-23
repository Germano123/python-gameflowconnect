"""
AppState — Global session state for GameFlowConnect.

This module acts as a simple in-memory store for the current user session.
It avoids passing service instances and credentials across pages manually.

Usage:
    from state import AppState

    AppState.github_token = "ghp_..."
    AppState.git_service = GitService(token=AppState.github_token)
    AppState.drive_service = DriveService()

Demo Mode:
    Call AppState.enter_demo() to populate state with mock services and
    set demo_mode = True. The dashboard and other pages display a
    "Demo Mode" banner and all data is simulated.
"""
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from services.git_connection import GitService
    from services.drive import DriveService


class AppState:
    """
    Singleton-like module-level state container.

    All attributes are class-level, so they persist across the entire
    application lifetime without needing to be instantiated.
    """

    # Authentication credentials
    github_token: Optional[str] = None
    user_email: str = "user@gameflow.io"


    # Service instances (set after successful authentication)
    git_service:   Optional["GitService"]   = None
    drive_service: Optional["DriveService"] = None

    # Currently selected project context
    current_repo_name:      Optional[str] = None
    current_drive_folder_id: Optional[str] = None
    local_project_path:      Optional[str] = None

    # Demo mode flag — True when using mock services
    demo_mode: bool = False

    # ------------------------------------------------------------------ #
    # Repository Factories (Clean Architecture DIP / LSP)
    # ------------------------------------------------------------------ #

    @classmethod
    def get_storage_repository(cls):
        """Returns the IAssetStorageRepository implementation based on current state."""
        from adapters.google_drive_adapter import GoogleDriveAdapter
        from adapters.mock_drive_adapter import MockDriveAdapter

        if cls.demo_mode:
            return MockDriveAdapter(cls.drive_service)
        return GoogleDriveAdapter(cls.drive_service)

    @classmethod
    def get_local_repository(cls):
        """Returns the ILocalStorageRepository implementation for the current local_project_path."""
        import os
        from adapters.local_file_adapter import LocalFileAdapter

        path = cls.local_project_path or os.path.abspath("./GameProject")
        return LocalFileAdapter(path)

    # ------------------------------------------------------------------ #
    # Status checks
    # ------------------------------------------------------------------ #

    @classmethod
    def is_github_connected(cls) -> bool:
        """Returns True if a GitService is authenticated and available."""
        return cls.git_service is not None

    @classmethod
    def is_drive_connected(cls) -> bool:
        """Returns True if a DriveService is authenticated and available."""
        if cls.demo_mode:
            return True
        return cls.drive_service is not None and getattr(cls.drive_service, "is_authenticated", False)


    @classmethod
    def is_fully_connected(cls) -> bool:
        """Returns True only if both GitHub and Google Drive are connected."""
        return cls.is_github_connected() and cls.is_drive_connected()

    @classmethod
    def is_local_active(cls) -> bool:
        """Returns True if a local project directory is currently loaded."""
        return cls.local_project_path is not None

    # ------------------------------------------------------------------ #
    # Demo mode
    # ------------------------------------------------------------------ #

    @classmethod
    def enter_demo(cls) -> None:
        """
        Activates demo mode: populates state with mock services so
        the user can explore the full UI without real credentials.
        """
        from services.demo import MockDriveService, MockGitService

        cls.demo_mode     = True
        cls.github_token  = "demo"
        cls.git_service   = MockGitService()
        cls.drive_service = MockDriveService()

    # ------------------------------------------------------------------ #
    # Session management
    # ------------------------------------------------------------------ #

    @classmethod
    def clear(cls) -> None:
        """Resets all state (e.g. on logout)."""
        cls.github_token           = None
        cls.git_service            = None
        cls.drive_service          = None
        cls.current_repo_name      = None
        cls.current_drive_folder_id = None
        cls.local_project_path      = None
        cls.demo_mode              = False

