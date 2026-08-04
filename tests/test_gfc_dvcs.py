import os
import sys
import unittest
import tempfile
import shutil
import json
import gc
from datetime import datetime, timedelta

# Make src importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from domain import Commit, Lock, Snapshot, Asset, SyncStatus
from use_cases import WorkspaceManagerUseCase, GFCDVCSUseCase
from use_cases.gfc_dvcs_use_cases import calculate_file_hash


class InMemoryDriveAdapterMock:
    """Mock em memória para simular o GoogleDriveAdapter no GFC-DVCS."""
    def __init__(self):
        self.files = {}  # pasta/sub/file -> dict
        self.objects = {}  # hash -> bytes

    def is_authenticated(self) -> bool:
        return True

    def upload_object(self, local_path: str, content_hash: str, workspace_folder_id: str) -> str:
        with open(local_path, "rb") as f:
            self.objects[content_hash] = f.read()
        return f"file_{content_hash}"

    def download_object(self, content_hash: str, workspace_folder_id: str, destination_path: str) -> str:
        if content_hash not in self.objects:
            raise FileNotFoundError(f"Objeto {content_hash} não encontrado.")
        with open(destination_path, "wb") as f:
            f.write(self.objects[content_hash])
        return destination_path

    def write_metadata(self, workspace_folder_id: str, subfolder_name: str, filename: str, content: dict) -> str:
        key = f"{workspace_folder_id}/{subfolder_name}/{filename}"
        self.files[key] = json.loads(json.dumps(content))
        return f"meta_{filename}"

    def read_metadata(self, workspace_folder_id: str, subfolder_name: str, filename: str) -> dict:
        key = f"{workspace_folder_id}/{subfolder_name}/{filename}"
        return self.files.get(key)


