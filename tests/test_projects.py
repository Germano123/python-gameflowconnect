import os
import sys
import unittest
import shutil
import gc

# Make src importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from domain import Project, ProjectNotification, Asset
from use_cases import ProjectManagerUseCase


class TestProjectManagement(unittest.TestCase):
    """Testes unitários para Gestão de Projetos baseada em SQLite Local."""

    @classmethod
    def setUpClass(cls):
        cls.test_db_dir = "data_test"
        os.makedirs(cls.test_db_dir, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        # Coleta de lixo para garantir que conexões de arquivos SQLite do Python sejam liberadas
        gc.collect()
        try:
            if os.path.exists(cls.test_db_dir):
                shutil.rmtree(cls.test_db_dir)
        except Exception as e:
            print(f"\nAviso tearDownClass (limpeza de data_test): {e}")

    def setUp(self):
        # Cria uma instância limpa do gerenciador usando o banco de testes
        self.manager = ProjectManagerUseCase(db_dir=self.test_db_dir)
        
        # Limpar registros entre execuções de testes individuais
        db = self.manager._db
        conn = db.get_connection()
        try:
            conn.execute("DELETE FROM local_assets")
            conn.execute("DELETE FROM local_projects")
            conn.commit()
        finally:
            conn.close()

    def test_sqlite_create_and_list_projects(self):
        # Criar projeto de teste
        proj = self.manager.create_project(
            name="RPG Jogo de Teste",
            description="Criando mapas no Blender",
            owner="artist@gameflow.io",
            drive_service=None, # sem Drive para teste local
            local_path=os.path.join(self.test_db_dir, "RPG_Jogo")
        )

        self.assertIsNotNone(proj.id)
        self.assertEqual(proj.name, "RPG Jogo de Teste")
        self.assertEqual(proj.owner, "artist@gameflow.io")

        # Listar projetos e verificar presença do projeto criado no SQLite
        projects = self.manager.list_projects()
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0].id, proj.id)

        # Verificar se a pasta oculta .gameflow e o connection.json foram gerados
        gf_path = os.path.join(self.test_db_dir, "RPG_Jogo", ".gameflow", "connection.json")
        self.assertTrue(os.path.exists(gf_path))
        import json
        with open(gf_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["project_id"], proj.id)
            self.assertEqual(data["name"], "RPG Jogo de Teste")


    def test_sqlite_delete_project(self):
        proj = self.manager.create_project(
            name="Delete Me Project",
            description="Excluir",
            owner="developer@gameflow.io",
            drive_service=None
        )

        # Confirmar inserção
        p_loaded = self.manager.get_project_by_id(proj.id)
        self.assertIsNotNone(p_loaded)

        # Excluir e confirmar remoção
        deleted = self.manager.delete_project(proj.id)
        self.assertTrue(deleted)
        self.assertIsNone(self.manager.get_project_by_id(proj.id))

    def test_sqlite_notify_asset_added(self):
        proj = self.manager.create_project(
            name="Assets Test Project",
            description="Anexo de mídias",
            owner="designer@gameflow.io",
            drive_service=None
        )

        asset = Asset(name="hero_run.png", mime_type="image/png", size=20480)
        notif = self.manager.notify_asset_added(
            project_id=proj.id,
            author="designer@gameflow.io",
            asset=asset,
            drive_service=None
        )

        self.assertIsNotNone(notif.id)
        self.assertIn("hero_run.png", notif.message)

        # Verificar se o asset foi anexado ao projeto local recuperado
        p_loaded = self.manager.get_project_by_id(proj.id)
        self.assertEqual(len(p_loaded.assets), 1)
        self.assertEqual(p_loaded.assets[0].name, "hero_run.png")

    def test_sqlite_user_profile_crud(self):
        from use_cases import UserProfileUseCase
        uc = UserProfileUseCase(db_dir=self.test_db_dir)

        # Clear profiles first
        db = uc._db
        conn = db.get_connection()
        try:
            conn.execute("DELETE FROM user_profiles")
            conn.commit()
        finally:
            conn.close()

        # Criar / Atualizar perfil
        email = "developer@gameflow.io"
        profile = uc.save_profile(email, username="Dev Master", bio="Python programmer and game dev.")

        self.assertEqual(profile.email, email)
        self.assertEqual(profile.username, "Dev Master")
        self.assertEqual(profile.bio, "Python programmer and game dev.")

        # Buscar perfil
        loaded = uc.get_profile(email)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.username, "Dev Master")

