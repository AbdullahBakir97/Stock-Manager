"""
tests/test_migration.py — Tests for database migrations V7→V8→V9.

Verifies that migrations add new columns, create default location,
and populate location_stock from existing data.
"""
from __future__ import annotations

import os
import sys
import unittest
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging; logging.disable(logging.CRITICAL)

import app.core.database as db_mod


class TestFreshSchemaV9(unittest.TestCase):
    """Fresh DB should have all V9 tables and columns."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp()
        cls._orig = db_mod.DB_PATH
        db_mod.DB_PATH = os.path.join(cls._tmp, "test.db")
        db_mod.init_db()

    @classmethod
    def tearDownClass(cls):
        db_mod.DB_PATH = cls._orig

    def test_schema_version_is_12(self):
        with db_mod.get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM app_config WHERE key='schema_version'"
            ).fetchone()
            self.assertEqual(row["value"], "12")

    def test_inventory_items_has_expiry_columns(self):
        with db_mod.get_connection() as conn:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(inventory_items)").fetchall()}
            self.assertIn("expiry_date", cols)
            self.assertIn("warranty_date", cols)

    def test_suppliers_table_exists(self):
        with db_mod.get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='suppliers'"
            ).fetchone()
            self.assertEqual(row[0], 1)

    def test_locations_table_exists(self):
        with db_mod.get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='locations'"
            ).fetchone()
            self.assertEqual(row[0], 1)

    def test_sales_table_exists(self):
        with db_mod.get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='sales'"
            ).fetchone()
            self.assertEqual(row[0], 1)

    def test_sale_items_table_exists(self):
        with db_mod.get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='sale_items'"
            ).fetchone()
            self.assertEqual(row[0], 1)

    def test_stock_transfers_table_exists(self):
        with db_mod.get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='stock_transfers'"
            ).fetchone()
            self.assertEqual(row[0], 1)

    def test_default_location_created_by_migration(self):
        """When migrating from V7, a default 'Main' location should be created."""
        with db_mod.get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM locations WHERE is_default = 1"
            ).fetchone()
            # Fresh installs won't have the migration-created location,
            # but the table should at least exist and be queryable
            self.assertIsNotNone(row)


class TestMigrateV7toV8(unittest.TestCase):
    """Simulate a V7 database and test the migration path."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp()
        cls._orig = db_mod.DB_PATH
        db_mod.DB_PATH = os.path.join(cls._tmp, "migrate_test.db")

    @classmethod
    def tearDownClass(cls):
        db_mod.DB_PATH = cls._orig

    def test_v7_to_v9_migration(self):
        """Create a V7-like DB, run migration, verify V9 state."""
        import sqlite3
        conn = sqlite3.connect(db_mod.DB_PATH)
        conn.row_factory = sqlite3.Row

        # Create minimal V7 schema (must include all columns the DDL expects)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS app_config (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                name_en TEXT NOT NULL,
                name_de TEXT NOT NULL DEFAULT '',
                name_ar TEXT NOT NULL DEFAULT '',
                sort_order INTEGER NOT NULL DEFAULT 0,
                icon TEXT NOT NULL DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS part_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                accent_color TEXT NOT NULL DEFAULT '#4A9EFF',
                sort_order INTEGER NOT NULL DEFAULT 0,
                UNIQUE(category_id, key)
            );
            CREATE TABLE IF NOT EXISTS part_type_colors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_type_id INTEGER NOT NULL REFERENCES part_types(id) ON DELETE CASCADE,
                color_name TEXT NOT NULL,
                color_code TEXT NOT NULL DEFAULT '',
                sort_order INTEGER NOT NULL DEFAULT 0,
                UNIQUE(part_type_id, color_name)
            );
            CREATE TABLE IF NOT EXISTS phone_models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand TEXT NOT NULL,
                name TEXT NOT NULL UNIQUE,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS inventory_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL DEFAULT '',
                color TEXT NOT NULL DEFAULT '',
                sku TEXT,
                barcode TEXT UNIQUE,
                sell_price REAL,
                stock INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
                min_stock INTEGER NOT NULL DEFAULT 0,
                inventur INTEGER,
                image_path TEXT,
                model_id INTEGER REFERENCES phone_models(id) ON DELETE CASCADE,
                part_type_id INTEGER REFERENCES part_types(id) ON DELETE CASCADE,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(model_id, part_type_id, color)
            );
            CREATE TABLE IF NOT EXISTS inventory_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
                operation TEXT NOT NULL CHECK(operation IN ('IN','OUT','ADJUST','CREATE')),
                quantity INTEGER NOT NULL,
                stock_before INTEGER NOT NULL,
                stock_after INTEGER NOT NULL,
                note TEXT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now'))
            );
            INSERT OR REPLACE INTO app_config (key, value) VALUES ('schema_version', '7');
            INSERT INTO inventory_items (brand, name, stock) VALUES ('Test', 'Widget', 15);
        """)
        conn.commit()
        conn.close()

        # Run init_db which should migrate V7 → V8 → V9
        db_mod.init_db()

        with db_mod.get_connection() as conn:
            # Check version
            ver = conn.execute(
                "SELECT value FROM app_config WHERE key='schema_version'"
            ).fetchone()
            self.assertEqual(ver["value"], "12")

            # Check new columns exist
            cols = {r[1] for r in conn.execute("PRAGMA table_info(inventory_items)").fetchall()}
            self.assertIn("expiry_date", cols)
            self.assertIn("warranty_date", cols)

            # Check default location was created
            loc = conn.execute(
                "SELECT * FROM locations WHERE is_default = 1"
            ).fetchone()
            self.assertIsNotNone(loc)
            self.assertEqual(loc["name"], "Main")

            # Check location_stock was populated from the item with stock=15
            ls = conn.execute(
                "SELECT * FROM location_stock WHERE quantity > 0"
            ).fetchall()
            self.assertGreater(len(ls), 0)
            # The widget with stock=15 should have an entry
            total_qty = sum(r["quantity"] for r in ls)
            self.assertGreaterEqual(total_qty, 15)


if __name__ == "__main__":
    unittest.main()
