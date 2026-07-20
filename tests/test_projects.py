import os
import sys
import unittest

# Make src importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from domain import Project, ProjectNotification, Asset
from use_cases import ProjectManagerUseCase


class TestProjectManagement(unittest.TestCase):
    """Testes unitários para Gestão de Projetos e Alertas de Atualização."""

    def test_create_and_share_project(self):
        manager = ProjectManagerUseCase()
        new_proj = manager.create_project(
            name="Test Game Project",
            description="Jogo de teste",
            owner="artist@studio.com"
        )

        self.assertIsNotNone(new_proj.id)
        self.assertEqual(new_proj.name, "Test Game Project")

        # Share project
        shared = manager.share_project(new_proj.id, "developer@studio.com")
        self.assertTrue(shared)
        self.assertIn("developer@studio.com", new_proj.members)

    def test_notify_asset_added_emits_alert(self):
        manager = ProjectManagerUseCase()
        proj = manager.create_project(name="Alert Test", description="Desc")

        asset = Asset(name="hero_character.png", mime_type="image/png")
        notif = manager.notify_asset_added(proj.id, "artist@studio.com", asset)

        self.assertIsNotNone(notif.id)
        self.assertIn("hero_character.png", notif.message)

        unread = manager.get_unread_notifications()
        self.assertTrue(len(unread) > 0)
