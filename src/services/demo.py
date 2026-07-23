"""
Demo Services — Mock implementations for Drive and GitHub.

These classes implement the same public API as DriveService and GitService
but return realistic fake data, requiring zero external credentials.

Used exclusively when AppState.demo_mode is True.
"""
import random
from datetime import datetime, timedelta
from typing import Optional


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _rand_date(days_back: int = 180) -> str:
    """Returns a random ISO date string within the past N days."""
    delta = timedelta(days=random.randint(0, days_back))
    return (datetime.now() - delta).strftime("%Y-%m-%d")


def _rand_size() -> str:
    """Returns a random human-readable file size string."""
    choices = [
        f"{random.randint(10, 999)} KB",
        f"{random.randint(1, 99)}.{random.randint(1, 9)} MB",
        f"{random.randint(1, 9)}.{random.randint(1, 9)} GB",
    ]
    return random.choice(choices)


# ------------------------------------------------------------------ #
# Mock Drive Service
# ------------------------------------------------------------------ #

_DEMO_DRIVE_FILES = [
    {"id": "d001", "name": "character_hero_v3.png",        "mimeType": "image/png",          "size": "2048000",  "modifiedTime": "2026-06-15"},
    {"id": "d002", "name": "environment_forest_tileset.psd","mimeType": "image/vnd.adobe.photoshop","size": "48000000", "modifiedTime": "2026-06-20"},
    {"id": "d003", "name": "sfx_footsteps_pack.zip",       "mimeType": "application/zip",    "size": "12500000", "modifiedTime": "2026-07-01"},
    {"id": "d004", "name": "bgm_main_theme.mp3",           "mimeType": "audio/mpeg",         "size": "8700000",  "modifiedTime": "2026-07-03"},
    {"id": "d005", "name": "cutscene_intro.mp4",           "mimeType": "video/mp4",          "size": "245000000","modifiedTime": "2026-05-28"},
    {"id": "d006", "name": "design_doc_v2.pdf",            "mimeType": "application/pdf",    "size": "1200000",  "modifiedTime": "2026-06-10"},
    {"id": "d007", "name": "ui_hud_mockup.png",            "mimeType": "image/png",          "size": "3400000",  "modifiedTime": "2026-07-05"},
    {"id": "d008", "name": "shader_water_effect.glsl",     "mimeType": "text/plain",         "size": "28000",    "modifiedTime": "2026-07-08"},
    {"id": "d009", "name": "rigged_enemy_boss.fbx",        "mimeType": "application/octet-stream","size": "76000000","modifiedTime": "2026-06-30"},
    {"id": "d010", "name": "animation_run_cycle.anim",     "mimeType": "application/octet-stream","size": "1800000",  "modifiedTime": "2026-07-02"},
    {"id": "d011", "name": "level_01_layout.tmx",          "mimeType": "text/xml",           "size": "156000",   "modifiedTime": "2026-07-07"},
    {"id": "d012", "name": "sfx_ambient_cave.wav",         "mimeType": "audio/wav",          "size": "34000000", "modifiedTime": "2026-06-22"},
]


class MockDriveService:
    """
    Mock implementation of DriveService for Demo Mode.

    All methods return realistic fake data without network calls.
    Simulates a small artificial delay to mimic real API behaviour.
    """

    @property
    def is_authenticated(self) -> bool:
        return True

    def authenticate(self) -> bool:
        return True

    def list_files(self, page_size: int = 20) -> list[dict]:
        """Returns a curated list of demo game asset files."""
        import time
        time.sleep(0.4)  # simulate network latency
        return _DEMO_DRIVE_FILES[:page_size]

    def upload_file(self, local_path: str, drive_folder_id: Optional[str] = None) -> str:
        """Simulates a file upload and returns a fake file ID."""
        import time
        time.sleep(0.8)
        return f"demo_upload_{abs(hash(local_path)) % 100000:05d}"

    def download_file(self, file_id: str, destination_path: str) -> str:
        """Simulates a file download."""
        import os
        import time
        time.sleep(0.1)
        parent_dir = os.path.dirname(destination_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        with open(destination_path, "wb") as f:
            f.write(b"MOCK_IMAGE_DATA")
        return destination_path

    def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> str:
        return "demo_folder_123"

    def share_folder(self, folder_id: str, email: str, role: str = "writer") -> dict:
        return {"id": "permission_123"}

    def search_shared_projects(self) -> list[dict]:
        return [{"id": "meta_file_123", "name": "project_metadata.json", "parents": ["demo_folder_123"]}]

    def read_json_file(self, file_id: str) -> dict:
        return {
            "id": "proj_demo",
            "name": "Cyberpunk RPG (Demo)",
            "description": "Projeto simulado compartilhado pelo Drive",
            "owner": "artist_demo@gameflow.io",
            "members": ["user@gameflow.io", "artist_demo@gameflow.io"],
            "assets": []
        }

    def write_json_file(self, folder_id: str, filename: str, content: dict, file_id: Optional[str] = None) -> str:
        return file_id or "meta_file_123"

    def find_file_in_folder(self, folder_id: str, filename: str) -> Optional[str]:
        return "meta_file_123"

    def get_user_email(self) -> str:
        return "user@gameflow.io"





# ------------------------------------------------------------------ #
# Mock Git Service / Repo objects
# ------------------------------------------------------------------ #

class _MockRepo:
    """Mimics a PyGithub Repository object for demo purposes."""
    def __init__(self, name: str, language: str, stars: int, private: bool = False, description: str = ""):
        self.name             = name
        self.language         = language
        self.stargazers_count = stars
        self.private          = private
        self.description      = description
        self.owner            = type("Owner", (), {"login": "demo_studio"})()
        self.html_url         = f"https://github.com/demo_studio/{name}"
        self.updated_at       = datetime.now() - timedelta(days=random.randint(0, 30))


_DEMO_REPOS = [
    _MockRepo("gameflow-engine",       "C++",        142, False, "Core game engine powering the project"),
    _MockRepo("gameflow-assets",       "Python",     38,  False, "Asset pipeline and automation scripts"),
    _MockRepo("ui-components-lib",     "GDScript",   27,  False, "Reusable UI widgets for Godot"),
    _MockRepo("level-editor-plugin",   "C#",         54,  True,  "Custom Unity level editor plugin"),
    _MockRepo("shader-collection",     "GLSL",       91,  False, "Visual effects shader library"),
    _MockRepo("audio-manager",         "GDScript",   19,  False, "Dynamic audio system for Godot"),
    _MockRepo("enemy-ai-module",       "C++",        33,  True,  "Behaviour tree AI system"),
    _MockRepo("narrative-framework",   "Python",     62,  False, "Dialogue and story scripting system"),
]


class MockGitService:
    """
    Mock implementation of GitService for Demo Mode.

    Returns realistic fake GitHub repository data.
    """
    def __init__(self, token: str = "demo"):
        self._client = True  # non-None so is_github_connected() returns True

    def get_repos(self) -> list[_MockRepo]:
        import time
        time.sleep(0.5)
        return _DEMO_REPOS

    def get_repo_names(self) -> list[str]:
        return [r.name for r in _DEMO_REPOS]

    def close(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