class TestGFCDVCS(unittest.TestCase):
    """Testes de integração unitária para a nova arquitetura GFC-DVCS."""

    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp()
        cls.test_db_dir = os.path.join(cls.test_dir, "db")
        os.makedirs(cls.test_db_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        gc.collect()
        try:
            if os.path.exists(cls.test_dir):
                shutil.rmtree(cls.test_dir)
        except Exception as e:
            print(f"Erro no tearDownClass: {e}")

    def setUp(self):
        from state import AppState
        AppState.local_base_dir = self.test_dir
        self.workspace_manager = WorkspaceManagerUseCase(db_dir=self.test_db_dir)
        self.dvcs = GFCDVCSUseCase(db_dir=self.test_db_dir)
        self.drive_mock = InMemoryDriveAdapterMock()
        
        # Limpar registros do banco SQLite
        db = self.workspace_manager._db
        conn = db.get_connection()
        try:
            conn.execute("DELETE FROM local_locks")
            conn.execute("DELETE FROM local_commits")
            conn.execute("DELETE FROM local_branches")
            conn.execute("DELETE FROM local_assets")
            conn.execute("DELETE FROM local_workspaces")
            conn.commit()
        finally:
            conn.close()

    def test_calculate_file_hash(self):
        # Criar arquivo temporário e testar SHA256
        with tempfile.NamedTemporaryFile(dir=self.test_dir, delete=False) as f:
            f.write(b"GameFlow Connect DVCS")
            temp_path = f.name
        
        try:
            file_hash = calculate_file_hash(temp_path)
            # Hash esperado real para "GameFlow Connect DVCS"
            expected = "f4c0d3072a15bb18fe6e9d0b7e85ebf87bd5eff90ec632ca6a828a09544c9df2"
            self.assertEqual(file_hash, expected)
        finally:
            os.remove(temp_path)

    def test_create_workspace_dvcs_structure(self):
        ws_path = os.path.join(self.test_dir, "NewDVCSProject")
        ws = self.workspace_manager.create_workspace(
            name="NewDVCSProject",
            description="Projeto de teste",
            engine="Unity",
            owner="developer@gameflow.io",
            drive_service=None,
            local_path=ws_path
        )

        self.assertIsNotNone(ws.id)
        # Verificar subpastas locais em .gameflow
        gameflow_dir = os.path.join(ws_path, ".gameflow")
        for sub in ["objects", "commits", "branches", "manifests", "snapshots", "users", "locks"]:
            self.assertTrue(os.path.exists(os.path.join(gameflow_dir, sub)))

        # Verificar manifesto inicial
        manifest_path = os.path.join(gameflow_dir, "manifests", "project.json")
        self.assertTrue(os.path.exists(manifest_path))
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
            self.assertEqual(manifest["project_id"], ws.id)
            self.assertIn("main", manifest["active_branches"])
            self.assertIsNone(manifest["heads"]["main"])

    def test_commit_creation_and_cas_upload(self):
        ws_path = os.path.join(self.test_dir, "CommitProject")
        ws = self.workspace_manager.create_workspace(
            name="CommitProject",
            description="Commit Test",
            engine="Godot",
            owner="developer@gameflow.io",
            drive_service=None,
            local_path=ws_path
        )

        # Adicionar arquivos locais simulando código e textura
        os.makedirs(os.path.join(ws_path, "Scripts"), exist_ok=True)
        os.makedirs(os.path.join(ws_path, "Assets"), exist_ok=True)

        player_script = os.path.join(ws_path, "Scripts", "Player.gd")
        with open(player_script, "w") as f:
            f.write("extends KinematicBody2D\nfunc _ready():\n    pass")

        texture_png = os.path.join(ws_path, "Assets", "hero.png")
        with open(texture_png, "wb") as f:
            f.write(b"hero_texture_data_mock")

        # Gerar commit
        commit = self.dvcs.create_commit(
            workspace_id=ws.id,
            local_path=ws_path,
            message="Initial commit",
            author="developer@gameflow.io",
            drive_folder_id="drive_folder_123",
            drive_adapter=self.drive_mock
        )

        self.assertIsNotNone(commit.hash)
        self.assertEqual(len(commit.changes), 2)
        
        # Verificar se os objetos foram gravados no Drive Mock (CAS)
        script_hash = calculate_file_hash(player_script)
        texture_hash = calculate_file_hash(texture_png)
        self.assertIn(script_hash, self.drive_mock.objects)
        self.assertIn(texture_hash, self.drive_mock.objects)

        # Verificar se o commit JSON foi gravado localmente
        commit_local_path = os.path.join(ws_path, ".gameflow", "commits", f"{commit.hash}.json")
        self.assertTrue(os.path.exists(commit_local_path))

        # Verificar se a cabeça da branch local e remota foram atualizadas
        conn = self.workspace_manager._db.get_connection()
        try:
            branch_row = conn.execute(
                "SELECT head_commit_hash FROM local_branches WHERE name='main' AND workspace_id=?", (ws.id,)
            ).fetchone()
            self.assertEqual(branch_row["head_commit_hash"], commit.hash)
        finally:
            conn.close()

        # Verificar manifesto no Drive Mock
        remote_manifest = self.drive_mock.read_metadata("drive_folder_123", "manifests", "project.json")
        self.assertEqual(remote_manifest["heads"]["main"], commit.hash)

    def test_locking_mechanism(self):
        ws_id = "ws_test_locks"
        asset_uuid = "asset_sword_fbx"
        user_1 = "artist1@gameflow.io"
        user_2 = "artist2@gameflow.io"

        # Registrar o workspace no SQLite para evitar erro de chave estrangeira
        conn = self.workspace_manager._db.get_connection()
        try:
            conn.execute(
                "INSERT INTO local_workspaces (id, name, description, engine, drive_folder_id, local_path, owner, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (ws_id, "Test Locks Project", "Desc", "Unity", "drive_folder_123", "fake/path", user_1, "2026-07-30")
            )
            conn.commit()
        finally:
            conn.close()

        # Adquirir lock para o usuário 1
        lock = self.dvcs.acquire_lock(
            workspace_id=ws_id,
            asset_uuid=asset_uuid,
            user_email=user_1,
            drive_folder_id="drive_folder_123",
            drive_adapter=self.drive_mock
        )
        self.assertEqual(lock.owner, user_1)

        # Tentar adquirir lock para o usuário 2 (deve lançar exceção)
        with self.assertRaises(PermissionError):
            self.dvcs.acquire_lock(
                workspace_id=ws_id,
                asset_uuid=asset_uuid,
                user_email=user_2,
                drive_folder_id="drive_folder_123",
                drive_adapter=self.drive_mock
            )

        # Liberar lock
        self.dvcs.release_lock(
            workspace_id=ws_id,
            asset_uuid=asset_uuid,
            drive_folder_id="drive_folder_123",
            drive_adapter=self.drive_mock
        )

        # Agora o usuário 2 deve conseguir adquirir
        lock_2 = self.dvcs.acquire_lock(
            workspace_id=ws_id,
            asset_uuid=asset_uuid,
            user_email=user_2,
            drive_folder_id="drive_folder_123",
            drive_adapter=self.drive_mock
        )
        self.assertEqual(lock_2.owner, user_2)

    def test_reconstruct_database_from_metadata(self):
        ws_path = os.path.join(self.test_dir, "ReconstructProject")
        ws = self.workspace_manager.create_workspace(
            name="ReconstructProject",
            description="Rebuild Test",
            engine="Godot",
            owner="developer@gameflow.io",
            drive_service=None,
            local_path=ws_path
        )

        # Adicionar arquivos e fazer commit
        os.makedirs(os.path.join(ws_path, "Assets"), exist_ok=True)
        scene_file = os.path.join(ws_path, "Assets", "main.tscn")
        with open(scene_file, "w") as f:
            f.write("[gd_scene format=2]\n[node name='Node2D' type='Node2D']\n")

        commit = self.dvcs.create_commit(
            workspace_id=ws.id,
            local_path=ws_path,
            message="Add main scene",
            author="developer@gameflow.io",
            drive_folder_id="drive_reconstruct_folder",
            drive_adapter=self.drive_mock
        )

        # Simular perda completa do banco SQLite local
        db = self.workspace_manager._db
        conn = db.get_connection()
        try:
            conn.execute("DELETE FROM local_commits")
            conn.execute("DELETE FROM local_branches")
            conn.execute("DELETE FROM local_assets")
            conn.commit()
        finally:
            conn.close()

        # Executar reconstrução
        self.dvcs.reconstruct_workspace_database(workspace_id=ws.id, local_path=ws_path)

        # Validar se os dados reapareceram no SQLite
        conn = db.get_connection()
        try:
            commits = conn.execute("SELECT * FROM local_commits WHERE workspace_id=?", (ws.id,)).fetchall()
            self.assertEqual(len(commits), 1)
            self.assertEqual(commits[0]["hash"], commit.hash)

            branches = conn.execute("SELECT * FROM local_branches WHERE name='main' AND workspace_id=?", (ws.id,)).fetchone()
            self.assertEqual(branches["head_commit_hash"], commit.hash)

            assets = conn.execute("SELECT * FROM local_assets WHERE workspace_id=?", (ws.id,)).fetchall()
            self.assertEqual(len(assets), 1)
            self.assertEqual(assets[0]["name"], "main.tscn")
        finally:
            conn.close()
