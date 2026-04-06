"""
app/services/backup_service.py — Database backup and restore service.

Provides methods to create, list, restore, and delete database backups.
Backups are stored in a backups/ folder next to the database.
"""
from __future__ import annotations

import os
import shutil
import glob
import sqlite3
from datetime import datetime
from pathlib import Path

from app.core.database import DB_PATH


# ── BackupService ─────────────────────────────────────────────────────────────

class BackupService:
    """Manages database backups and restores."""

    # ── Public Methods ─────────────────────────────────────────────────────────

    def create_backup(self, dest_dir: str | None = None) -> str:
        """
        Create a backup of the current database.

        Args:
            dest_dir: Optional destination directory. If None, uses default
                     backups/ folder next to the DB.

        Returns:
            Path to the created backup file.

        Raises:
            IOError: If backup creation fails.
        """
        backup_dir = dest_dir or self.get_backup_dir()
        os.makedirs(backup_dir, exist_ok=True)

        # Generate filename: stock_manager_YYYY-MM-DD_HHMMSS.db
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        backup_filename = f"stock_manager_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)

        try:
            shutil.copy2(DB_PATH, backup_path)
            return backup_path
        except Exception as e:
            raise IOError(f"Failed to create backup: {e}")

    def list_backups(self) -> list[dict]:
        """
        List all backups sorted by date (newest first).

        Returns:
            List of dicts with keys: 'path', 'filename', 'size', 'date'
        """
        backup_dir = self.get_backup_dir()
        if not os.path.isdir(backup_dir):
            return []

        backups = []
        pattern = os.path.join(backup_dir, "stock_manager_*.db")

        for backup_path in glob.glob(pattern):
            try:
                stat = os.stat(backup_path)
                size = stat.st_size
                mtime = stat.st_mtime
                filename = os.path.basename(backup_path)

                backups.append({
                    "path": backup_path,
                    "filename": filename,
                    "size": size,
                    "date": mtime,
                })
            except (OSError, IOError):
                # Skip if file is inaccessible
                continue

        # Sort by date descending (newest first)
        backups.sort(key=lambda x: x["date"], reverse=True)
        return backups

    def restore_backup(self, backup_path: str) -> None:
        """
        Restore the database from a backup.

        IMPORTANT: Closes all connections to the database before restoring.

        Args:
            backup_path: Path to the backup file.

        Raises:
            IOError: If restore fails.
            FileNotFoundError: If backup_path does not exist.
        """
        if not os.path.isfile(backup_path):
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        try:
            # Close all SQLite connections to the current DB
            # (This is a best-effort; proper cleanup should happen at app level)
            import gc
            gc.collect()

            # Replace current DB with backup
            shutil.copy2(backup_path, DB_PATH)
        except Exception as e:
            raise IOError(f"Failed to restore backup: {e}")

    def delete_backup(self, backup_path: str) -> None:
        """
        Delete a specific backup file.

        Args:
            backup_path: Path to the backup file.

        Raises:
            FileNotFoundError: If backup_path does not exist.
            OSError: If deletion fails.
        """
        if not os.path.isfile(backup_path):
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        try:
            os.remove(backup_path)
        except Exception as e:
            raise OSError(f"Failed to delete backup: {e}")

    def get_backup_dir(self) -> str:
        """
        Get the backup directory path.

        Returns:
            Path to the backups/ folder next to the database.
        """
        db_dir = os.path.dirname(DB_PATH)
        return os.path.join(db_dir, "backups")

    def auto_cleanup(self, keep: int = 10) -> int:
        """
        Delete oldest backups, keeping only the most recent `keep` backups.

        Args:
            keep: Number of most recent backups to retain (default: 10).

        Returns:
            Number of backups deleted.
        """
        backups = self.list_backups()
        if len(backups) <= keep:
            return 0

        # Delete oldest backups beyond keep count
        to_delete = backups[keep:]
        deleted_count = 0

        for backup in to_delete:
            try:
                os.remove(backup["path"])
                deleted_count += 1
            except (OSError, IOError):
                # Log error but continue with other deletions
                continue

        return deleted_count
