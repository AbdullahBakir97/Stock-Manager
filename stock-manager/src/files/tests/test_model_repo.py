"""
tests/test_model_repo.py — Tests for ModelRepository.

Covers CRUD, delete guard (inventory_items with stock > 0), natural sort.
"""
from __future__ import annotations

import os
import sys
import unittest
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging; logging.disable(logging.CRITICAL)

import app.core.database as db_mod
from app.repositories.model_repo import ModelRepository, _natural_sort_key


class _ModelTestBase(unittest.TestCase):

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
        self.repo = ModelRepository()


# ── CRUD ─────────────────────────────────────────────────────────────────────

class TestModelCRUD(_ModelTestBase):

    def test_add_model(self):
        mid = self.repo.add("Samsung", "Galaxy S24")
        self.assertIsInstance(mid, int)
        self.assertGreater(mid, 0)

    def test_get_by_id(self):
        mid = self.repo.add("Apple", "iPhone 16 Pro")
        model = self.repo.get_by_id(mid)
        self.assertIsNotNone(model)
        self.assertEqual(model.brand, "Apple")
        self.assertEqual(model.name, "iPhone 16 Pro")

    def test_get_by_id_not_found(self):
        self.assertIsNone(self.repo.get_by_id(999999))

    def test_exists(self):
        self.repo.add("Huawei", "P60 Pro Unique")
        self.assertTrue(self.repo.exists("P60 Pro Unique"))
        self.assertFalse(self.repo.exists("nonexistent_model_xyz"))

    def test_rename(self):
        mid = self.repo.add("Xiaomi", "Redmi Note 13 Orig")
        self.repo.rename(mid, "Redmi Note 13 Pro")
        model = self.repo.get_by_id(mid)
        self.assertEqual(model.name, "Redmi Note 13 Pro")

    def test_get_brands(self):
        self.repo.add("OnePlus", "12 Pro")
        brands = self.repo.get_brands()
        self.assertIn("OnePlus", brands)

    def test_get_all(self):
        models = self.repo.get_all()
        self.assertIsInstance(models, list)
        self.assertGreater(len(models), 0)

    def test_get_all_by_brand(self):
        brand = "NokiaTest"
        self.repo.add(brand, "G50 Test")
        self.repo.add(brand, "G60 Test")
        models = self.repo.get_all(brand=brand)
        self.assertTrue(all(m.brand == brand for m in models))


# ── Delete Guard ─────────────────────────────────────────────────────────────

class TestModelDeleteGuard(_ModelTestBase):

    def test_delete_empty_model_succeeds(self):
        mid = self.repo.add("DeleteBrand", "DeleteModel_ok")
        result = self.repo.delete(mid)
        self.assertTrue(result)
        self.assertIsNone(self.repo.get_by_id(mid))

    def test_delete_model_with_stock_blocked(self):
        """Model with inventory_items stock > 0 cannot be deleted."""
        mid = self.repo.add("DeleteBrand", "DeleteModel_block_stock")
        # Create category and part type for the matrix item
        from app.repositories.category_repo import CategoryRepository
        cat_repo = CategoryRepository()
        cid = cat_repo.add_category(f"del_m_{mid}", "Del Model Cat")
        ptid = cat_repo.add_part_type(cid, f"pt_{mid}", "PT for Model")
        with db_mod.get_connection() as conn:
            conn.execute(
                """INSERT INTO inventory_items
                   (brand, name, color, stock, min_stock, model_id, part_type_id)
                   VALUES ('DeleteBrand', 'Item', '', 10, 5, ?, ?)""",
                (mid, ptid),
            )
        result = self.repo.delete(mid)
        self.assertFalse(result)
        # Model should still exist
        self.assertIsNotNone(self.repo.get_by_id(mid))

    def test_delete_model_zero_stock_succeeds(self):
        """Model with inventory_items stock == 0 can be deleted."""
        mid = self.repo.add("DeleteBrand", "DeleteModel_zero")
        from app.repositories.category_repo import CategoryRepository
        cat_repo = CategoryRepository()
        cid = cat_repo.add_category(f"del_z_{mid}", "Del Zero Cat")
        ptid = cat_repo.add_part_type(cid, f"ptz_{mid}", "PT Zero")
        with db_mod.get_connection() as conn:
            conn.execute(
                """INSERT INTO inventory_items
                   (brand, name, color, stock, min_stock, model_id, part_type_id)
                   VALUES ('DeleteBrand', 'Item', '', 0, 5, ?, ?)""",
                (mid, ptid),
            )
        result = self.repo.delete(mid)
        self.assertTrue(result)


# ── Natural Sort ─────────────────────────────────────────────────────────────

class TestNaturalSort(unittest.TestCase):

    def test_numeric_sort(self):
        names = ["A12", "A5", "A22", "A3"]
        sorted_names = sorted(names, key=_natural_sort_key)
        self.assertEqual(sorted_names, ["A3", "A5", "A12", "A22"])

    def test_mixed_prefix(self):
        names = ["Note20", "Note10", "Note9"]
        sorted_names = sorted(names, key=_natural_sort_key)
        self.assertEqual(sorted_names, ["Note9", "Note10", "Note20"])

    def test_pure_text(self):
        names = ["Banana", "Apple", "Cherry"]
        sorted_names = sorted(names, key=_natural_sort_key)
        self.assertEqual(sorted_names, ["Apple", "Banana", "Cherry"])


if __name__ == "__main__":
    unittest.main()
