"""
tests/test_database.py — Tests for database initialization and integrity.

Tests cover schema creation, migrations, and connection handling.
"""
from __future__ import annotations

import unittest
import tempfile
import os
import sys
import shutil
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.core.database as db_mod


class TestDatabaseBase(unittest.TestCase):
    """Base class with isolated DB setup."""

    def setUp(self):
        self.test_tmp_dir = tempfile.mkdtemp()
        self.test_db_file = os.path.join(self.test_tmp_dir, "test.db")
        self.original_db_path = db_mod.DB_PATH
        db_mod.DB_PATH = self.test_db_file
        db_mod.init_db()

    def tearDown(self):
        db_mod.DB_PATH = self.original_db_path
        try:
            shutil.rmtree(self.test_tmp_dir)
        except Exception:
            pass


class TestSchemaCreation(TestDatabaseBase):
    """Test that init_db creates all required tables."""

    def test_app_config_table_exists(self):
        conn = db_mod.get_connection()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='app_config'"
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)

    def test_inventory_items_table_exists(self):
        conn = db_mod.get_connection()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='inventory_items'"
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)

    def test_inventory_transactions_table_exists(self):
        conn = db_mod.get_connection()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='inventory_transactions'"
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)

    def test_categories_table_exists(self):
        conn = db_mod.get_connection()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='categories'"
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)

    def test_part_types_table_exists(self):
        conn = db_mod.get_connection()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='part_types'"
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)

    def test_phone_models_table_exists(self):
        conn = db_mod.get_connection()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='phone_models'"
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)


class TestConnectionSettings(TestDatabaseBase):
    """Test connection pragmas."""

    def test_foreign_keys_enabled(self):
        conn = db_mod.get_connection()
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        conn.close()
        self.assertEqual(fk, 1)

    def test_wal_mode(self):
        conn = db_mod.get_connection()
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        conn.close()
        self.assertEqual(mode.lower(), "wal")

    def test_row_factory_is_row(self):
        conn = db_mod.get_connection()
        row = conn.execute("SELECT 1 AS val").fetchone()
        conn.close()
        self.assertEqual(row["val"], 1)


class TestSchemaVersion(TestDatabaseBase):
    """Test schema versioning."""

    def test_schema_version_exists(self):
        conn = db_mod.get_connection()
        row = conn.execute(
            "SELECT value FROM app_config WHERE key='schema_version'"
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)

    def test_schema_version_is_numeric(self):
        conn = db_mod.get_connection()
        row = conn.execute(
            "SELECT value FROM app_config WHERE key='schema_version'"
        ).fetchone()
        conn.close()
        version = int(row["value"])
        self.assertGreaterEqual(version, 1)

    def test_reinit_is_idempotent(self):
        """Calling init_db twice should not fail or corrupt data."""
        conn = db_mod.get_connection()
        v1 = conn.execute(
            "SELECT value FROM app_config WHERE key='schema_version'"
        ).fetchone()["value"]
        conn.close()

        # Re-init
        db_mod.init_db()

        conn = db_mod.get_connection()
        v2 = conn.execute(
            "SELECT value FROM app_config WHERE key='schema_version'"
        ).fetchone()["value"]
        conn.close()

        self.assertEqual(v1, v2)


class TestDatabaseIntegrity(TestDatabaseBase):
    """Test database integrity checks."""

    def test_integrity_check_passes(self):
        conn = db_mod.get_connection()
        result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        conn.close()
        self.assertEqual(result, "ok")

    def test_foreign_key_check_passes(self):
        conn = db_mod.get_connection()
        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        conn.close()
        self.assertEqual(len(violations), 0)

    def test_inventory_items_columns(self):
        """Verify essential columns exist on inventory_items."""
        conn = db_mod.get_connection()
        cols = conn.execute("PRAGMA table_info(inventory_items)").fetchall()
        conn.close()
        col_names = {c["name"] for c in cols}
        required = {"id", "brand", "name", "color", "stock", "min_stock",
                     "barcode", "sell_price", "model_id", "part_type_id"}
        self.assertTrue(required.issubset(col_names),
                        f"Missing columns: {required - col_names}")


if __name__ == "__main__":
    unittest.main()
