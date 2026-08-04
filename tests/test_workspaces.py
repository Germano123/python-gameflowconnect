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
        from state import AppState
        AppState.local_base_dir = self.test_db_dir
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

        # Verificar se a pasta oculta .gameflow, manifests/project.json e config.json foram gerados
        manifest_path = os.path.join(self.test_db_dir, "RPG_Godot", ".gameflow", "manifests", "project.json")
        config_path = os.path.join(self.test_db_dir, "RPG_Godot", ".gameflow", "config.json")
        self.assertTrue(os.path.exists(manifest_path))
        self.assertTrue(os.path.exists(config_path))

        import json
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["project_id"], ws.id)
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
            drive_service=None,
            local_path=os.path.join(self.test_db_dir, "assets_test_ws")
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

    def test_scan_and_import_local_workspaces(self):
        # 1. Preparar pastas de workspace simuladas no disco
        test_scan_dir = os.path.join(self.test_db_dir, "Scan_Base_Dir")
        os.makedirs(test_scan_dir, exist_ok=True)
        
        ws_folder = os.path.join(test_scan_dir, "My_Existing_RPG_Game")
        gameflow_meta_dir = os.path.join(ws_folder, ".gameflow")
        os.makedirs(gameflow_meta_dir, exist_ok=True)
        
        manifest_data = {
            "id": "ws_scan_test_123",
            "name": "My Existing RPG Game",
            "description": "Um RPG existente no disco",
            "engine": "Unity",
            "owner": "old_dev@gameflow.io",
            "drive_folder_id": "drive_folder_scan_123",
            "created_at": "2026-01-01"
        }
        
        import json
        with open(os.path.join(gameflow_meta_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest_data, f)
            
        # 2. Executar escaneamento
        imported = self.manager.scan_and_import_local_workspaces(test_scan_dir)
        self.assertEqual(len(imported), 1)
        self.assertEqual(imported[0].id, "ws_scan_test_123")
        self.assertEqual(imported[0].name, "My Existing RPG Game")
        
        # 3. Confirmar que agora está listado no banco local
        workspaces = self.manager.list_workspaces()
        self.assertTrue(any(w.id == "ws_scan_test_123" for w in workspaces))
        
        # 4. Escanear novamente não deve importar duplicatas
        imported_again = self.manager.scan_and_import_local_workspaces(test_scan_dir)
        self.assertEqual(len(imported_again), 0)

    def test_sync_workspaces_with_registry(self):
        class MockDriveService:
            def __init__(self):
                self.is_authenticated = True
                self.registry_data = {
                    "version": "1.0.0",
                    "workspaces": [
                        {
                            "id": "ws_remote_123",
                            "name": "Remote Shared Project",
                            "drive_folder_id": "folder_remote_123",
                            "owner": "partner@gameflow.io",
                            "created_at": "2026-01-01"
                        }
                    ]
                }
                self.existing_folders = {"folder_remote_123": True}
                self.registry_written = None

            def read_gameflow_registry(self):
                return self.registry_data

            def write_gameflow_registry(self, registry):
                self.registry_written = registry

            def check_folder_exists(self, folder_id):
                return self.existing_folders.get(folder_id, False)

            def find_file_in_folder(self, folder_id, filename):
                return "manifest_id_123" if filename == "manifest.json" else None

            def read_json_file(self, file_id):
                return {
                    "id": "ws_remote_123",
                    "name": "Remote Shared Project",
                    "description": "Shared RPG Desc",
                    "engine": "Unity",
                    "owner": "partner@gameflow.io",
                    "members": ["partner@gameflow.io", "test_user@gameflow.io"],
                    "created_at": "2026-01-01",
                    "drive_folder_id": "folder_remote_123"
                }

            def remove_workspace_from_registry(self, ws_id):
                self.registry_data["workspaces"] = [w for w in self.registry_data["workspaces"] if w["id"] != ws_id]

        mock_drive = MockDriveService()

        # 1. Executar sincronização para auto-importar o projeto compartilhado
        # Como o usuário test_user@gameflow.io está no manifest e não localmente, deve ser importado
        self.manager.sync_workspaces_with_registry(mock_drive, "test_user@gameflow.io")

        # Verificar se foi inserido no banco local
        ws_loaded = self.manager.get_workspace_by_id("ws_remote_123")
        self.assertIsNotNone(ws_loaded)
        self.assertEqual(ws_loaded.name, "Remote Shared Project")
        self.assertEqual(ws_loaded.engine, "Unity")

        # 2. Agora simular que a pasta do workspace foi excluída do Drive
        # Removemos dos existentes e do registro remoto
        mock_drive.registry_data["workspaces"] = []
        mock_drive.existing_folders = {}

        # Executa a sincronização novamente
        self.manager.sync_workspaces_with_registry(mock_drive, "test_user@gameflow.io")

        # Deve ter sido deletado localmente
        self.assertIsNone(self.manager.get_workspace_by_id("ws_remote_123"))

    def test_set_and_load_item_category(self):
        # Criar workspace temporário
        ws = self.manager.create_workspace(
            name="Category Test Workspace",
            description="Testing category assignment",
            engine="Godot",
            owner="test@gameflow.io",
            drive_service=None,
            local_path=os.path.join(self.test_db_dir, "category_ws")
        )
        self.assertIsNotNone(ws)
        
        # 1. Definir categoria para arquivo e pasta
        success1 = self.manager.set_item_category(ws.id, "Assets/Art", "character.png", "art", None)
        success2 = self.manager.set_item_category(ws.id, "Scripts", "Movement.gd", "programming", None)
        success3 = self.manager.set_item_category(ws.id, "Assets", "LevelDesign", "design", None)
        
        self.assertTrue(success1)
        self.assertTrue(success2)
        self.assertTrue(success3)
        
        # 2. Carregar as categorias localmente
        categories = self.manager._load_categories(ws.local_path)
        self.assertEqual(categories.get("Assets/Art/character.png"), "art")
        self.assertEqual(categories.get("Scripts/Movement.gd"), "programming")
        self.assertEqual(categories.get("Assets/LevelDesign"), "design")

    def test_sync_folder_recursive_dry(self):
        # Criar workspace temporário
        ws = self.manager.create_workspace(
            name="Recursive Sync Workspace",
            description="Testing recursive folder synchronization",
            engine="Godot",
            owner="test@gameflow.io",
            drive_service=None,
            local_path=os.path.join(self.test_db_dir, "recursive_ws")
        )
        self.assertIsNotNone(ws)

        # Apenas testando que a lógica de DFS resolve com sucesso mesmo sem Drive ativo
        # (retorna True por padrão no dry run offline ou se demo_folder for ativa)
        success = self.manager.sync_folder(ws.id, "Art", None, "test@gameflow.io")
        self.assertTrue(success)

    def test_gameflow_folder_is_hidden(self):
        # 1. Simular uma resposta da API do Drive com .gameflow contido na raiz
        class MockDriveWithGameflow:
            def __init__(self):
                self.is_authenticated = True
                self._service = self
                
            def files(self):
                return self
                
            def list(self, q, fields):
                return self
                
            def execute(self, http=None):
                return {
                    "files": [
                        {"id": "id_normal", "name": "Assets", "mimeType": "application/vnd.google-apps.folder"},
                        {"id": "id_gameflow", "name": ".gameflow", "mimeType": "application/vnd.google-apps.folder"},
                        {"id": "id_manifest", "name": "manifest.json", "mimeType": "application/json"}
                    ]
                }
                
            def get_or_create_root_folder(self, name):
                return "root_id"
                
            def read_json_file(self, file_id):
                return {}
                
            def find_file_in_folder(self, parent_id, name):
                return None
                
            def _get_http(self):
                return None

        # 2. Criar workspace temporário
        ws = self.manager.create_workspace(
            name="Hidden Test Workspace",
            description="Testing hidden gameflow folder",
            engine="Godot",
            owner="test@gameflow.io",
            drive_service=None,
            local_path=os.path.join(self.test_db_dir, "hidden_ws")
        )
        self.assertIsNotNone(ws)

        # Forçar drive_folder_id diferente de demo_folder no SQLite para processar a nuvem
        conn = self.manager._db.get_connection()
        try:
            conn.execute("UPDATE local_workspaces SET drive_folder_id = 'real_folder_id' WHERE id = ?", (ws.id,))
            conn.commit()
        finally:
            conn.close()
        ws.drive_folder_id = "real_folder_id"

        # 3. Chamar a listagem e verificar que .gameflow e manifest.json foram ocultados
        mock_drive = MockDriveWithGameflow()
        assets = self.manager.get_workspace_assets_sync_status(ws.id, mock_drive)
        
        # .gameflow não deve estar nos assets listados
        self.assertFalse(any(a.name == ".gameflow" for a in assets))
        # manifest.json não deve estar nos assets listados
        self.assertFalse(any(a.name == "manifest.json" for a in assets))
        # A pasta normal 'Assets' deve estar listada
        self.assertTrue(any(a.name == "Assets" for a in assets))

    def test_sync_workspace_metadata_dry(self):
        ws = self.manager.create_workspace(
            name="Metadata Sync Workspace",
            description="Testing metadata sync",
            engine="Godot",
            owner="test@gameflow.io",
            drive_service=None,
            local_path=os.path.join(self.test_db_dir, "metadata_ws")
        )
        self.assertIsNotNone(ws)
        # Executar com drive inativo ou demo_folder (deve retornar True e ser ignorado silenciosamente)
        self.manager.sync_workspace_metadata(ws, None)

    def test_untracked_remote_detection(self):
        from domain import SyncStatus
        # 1. Simular uma resposta da API do Drive com arquivos na raiz
        class MockDriveWithUntracked:
            def __init__(self):
                self.is_authenticated = True
                self._service = self
                
            def files(self):
                return self
                
            def list(self, q, fields):
                return self
                
            def execute(self, http=None):
                return {
                    "files": [
                        {"id": "untracked_id_123", "name": "externo.png", "mimeType": "image/png", "size": 2048, "modifiedTime": "2026-08-03T20:00:00Z"}
                    ]
                }
                
            def get_or_create_root_folder(self, name):
                return "root_id"
                
            def read_json_file(self, file_id):
                return {}
                
            def find_file_in_folder(self, parent_id, name):
                return None
                
            def _get_http(self):
                return None

        # 2. Criar workspace temporário
        ws = self.manager.create_workspace(
            name="Untracked Test Workspace",
            description="Testing untracked files detection",
            engine="Godot",
            owner="test@gameflow.io",
            drive_service=None,
            local_path=os.path.join(self.test_db_dir, "untracked_ws")
        )
        self.assertIsNotNone(ws)

        # Forçar ID diferente de demo_folder no SQLite para buscar na nuvem
        conn = self.manager._db.get_connection()
        try:
            conn.execute("UPDATE local_workspaces SET drive_folder_id = 'real_folder_id' WHERE id = ?", (ws.id,))
            conn.commit()
        finally:
            conn.close()
        ws.drive_folder_id = "real_folder_id"

        # 3. Chamar a listagem e verificar que o arquivo remoto foi marcado como UNTRACKED_REMOTE
        mock_drive = MockDriveWithUntracked()
        assets = self.manager.get_workspace_assets_sync_status(ws.id, mock_drive)
        
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0].name, "externo.png")
        self.assertEqual(assets[0].status, SyncStatus.UNTRACKED_REMOTE)

        # 4. Marcar como trackeado e listar novamente (agora deve vir como REMOTE_ONLY)
        self.manager.mark_file_as_tracked(ws.id, "untracked_id_123", "externo.png", mock_drive)
        
        # Invalidar o cache da listagem no teste para forçar recarga
        cache = self.manager._load_remote_cache(ws.local_path)
        if "" in cache.get("subpaths", {}):
            cache["subpaths"][""]["timestamp"] = 0
            self.manager._save_remote_cache(ws.local_path, cache)

        assets2 = self.manager.get_workspace_assets_sync_status(ws.id, mock_drive)
        self.assertEqual(len(assets2), 1)
        self.assertEqual(assets2[0].name, "externo.png")
        self.assertEqual(assets2[0].status, SyncStatus.REMOTE_ONLY)








