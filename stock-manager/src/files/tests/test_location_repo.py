"""
tests/test_location_repo.py — Tests for LocationRepository.

Covers CRUD, location stock, transfers, delete guard.
"""
from __future__ import annotations

import os
import sys
import unittest
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging; logging.disable(logging.CRITICAL)

import app.core.database as db_mod


class _LocationTestBase(unittest.TestCase):

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
        from app.repositories.location_repo import LocationRepository
        self.repo = LocationRepository()

    def _create_item(self, stock: int = 0) -> int:
        with db_mod.get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO inventory_items (brand, name, stock, min_stock) "
                "VALUES ('Test', 'LocTestItem', ?, 0)",
                (stock,),
            )
            return cur.lastrowid


# ── Location CRUD ────────────────────────────────────────────────────────────

class TestLocationCRUD(_LocationTestBase):

    def test_add_location(self):
        lid = self.repo.add("Warehouse A")
        self.assertIsInstance(lid, int)
        self.assertGreater(lid, 0)

    def test_get_by_id(self):
        lid = self.repo.add("Warehouse B", description="Second warehouse")
        loc = self.repo.get_by_id(lid)
        self.assertIsNotNone(loc)
        self.assertEqual(loc.name, "Warehouse B")
        self.assertEqual(loc.description, "Second warehouse")

    def test_get_by_id_not_found(self):
        self.assertIsNone(self.repo.get_by_id(999999))

    def test_get_all(self):
        self.repo.add("GetAll Location")
        locs = self.repo.get_all()
        self.assertIsInstance(locs, list)
        self.assertGreater(len(locs), 0)

    def test_add_default_clears_previous(self):
        lid1 = self.repo.add("Default1", is_default=True)
        lid2 = self.repo.add("Default2", is_default=True)
        loc1 = self.repo.get_by_id(lid1)
        loc2 = self.repo.get_by_id(lid2)
        self.assertFalse(loc1.is_default)
        self.assertTrue(loc2.is_default)

    def test_update(self):
        lid = self.repo.add("Old Loc")
        self.repo.update(lid, "New Loc", description="Updated")
        loc = self.repo.get_by_id(lid)
        self.assertEqual(loc.name, "New Loc")
        self.assertEqual(loc.description, "Updated")

    def test_delete_empty_succeeds(self):
        lid = self.repo.add("Delete Me Loc")
        result = self.repo.delete(lid)
        self.assertTrue(result)
        self.assertIsNone(self.repo.get_by_id(lid))

    def test_delete_default_blocked(self):
        lid = self.repo.add("Default No Delete", is_default=True)
        result = self.repo.delete(lid)
        self.assertFalse(result)
        self.assertIsNotNone(self.repo.get_by_id(lid))


# ── Location Stock ───────────────────────────────────────────────────────────

class TestLocationStock(_LocationTestBase):

    def test_set_and_get_stock(self):
        lid = self.repo.add("Stock Loc")
        item_id = self._create_item()
        self.repo.set_stock(item_id, lid, 25)
        stock = self.repo.get_stock(item_id)
        self.assertEqual(len(stock), 1)
        self.assertEqual(stock[0].quantity, 25)

    def test_adjust_stock_add(self):
        lid = self.repo.add("Adjust Add Loc")
        item_id = self._create_item()
        self.repo.set_stock(item_id, lid, 10)
        new_qty = self.repo.adjust_stock(item_id, lid, 5)
        self.assertEqual(new_qty, 15)

    def test_adjust_stock_subtract(self):
        lid = self.repo.add("Adjust Sub Loc")
        item_id = self._create_item()
        self.repo.set_stock(item_id, lid, 10)
        new_qty = self.repo.adjust_stock(item_id, lid, -3)
        self.assertEqual(new_qty, 7)

    def test_adjust_stock_floor_zero(self):
        lid = self.repo.add("Floor Zero Loc")
        item_id = self._create_item()
        self.repo.set_stock(item_id, lid, 2)
        new_qty = self.repo.adjust_stock(item_id, lid, -10)
        self.assertEqual(new_qty, 0)

    def test_delete_location_with_stock_blocked(self):
        lid = self.repo.add("Has Stock Loc")
        item_id = self._create_item()
        self.repo.set_stock(item_id, lid, 5)
        result = self.repo.delete(lid)
        self.assertFalse(result)


# ── Transfers ────────────────────────────────────────────────────────────────

class TestTransfers(_LocationTestBase):

    def test_transfer_stock(self):
        lid_a = self.repo.add("Transfer From")
        lid_b = self.repo.add("Transfer To")
        item_id = self._create_item()
        self.repo.set_stock(item_id, lid_a, 20)
        self.repo.transfer(item_id, lid_a, lid_b, 8, note="test transfer")

        stock = self.repo.get_stock(item_id)
        stock_map = {s.location_id: s.quantity for s in stock}
        self.assertEqual(stock_map[lid_a], 12)
        self.assertEqual(stock_map[lid_b], 8)

    def test_get_transfers(self):
        lid_a = self.repo.add("Txn From")
        lid_b = self.repo.add("Txn To")
        item_id = self._create_item()
        self.repo.set_stock(item_id, lid_a, 50)
        self.repo.transfer(item_id, lid_a, lid_b, 5)
        transfers = self.repo.get_transfers(item_id=item_id)
        self.assertGreaterEqual(len(transfers), 1)
        self.assertEqual(transfers[0].quantity, 5)


if __name__ == "__main__":
    unittest.main()
