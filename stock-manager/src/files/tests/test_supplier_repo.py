"""
tests/test_supplier_repo.py — Tests for SupplierRepository.

Covers CRUD, supplier-item linking, delete guard.
"""
from __future__ import annotations

import os
import sys
import unittest
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging; logging.disable(logging.CRITICAL)

import app.core.database as db_mod


class _SupplierTestBase(unittest.TestCase):

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
        from app.repositories.supplier_repo import SupplierRepository
        self.repo = SupplierRepository()


# ── CRUD ─────────────────────────────────────────────────────────────────────

class TestSupplierCRUD(_SupplierTestBase):

    def test_add_supplier(self):
        sid = self.repo.add("Acme Parts")
        self.assertIsInstance(sid, int)
        self.assertGreater(sid, 0)

    def test_get_by_id(self):
        sid = self.repo.add("Beta Supplier", phone="+49123")
        supplier = self.repo.get_by_id(sid)
        self.assertIsNotNone(supplier)
        self.assertEqual(supplier.name, "Beta Supplier")
        self.assertEqual(supplier.phone, "+49123")

    def test_get_by_id_not_found(self):
        self.assertIsNone(self.repo.get_by_id(999999))

    def test_get_all(self):
        self.repo.add("GetAll Supplier")
        suppliers = self.repo.get_all()
        self.assertIsInstance(suppliers, list)
        self.assertGreater(len(suppliers), 0)

    def test_get_all_active_only(self):
        sid = self.repo.add("Inactive Supplier")
        self.repo.set_active(sid, False)
        active = self.repo.get_all(active_only=True)
        ids = [s.id for s in active]
        self.assertNotIn(sid, ids)

    def test_update(self):
        sid = self.repo.add("Old Name")
        self.repo.update(sid, "New Name", email="new@test.com")
        supplier = self.repo.get_by_id(sid)
        self.assertEqual(supplier.name, "New Name")
        self.assertEqual(supplier.email, "new@test.com")

    def test_set_active(self):
        sid = self.repo.add("Toggle Active")
        self.repo.set_active(sid, False)
        supplier = self.repo.get_by_id(sid)
        self.assertFalse(supplier.is_active)

    def test_delete_no_items(self):
        sid = self.repo.add("Delete Me")
        result = self.repo.delete(sid)
        self.assertTrue(result)
        self.assertIsNone(self.repo.get_by_id(sid))


# ── Supplier-Item Linking ────────────────────────────────────────────────────

class TestSupplierItems(_SupplierTestBase):

    def _create_item(self) -> int:
        """Create a standalone product for testing."""
        with db_mod.get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO inventory_items (brand, name, stock, min_stock) "
                "VALUES ('Test', 'TestProduct', 5, 1)"
            )
            return cur.lastrowid

    def test_link_and_get_items(self):
        sid = self.repo.add("Link Supplier")
        item_id = self._create_item()
        self.repo.link_item(sid, item_id, cost_price=12.50, lead_days=3)
        items = self.repo.get_items(sid)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].cost_price, 12.50)
        self.assertEqual(items[0].lead_days, 3)

    def test_get_suppliers_for_item(self):
        sid1 = self.repo.add("Supplier A")
        sid2 = self.repo.add("Supplier B")
        item_id = self._create_item()
        self.repo.link_item(sid1, item_id, cost_price=10)
        self.repo.link_item(sid2, item_id, cost_price=8, is_preferred=True)
        suppliers = self.repo.get_suppliers_for_item(item_id)
        self.assertEqual(len(suppliers), 2)
        # Preferred should be first
        self.assertTrue(suppliers[0].is_preferred)

    def test_unlink_item(self):
        sid = self.repo.add("Unlink Supplier")
        item_id = self._create_item()
        self.repo.link_item(sid, item_id)
        self.repo.unlink_item(sid, item_id)
        items = self.repo.get_items(sid)
        self.assertEqual(len(items), 0)

    def test_delete_blocked_with_stock(self):
        """Supplier linked to item with stock > 0 cannot be deleted."""
        sid = self.repo.add("Block Delete Supplier")
        item_id = self._create_item()  # has stock=5
        self.repo.link_item(sid, item_id)
        result = self.repo.delete(sid)
        self.assertFalse(result)
        self.assertIsNotNone(self.repo.get_by_id(sid))


if __name__ == "__main__":
    unittest.main()
