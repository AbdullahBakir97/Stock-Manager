"""
tests/test_category_repo.py — Tests for CategoryRepository.

Covers CRUD, delete guards (stock > 0), part type management.
"""
from __future__ import annotations

import os
import sys
import unittest
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging; logging.disable(logging.CRITICAL)

import app.core.database as db_mod
from app.repositories.category_repo import CategoryRepository
from app.repositories.item_repo import ItemRepository


class _CatTestBase(unittest.TestCase):
    """Shared setup: temp DB with schema."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp()
        cls._orig = db_mod.DB_PATH
        db_mod.DB_PATH = os.path.join(cls._tmp, "test.db")
        db_mod.init_db()

    @classmethod
    def tearDownClass(cls):
        db_mod.DB_PATH = cls._orig

    def setUp(self):
        self.repo = CategoryRepository()
        self.item_repo = ItemRepository()


# ── CRUD ─────────────────────────────────────────────────────────────────────

class TestCategoryCRUD(_CatTestBase):

    def test_add_category(self):
        cid = self.repo.add_category("test_cat", "Test EN", "Test DE", "اختبار")
        self.assertIsInstance(cid, int)
        self.assertGreater(cid, 0)

    def test_get_by_key(self):
        key = "test_get_by_key"
        self.repo.add_category(key, "Get Key EN")
        cat = self.repo.get_by_key(key)
        self.assertIsNotNone(cat)
        self.assertEqual(cat.key, key)

    def test_get_by_id(self):
        cid = self.repo.add_category("test_get_id", "Get ID EN")
        cat = self.repo.get_by_id(cid)
        self.assertIsNotNone(cat)
        self.assertEqual(cat.id, cid)

    def test_get_all(self):
        cats = self.repo.get_all()
        self.assertIsInstance(cats, list)
        self.assertGreater(len(cats), 0)

    def test_update_category(self):
        cid = self.repo.add_category("test_upd", "Old")
        self.repo.update_category(cid, "New EN", "New DE", "جديد", "📱", True)
        cat = self.repo.get_by_id(cid)
        self.assertEqual(cat.name_en, "New EN")

    def test_set_active(self):
        cid = self.repo.add_category("test_active", "Active")
        self.repo.set_active(cid, False)
        cat = self.repo.get_by_id(cid)
        self.assertFalse(cat.is_active)


# ── Part Types ───────────────────────────────────────────────────────────────

class TestPartTypeCRUD(_CatTestBase):

    def test_add_part_type(self):
        cid = self.repo.add_category("pt_cat", "PT Cat")
        ptid = self.repo.add_part_type(cid, "original", "Original", "#FF0000")
        self.assertIsInstance(ptid, int)
        self.assertGreater(ptid, 0)

    def test_get_part_types(self):
        cid = self.repo.add_category("pt_list", "PT List")
        self.repo.add_part_type(cid, "org", "Original")
        self.repo.add_part_type(cid, "comp", "Compatible")
        pts = self.repo.get_part_types(cid)
        self.assertEqual(len(pts), 2)

    def test_update_part_type(self):
        cid = self.repo.add_category("pt_upd", "PT Upd")
        ptid = self.repo.add_part_type(cid, "old_key", "Old Name")
        self.repo.update_part_type(ptid, "new_key", "New Name", "#00FF00")
        pts = self.repo.get_part_types(cid)
        found = [p for p in pts if p.id == ptid]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].name, "New Name")
        self.assertEqual(found[0].accent_color, "#00FF00")


# ── Delete Guards ────────────────────────────────────────────────────────────

class TestDeleteGuards(_CatTestBase):
    """Verify delete_category and delete_part_type check inventory_items (not stock_entries)."""

    def test_delete_category_empty_succeeds(self):
        cid = self.repo.add_category("del_empty", "Delete Empty")
        result = self.repo.delete_category(cid)
        self.assertTrue(result)
        self.assertIsNone(self.repo.get_by_id(cid))

    def test_delete_category_with_stock_blocked(self):
        """Category with items that have stock > 0 cannot be deleted."""
        cid = self.repo.add_category("del_block", "Delete Block")
        ptid = self.repo.add_part_type(cid, "pt_block", "PT Block")
        # Create a phone model and a matrix item with stock > 0
        from app.repositories.model_repo import ModelRepository
        model_repo = ModelRepository()
        mid = model_repo.add("TestBrand", f"TestModel_del_block_{cid}")
        with db_mod.get_connection() as conn:
            conn.execute(
                """INSERT INTO inventory_items
                   (brand, name, color, stock, min_stock, model_id, part_type_id)
                   VALUES ('TestBrand', 'TestItem', '', 10, 5, ?, ?)""",
                (mid, ptid),
            )
        result = self.repo.delete_category(cid)
        self.assertFalse(result)
        # Category should still exist
        self.assertIsNotNone(self.repo.get_by_id(cid))

    def test_delete_part_type_empty_succeeds(self):
        cid = self.repo.add_category("pt_del_ok", "PT Del OK")
        ptid = self.repo.add_part_type(cid, "pt_del", "PT Del")
        result = self.repo.delete_part_type(ptid)
        self.assertTrue(result)

    def test_delete_part_type_with_stock_blocked(self):
        """Part type with items that have stock > 0 cannot be deleted."""
        cid = self.repo.add_category("pt_del_block", "PT Del Block")
        ptid = self.repo.add_part_type(cid, "pt_blk", "PT Blk")
        from app.repositories.model_repo import ModelRepository
        model_repo = ModelRepository()
        mid = model_repo.add("TestBrand", f"TestModel_pt_block_{ptid}")
        with db_mod.get_connection() as conn:
            conn.execute(
                """INSERT INTO inventory_items
                   (brand, name, color, stock, min_stock, model_id, part_type_id)
                   VALUES ('TestBrand', 'TestItem', '', 5, 2, ?, ?)""",
                (mid, ptid),
            )
        result = self.repo.delete_part_type(ptid)
        self.assertFalse(result)


# ── Reorder ──────────────────────────────────────────────────────────────────

class TestReorder(_CatTestBase):

    def test_reorder_categories(self):
        ids = [
            self.repo.add_category(f"reord_{i}", f"Reord {i}")
            for i in range(3)
        ]
        self.repo.reorder(list(reversed(ids)))
        cats = self.repo.get_all()
        cat_ids = [c.id for c in cats if c.id in ids]
        self.assertEqual(cat_ids, list(reversed(ids)))

    def test_reorder_part_types(self):
        cid = self.repo.add_category("pt_reord", "PT Reord")
        pt_ids = [
            self.repo.add_part_type(cid, f"r{i}", f"R{i}")
            for i in range(3)
        ]
        self.repo.reorder_part_types(list(reversed(pt_ids)))
        pts = self.repo.get_part_types(cid)
        found = [p.id for p in pts if p.id in pt_ids]
        self.assertEqual(found, list(reversed(pt_ids)))


if __name__ == "__main__":
    unittest.main()
