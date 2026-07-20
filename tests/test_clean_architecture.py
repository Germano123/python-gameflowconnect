import os
import sys
import tempfile
import unittest

# Make src importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from domain import Asset, AssetType, SyncStatus
from adapters import MockDriveAdapter, LocalFileAdapter
from use_cases import ListAssetsUseCase, SyncAssetUseCase


class TestDomainEntities(unittest.TestCase):
    """Testes unitários para as entidades puras de domínio."""

    def test_asset_type_detection(self):
        img_asset = Asset(name="hero_sprite.png", mime_type="image/png")
        self.assertEqual(img_asset.asset_type, AssetType.IMAGE)

        doc_asset = Asset(name="readme.txt", mime_type="text/plain")
        self.assertEqual(doc_asset.asset_type, AssetType.DOCUMENT)

        model_asset = Asset(name="character.fbx", mime_type="application/octet-stream")
        self.assertEqual(model_asset.asset_type, AssetType.MODEL_3D)

    def test_formatted_size(self):
        asset = Asset(name="texture.png", size=2048)
        self.assertEqual(asset.formatted_size, "2.0 KB")


class TestCleanArchitectureUseCases(unittest.TestCase):
    """Testes de integração unitários entre Adaptadores Mock e Casos de Uso."""

    def test_list_assets_use_case_filtering(self):
        mock_drive = MockDriveAdapter()
        with tempfile.TemporaryDirectory() as tmp_dir:
            local_repo = LocalFileAdapter(tmp_dir)
            use_case = ListAssetsUseCase(remote_repo=mock_drive, local_repo=local_repo)

            images = use_case.execute(asset_type=AssetType.IMAGE)
            self.assertIsInstance(images, list)
            for img in images:
                self.assertEqual(img.asset_type, AssetType.IMAGE)

    def test_sync_asset_use_case_download(self):
        mock_drive = MockDriveAdapter()
        with tempfile.TemporaryDirectory() as tmp_dir:
            local_repo = LocalFileAdapter(tmp_dir)
            sync_use_case = SyncAssetUseCase(remote_repo=mock_drive, local_repo=local_repo)

            asset_to_sync = Asset(id="mock_1", name="hero_sprite.png", mime_type="image/png")
            downloaded_path = sync_use_case.download_to_engine(asset_to_sync)

            self.assertTrue(os.path.exists(downloaded_path))
            self.assertEqual(asset_to_sync.status, SyncStatus.SYNCHRONIZED)

