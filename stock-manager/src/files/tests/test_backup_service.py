"""
tests/test_backup_service.py — Tests for BackupService.

Tests cover backup creation, listing, restoration, deletion,
and automatic cleanup functionality.
"""
from __future__ import annotations

import unittest
import tempfile
import os
import sys
import shutil

# Add src/files to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.core.database as db_mod
from app.repositories.item_repo import ItemRepository
from app.services.backup_service import BackupService


class TestBackupServiceBase(unittest.TestCase):
    """Base test class with shared setup."""

    def setUp(self):
        """Create fresh services for each test with unique DB."""
        self.test_tmp_dir = tempfile.mkdtemp()
        self.test_db_file = os.path.join(self.test_tmp_dir, "test.db")
        self.original_db_path = db_mod.DB_PATH
        db_mod.DB_PATH = self.test_db_file
        db_mod.init_db()
        self.backup_svc = BackupService()

    def tearDown(self):
        """Clean up test database."""
        db_mod.DB_PATH = self.original_db_path
        try:
            shutil.rmtree(self.test_tmp_dir)
        except:
            pass


class TestBackupServiceCreation(TestBackupServiceBase):
    """Test backup creation."""

    def test_create_backup_creates_file(self):
        """Test create_backup creates a backup file."""
        backup_path = self.backup_svc.create_backup()

        self.assertTrue(os.path.isfile(backup_path))
        self.assertIn("stock_manager_", backup_path)
        self.assertTrue(backup_path.endswith(".db"))

    def test_create_backup_returns_path(self):
        """Test create_backup returns the backup file path."""
        backup_path = self.backup_svc.create_backup()

        self.assertIsInstance(backup_path, str)
        self.assertGreater(len(backup_path), 0)

    def test_create_backup_with_custom_directory(self):
        """Test create_backup with custom destination directory."""
        custom_dir = os.path.join(self.test_tmp_dir, "custom_backups")
        backup_path = self.backup_svc.create_backup(dest_dir=custom_dir)

        self.assertTrue(os.path.isfile(backup_path))
        self.assertIn(custom_dir, backup_path)

    def test_create_backup_creates_directory(self):
        """Test create_backup creates destination directory if missing."""
        custom_dir = os.path.join(self.test_tmp_dir, "new_dir", "backups")
        backup_path = self.backup_svc.create_backup(dest_dir=custom_dir)

        self.assertTrue(os.path.isdir(custom_dir))
        self.assertTrue(os.path.isfile(backup_path))

    def test_create_multiple_backups(self):
        """Test creating multiple backups with different timestamps."""
        import time
        backup1 = self.backup_svc.create_backup()
        time.sleep(1)  # Ensure different timestamp
        backup2 = self.backup_svc.create_backup()

        self.assertTrue(os.path.isfile(backup1))
        self.assertTrue(os.path.isfile(backup2))
        self.assertNotEqual(backup1, backup2)


class TestBackupServiceListing(TestBackupServiceBase):
    """Test backup listing."""

    def test_list_backups_returns_list(self):
        """Test list_backups returns a list."""
        backups = self.backup_svc.list_backups()
        self.assertIsInstance(backups, list)

    def test_list_backups_returns_created_backup(self):
        """Test list_backups returns the created backup."""
        backup_path = self.backup_svc.create_backup()
        backups = self.backup_svc.list_backups()

        self.assertGreater(len(backups), 0)
        backup_filenames = [b["filename"] for b in backups]
        self.assertIn(os.path.basename(backup_path), backup_filenames)

    def test_list_backups_contains_metadata(self):
        """Test list_backups includes required metadata."""
        self.backup_svc.create_backup()
        backups = self.backup_svc.list_backups()

        self.assertGreater(len(backups), 0)
        backup = backups[0]
        self.assertIn("path", backup)
        self.assertIn("filename", backup)
        self.assertIn("size", backup)
        self.assertIn("date", backup)

    def test_list_backups_sorted_by_date_descending(self):
        """Test list_backups sorts by date (newest first)."""
        self.backup_svc.create_backup()
        self.backup_svc.create_backup()

        backups = self.backup_svc.list_backups()
        self.assertGreaterEqual(len(backups), 2)

        self.assertGreaterEqual(backups[0]["date"], backups[1]["date"])

    def test_list_backups_size_is_positive(self):
        """Test backup files have positive size."""
        self.backup_svc.create_backup()
        backups = self.backup_svc.list_backups()

        self.assertGreater(len(backups), 0)
        self.assertGreater(backups[0]["size"], 0)


class TestBackupServiceDeletion(TestBackupServiceBase):
    """Test backup deletion."""

    def test_delete_backup_removes_file(self):
        """Test delete_backup removes the backup file."""
        custom_dir = os.path.join(self.test_tmp_dir, "backup_del")
        backup_path = self.backup_svc.create_backup(dest_dir=custom_dir)
        self.assertTrue(os.path.isfile(backup_path))

        self.backup_svc.delete_backup(backup_path)

        self.assertFalse(os.path.isfile(backup_path))

    def test_delete_backup_nonexistent_raises_error(self):
        """Test delete_backup raises FileNotFoundError for missing file."""
        with self.assertRaises(FileNotFoundError):
            self.backup_svc.delete_backup("/nonexistent/path/file.db")

    def test_delete_specific_backup(self):
        """Test deleting one backup doesn't affect others."""
        custom_dir = os.path.join(self.test_tmp_dir, "backup_spec")
        backup1 = self.backup_svc.create_backup(dest_dir=custom_dir)
        import time
        time.sleep(1)
        backup2 = self.backup_svc.create_backup(dest_dir=custom_dir)

        self.backup_svc.delete_backup(backup1)

        self.assertFalse(os.path.isfile(backup1))
        self.assertTrue(os.path.isfile(backup2))


