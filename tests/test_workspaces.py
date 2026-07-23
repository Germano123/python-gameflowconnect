import os
import sys
import unittest
import shutil
import gc

# Make src importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from domain import Workspace, WorkspaceNotification, Asset
from use_cases import WorkspaceManagerUseCase


class TestWorkspaceManagement(unittest.TestCase):
    """Testes unitários para Gestão de Workspaces baseada em SQLite Local (doc.md)."""

    @classmethod
    def setUpClass(cls):
        cls.test_db_dir = "data_test"
        os.makedirs(cls.test_db_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        gc.collect()
        try:
            if os.path.exists(cls.test_db_dir):
                shutil.rmtree(cls.test_db_dir)
        except Exception as e:
            print(f"\nAviso tearDownClass: {e}")

    def setUp(self):
        self.manager = WorkspaceManagerUseCase(db_dir=self.test_db_dir)
        
        # Limpar registros entre testes
        db = self.manager._db
        conn = db.get_connection()
        try:
            conn.execute("DELETE FROM local_assets")
            conn.execute("DELETE FROM local_workspaces")
            conn.commit()
        finally:
            conn.close()

    def test_sqlite_create_and_list_workspaces(self):
        # Criar workspace de teste
        ws = self.manager.create_workspace(
            name="RPG Godot Game",
            description="Criando mapas no Godot Engine",
            engine="Godot",
            owner="artist@gameflow.io",
            drive_service=None,
            local_path=os.path.join(self.test_db_dir, "RPG_Godot")
        )

        self.assertIsNotNone(ws.id)
        self.assertEqual(ws.name, "RPG Godot Game")
        self.assertEqual(ws.engine, "Godot")
        self.assertEqual(ws.owner, "artist@gameflow.io")

        # Listar workspaces e verificar presença
        workspaces = self.manager.list_workspaces()
        self.assertEqual(len(workspaces), 1)
        self.assertEqual(workspaces[0].id, ws.id)
        self.assertEqual(workspaces[0].engine, "Godot")

        # Verificar se a pasta oculta .gameflow, manifest.json e config.json foram gerados
        manifest_path = os.path.join(self.test_db_dir, "RPG_Godot", ".gameflow", "manifest.json")
        config_path = os.path.join(self.test_db_dir, "RPG_Godot", ".gameflow", "config.json")
        self.assertTrue(os.path.exists(manifest_path))
        self.assertTrue(os.path.exists(config_path))

        import json
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["id"], ws.id)
            self.assertEqual(data["engine"], "Godot")

    def test_sqlite_delete_workspace(self):
        ws = self.manager.create_workspace(
            name="Delete Me Workspace",
            description="Excluir",
            engine="Unity",
            owner="developer@gameflow.io",
            drive_service=None
        )

        # Confirmar inserção
        w_loaded = self.manager.get_workspace_by_id(ws.id)
        self.assertIsNotNone(w_loaded)

        # Excluir
        deleted = self.manager.delete_workspace(ws.id)
        self.assertTrue(deleted)
        self.assertIsNone(self.manager.get_workspace_by_id(ws.id))

    def test_sqlite_notify_asset_added_to_workspace(self):
        ws = self.manager.create_workspace(
            name="Assets Test Workspace",
            description="Anexo de mídias",
            engine="Godot",
            owner="designer@gameflow.io",
            drive_service=None
        )

        asset = Asset(name="hero_run.png", mime_type="image/png", size=20480)
        notif = self.manager.notify_asset_added(
            workspace_id=ws.id,
            author="designer@gameflow.io",
            asset=asset,
            drive_service=None
        )

        self.assertIsNotNone(notif.id)
        self.assertIn("hero_run.png", notif.message)

        # Verificar se o asset foi anexado ao workspace
        w_loaded = self.manager.get_workspace_by_id(ws.id)
        self.assertEqual(len(w_loaded.assets), 1)
        self.assertEqual(w_loaded.assets[0].name, "hero_run.png")

    def test_create_workspace_folder(self):
        ws = self.manager.create_workspace(
            name="Folder Test Workspace",
            description="Criando subpastas",
            engine="Godot",
            owner="designer@gameflow.io",
            drive_service=None,
            local_path=os.path.join(self.test_db_dir, "Folder_Test")
        )
        # Criar pasta
        success = self.manager.create_workspace_folder(ws.id, "", "Sprites", None)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(os.path.join(ws.local_path, "Sprites")))

    def test_rename_workspace_item(self):
        ws = self.manager.create_workspace(
            name="Rename Test Workspace",
            description="Renomeação",
            engine="Godot",
            owner="designer@gameflow.io",
            drive_service=None,
            local_path=os.path.join(self.test_db_dir, "Rename_Test")
        )
        # Criar arquivo fake local
        os.makedirs(ws.local_path, exist_ok=True)
        file_path = os.path.join(ws.local_path, "old_name.txt")
        with open(file_path, "w") as f:
            f.write("test content")

        success = self.manager.rename_workspace_item(ws.id, "", "old_name.txt", "new_name.txt", None)
        self.assertTrue(success)
        self.assertFalse(os.path.exists(file_path))
        self.assertTrue(os.path.exists(os.path.join(ws.local_path, "new_name.txt")))

    def test_delete_workspace_item(self):
        ws = self.manager.create_workspace(
            name="Delete Item Workspace",
            description="Excluir item",
            engine="Godot",
            owner="designer@gameflow.io",
            drive_service=None,
            local_path=os.path.join(self.test_db_dir, "Delete_Item_Test")
        )
        os.makedirs(ws.local_path, exist_ok=True)
        file_path = os.path.join(ws.local_path, "to_delete.txt")
        with open(file_path, "w") as f:
            f.write("delete me")

        success = self.manager.delete_workspace_item(ws.id, "", "to_delete.txt", None)
        self.assertTrue(success)
        self.assertFalse(os.path.exists(file_path))

    def test_move_workspace_item(self):
        ws = self.manager.create_workspace(
            name="Move Test Workspace",
            description="Mover itens",
            engine="Godot",
            owner="designer@gameflow.io",
            drive_service=None,
            local_path=os.path.join(self.test_db_dir, "Move_Test")
        )
        os.makedirs(os.path.join(ws.local_path, "Dest"), exist_ok=True)
        file_path = os.path.join(ws.local_path, "move_me.txt")
        with open(file_path, "w") as f:
            f.write("move content")

        success = self.manager.move_workspace_item(ws.id, "", "Dest", "move_me.txt", None)
        self.assertTrue(success)
        self.assertFalse(os.path.exists(file_path))
        self.assertTrue(os.path.exists(os.path.join(ws.local_path, "Dest", "move_me.txt")))

    def test_delete_workspace_marks_ignored(self):
        ws = self.manager.create_workspace(
            name="Ignore Test Workspace",
            description="Ignorados",
            engine="Godot",
            owner="designer@gameflow.io",
            drive_service=None,
            local_path=os.path.join(self.test_db_dir, "Ignore_Test")
        )
        ws_id = ws.id
        
        # Deletar
        self.manager.delete_workspace(ws_id)
        
        # Verificar se foi inserido nos ignorados
        conn = self.manager._db.get_connection()
        try:
            cursor = conn.execute("SELECT 1 FROM ignored_workspaces WHERE id = ?", (ws_id,))
            ignored = cursor.fetchone() is not None
            self.assertTrue(ignored)
        finally:
            conn.close()
            
        # Re-ativar/Unignore
        self.manager.unignore_workspace(ws_id)
        conn = self.manager._db.get_connection()
        try:
            cursor = conn.execute("SELECT 1 FROM ignored_workspaces WHERE id = ?", (ws_id,))
            ignored = cursor.fetchone() is not None
            self.assertFalse(ignored)
        finally:
            conn.close()

    def test_upload_and_notify_asset(self):
        ws = self.manager.create_workspace(
            name="Upload Test Workspace",
            description="Envios",
            engine="Godot",
            owner="designer@gameflow.io",
            drive_service=None,
            local_path=os.path.join(self.test_db_dir, "Upload_Test")
        )
        os.makedirs(ws.local_path, exist_ok=True)
        file_path = os.path.join(ws.local_path, "upload_doc.txt")
        with open(file_path, "w") as f:
            f.write("document content")
            
        # Como drive_service é None, deve falhar graciosamente e retornar False
        success = self.manager.upload_and_notify_asset(
            workspace_id=ws.id,
            subpath="",
            filename="upload_doc.txt",
            local_path=file_path,
            drive_service=None,
            author_email="designer@gameflow.io"
        )
        self.assertFalse(success)



