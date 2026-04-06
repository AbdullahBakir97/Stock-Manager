"""
tests/test_image_service.py — Tests for ImageService.

Covers save, get, delete, and image path resolution.
"""
from __future__ import annotations

import os
import sys
import unittest
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging; logging.disable(logging.CRITICAL)

from pathlib import Path

import app.core.database as db_mod


class _ImageTestBase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp()
        cls._orig = db_mod.DB_PATH
        db_mod.DB_PATH = os.path.join(cls._tmp, "test.db")
        db_mod.init_db()

        # Override IMAGES_DIR to use temp folder (must be Path, not str)
        import app.services.image_service as img_mod
        cls._orig_images_dir = img_mod.IMAGES_DIR
        cls._images_tmp = os.path.join(cls._tmp, "images")
        os.makedirs(cls._images_tmp, exist_ok=True)
        img_mod.IMAGES_DIR = Path(cls._images_tmp)

    @classmethod
    def tearDownClass(cls):
        db_mod.DB_PATH = cls._orig
        import app.services.image_service as img_mod
        img_mod.IMAGES_DIR = cls._orig_images_dir
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def setUp(self):
        from app.services.image_service import ImageService
        self.svc = ImageService()

    def _create_test_image(self, name: str = "test.png", width: int = 100, height: int = 100) -> str:
        """Create a minimal test PNG file and return its path."""
        path = os.path.join(self._tmp, name)
        try:
            from PIL import Image
            img = Image.new("RGB", (width, height), color="red")
            img.save(path)
        except ImportError:
            # If Pillow not available, create a minimal file
            with open(path, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        return path


# ── Save ─────────────────────────────────────────────────────────────────────

class TestImageSave(_ImageTestBase):

    def test_save_returns_filename(self):
        src = self._create_test_image("save_test.png")
        result = self.svc.save_image(src, item_id=1)
        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith("item_1"))

    def test_save_creates_file(self):
        src = self._create_test_image("save_creates.png")
        filename = self.svc.save_image(src, item_id=2)
        full_path = os.path.join(self._images_tmp, filename)
        self.assertTrue(os.path.exists(full_path))

    def test_save_different_items_different_files(self):
        src = self._create_test_image("diff_items.png")
        f1 = self.svc.save_image(src, item_id=10)
        f2 = self.svc.save_image(src, item_id=11)
        self.assertNotEqual(f1, f2)


# ── Get ──────────────────────────────────────────────────────────────────────

class TestImageGet(_ImageTestBase):

    def test_get_existing_image(self):
        src = self._create_test_image("get_exist.png")
        filename = self.svc.save_image(src, item_id=20)
        full = self.svc.get_image_path(filename)
        self.assertIsNotNone(full)
        self.assertTrue(os.path.exists(full))

    def test_get_nonexistent_returns_none(self):
        result = self.svc.get_image_path("nonexistent_file.png")
        self.assertIsNone(result)

    def test_get_none_returns_none(self):
        result = self.svc.get_image_path(None)
        self.assertIsNone(result)

    def test_get_empty_returns_none(self):
        result = self.svc.get_image_path("")
        self.assertIsNone(result)


# ── Delete ───────────────────────────────────────────────────────────────────

class TestImageDelete(_ImageTestBase):

    def test_delete_existing_image(self):
        src = self._create_test_image("del_exist.png")
        filename = self.svc.save_image(src, item_id=30)
        full = os.path.join(self._images_tmp, filename)
        self.assertTrue(os.path.exists(full))
        self.svc.delete_image(filename)
        self.assertFalse(os.path.exists(full))

    def test_delete_nonexistent_no_error(self):
        """Deleting a non-existent image should not raise."""
        self.svc.delete_image("nonexistent.png")

    def test_delete_empty_no_error(self):
        """Deleting with empty string should not raise."""
        self.svc.delete_image("")


if __name__ == "__main__":
    unittest.main()