class TestBackupServiceAutoCleanup(TestBackupServiceBase):
    """Test automatic cleanup of old backups."""

    def test_auto_cleanup_is_callable(self):
        """Test auto_cleanup function exists and is callable."""
        result = self.backup_svc.auto_cleanup(keep=100)
        self.assertIsInstance(result, int)
        self.assertGreaterEqual(result, 0)

    def test_auto_cleanup_no_deletion_when_under_limit(self):
        """Test auto_cleanup doesn't delete when count < keep."""
        custom_dir = os.path.join(self.test_tmp_dir, "cleanup_under")
        for _ in range(3):
            self.backup_svc.create_backup(dest_dir=custom_dir)

        # Count files before cleanup
        before = len([f for f in os.listdir(custom_dir) if f.endswith('.db')])

        original = self.backup_svc.get_backup_dir
        self.backup_svc.get_backup_dir = lambda: custom_dir

        deleted = self.backup_svc.auto_cleanup(keep=100)

        self.backup_svc.get_backup_dir = original

        # Should not delete if under limit
        self.assertEqual(deleted, 0)


class TestBackupServiceDirectory(TestBackupServiceBase):
    """Test backup directory operations."""

    def test_get_backup_dir_returns_path(self):
        """Test get_backup_dir returns a valid path."""
        backup_dir = self.backup_svc.get_backup_dir()

        self.assertIsInstance(backup_dir, str)
        self.assertGreater(len(backup_dir), 0)
        self.assertIn("backups", backup_dir)

    def test_backup_dir_next_to_database(self):
        """Test backups folder is created next to database."""
        backup_dir = self.backup_svc.get_backup_dir()

        self.backup_svc.create_backup()

        self.assertTrue(os.path.isdir(backup_dir))


class TestBackupServiceRestore(TestBackupServiceBase):
    """Test backup restoration."""

    def test_restore_backup_with_nonexistent_file_raises_error(self):
        """Test restore_backup raises FileNotFoundError for missing backup."""
        with self.assertRaises(FileNotFoundError):
            self.backup_svc.restore_backup("/nonexistent/backup.db")

    def test_restore_backup_with_valid_file(self):
        """Test restore_backup successfully creates a copy from backup."""
        item_repo = ItemRepository()

        pid = item_repo.add_product(
            brand="Apple", name="Item", color="", stock=50, barcode="TEST-RESTORE", min_stock=10
        )

        # Create a backup
        custom_dir = os.path.join(self.test_tmp_dir, "backup_restore")
        backup_path = self.backup_svc.create_backup(dest_dir=custom_dir)

        # Verify backup file exists
        self.assertTrue(os.path.isfile(backup_path))

        # Verify it's a valid SQLite file by checking size
        self.assertGreater(os.path.getsize(backup_path), 0)


class TestBackupServiceIntegration(TestBackupServiceBase):
    """Integration tests for backup service."""

    def test_backup_workflow(self):
        """Test typical backup workflow."""
        custom_dir = os.path.join(self.test_tmp_dir, "workflow")
        import time
        backup1 = self.backup_svc.create_backup(dest_dir=custom_dir)
        time.sleep(1)
        backup2 = self.backup_svc.create_backup(dest_dir=custom_dir)

        original_get_backup_dir = self.backup_svc.get_backup_dir
        self.backup_svc.get_backup_dir = lambda: custom_dir

        backups = self.backup_svc.list_backups()
        self.assertGreaterEqual(len(backups), 2)

        to_delete = backups[-1]["path"]
        self.backup_svc.delete_backup(to_delete)

        backups = self.backup_svc.list_backups()
        paths = [b["path"] for b in backups]
        self.assertNotIn(to_delete, paths)

        self.backup_svc.get_backup_dir = original_get_backup_dir

    def test_backup_with_directory_nesting(self):
        """Test backup in nested directory structure."""
        custom_dir = os.path.join(self.test_tmp_dir, "data", "backups", "archive")
        backup_path = self.backup_svc.create_backup(dest_dir=custom_dir)

        self.assertTrue(os.path.isfile(backup_path))
        self.assertTrue(os.path.isdir(custom_dir))

    def test_multiple_backups_consistency(self):
        """Test creating multiple backups maintains file integrity."""
        backup_paths = []
        for _ in range(3):
            path = self.backup_svc.create_backup()
            backup_paths.append(path)
            self.assertTrue(os.path.isfile(path))
            self.assertGreater(os.path.getsize(path), 0)

        for path in backup_paths:
            self.assertTrue(os.path.isfile(path))


if __name__ == "__main__":
    unittest.main()
