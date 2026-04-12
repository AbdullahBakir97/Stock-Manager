"""
tests/test_sale_repo.py — Tests for SaleRepository.

Covers create, get, list, daily totals, top items.
"""
from __future__ import annotations

import os
import sys
import unittest
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging; logging.disable(logging.CRITICAL)

import app.core.database as db_mod


class _SaleTestBase(unittest.TestCase):

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
        from app.repositories.sale_repo import SaleRepository
        self.repo = SaleRepository()

    def _create_item(self, name: str = "SaleItem", stock: int = 50) -> int:
        with db_mod.get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO inventory_items (brand, name, stock, min_stock) "
                "VALUES ('Test', ?, ?, 0)",
                (name, stock),
            )
            return cur.lastrowid


# ── Create & Get ─────────────────────────────────────────────────────────────

class TestSaleCRUD(_SaleTestBase):

    def test_create_sale(self):
        item_id = self._create_item()
        sale_id = self.repo.create(
            customer_name="John",
            items=[{"item_id": item_id, "quantity": 2,
                    "unit_price": 99.0, "cost_price": 50.0}],
        )
        self.assertIsInstance(sale_id, int)
        self.assertGreater(sale_id, 0)

    def test_get_by_id(self):
        item_id = self._create_item()
        sale_id = self.repo.create(
            customer_name="Jane",
            items=[{"item_id": item_id, "quantity": 1,
                    "unit_price": 150.0, "cost_price": 80.0}],
        )
        sale = self.repo.get_by_id(sale_id)
        self.assertIsNotNone(sale)
        self.assertEqual(sale.customer_name, "Jane")
        self.assertEqual(sale.total_amount, 150.0)
        self.assertEqual(len(sale.items), 1)

    def test_get_by_id_not_found(self):
        self.assertIsNone(self.repo.get_by_id(999999))

    def test_sale_total_calculated(self):
        item_id = self._create_item()
        sale_id = self.repo.create(
            items=[
                {"item_id": item_id, "quantity": 3, "unit_price": 10.0, "cost_price": 5.0},
                {"item_id": item_id, "quantity": 2, "unit_price": 20.0, "cost_price": 10.0},
            ],
        )
        sale = self.repo.get_by_id(sale_id)
        self.assertEqual(sale.total_amount, 70.0)  # 30 + 40

    def test_sale_with_discount(self):
        item_id = self._create_item()
        sale_id = self.repo.create(
            discount=5.0,
            items=[{"item_id": item_id, "quantity": 1,
                    "unit_price": 100.0, "cost_price": 60.0}],
        )
        sale = self.repo.get_by_id(sale_id)
        self.assertEqual(sale.net_total, 95.0)

    def test_delete_sale(self):
        item_id = self._create_item()
        sale_id = self.repo.create(
            items=[{"item_id": item_id, "quantity": 1,
                    "unit_price": 50.0, "cost_price": 25.0}],
        )
        self.assertTrue(self.repo.delete(sale_id))
        self.assertIsNone(self.repo.get_by_id(sale_id))


# ── List & Filter ────────────────────────────────────────────────────────────

class TestSaleList(_SaleTestBase):

    def test_get_all(self):
        item_id = self._create_item()
        self.repo.create(
            items=[{"item_id": item_id, "quantity": 1,
                    "unit_price": 10.0, "cost_price": 5.0}],
        )
        sales = self.repo.get_all()
        self.assertIsInstance(sales, list)
        self.assertGreater(len(sales), 0)

    def test_get_all_with_limit(self):
        item_id = self._create_item()
        for _ in range(5):
            self.repo.create(
                items=[{"item_id": item_id, "quantity": 1,
                        "unit_price": 10.0, "cost_price": 5.0}],
            )
        sales = self.repo.get_all(limit=2)
        self.assertLessEqual(len(sales), 2)


# ── Reporting ────────────────────────────────────────────────────────────────

class TestSaleReporting(_SaleTestBase):

    def test_daily_totals(self):
        item_id = self._create_item()
        self.repo.create(
            items=[{"item_id": item_id, "quantity": 2,
                    "unit_price": 25.0, "cost_price": 10.0}],
        )
        from datetime import date
        totals = self.repo.daily_totals(date.today().isoformat())
        self.assertIn("count", totals)
        self.assertIn("revenue", totals)
        self.assertIn("profit", totals)
        self.assertGreater(totals["count"], 0)

    def test_top_items(self):
        item_id = self._create_item("TopSeller")
        self.repo.create(
            items=[{"item_id": item_id, "quantity": 10,
                    "unit_price": 5.0, "cost_price": 2.0}],
        )
        top = self.repo.top_items(limit=5)
        self.assertIsInstance(top, list)
        self.assertGreater(len(top), 0)


# ── Model Properties ────────────────────────────────────────────────────────

class TestSaleModel(unittest.TestCase):

    def test_sale_item_profit(self):
        from app.models.sale import SaleItem
        si = SaleItem(
            id=1, sale_id=1, item_id=1,
            quantity=3, unit_price=100.0,
            cost_price=60.0, line_total=300.0,
        )
        self.assertEqual(si.profit, 300.0 - (60.0 * 3))  # 120

    def test_sale_item_count(self):
        from app.models.sale import Sale, SaleItem
        sale = Sale(
            id=1, customer_name="Test", total_amount=200.0,
            discount=0, note="", timestamp="2026-01-01",
            items=[
                SaleItem(id=1, sale_id=1, item_id=1, quantity=3,
                         unit_price=50, cost_price=25, line_total=150),
                SaleItem(id=2, sale_id=1, item_id=2, quantity=2,
                         unit_price=25, cost_price=10, line_total=50),
            ],
        )
        self.assertEqual(sale.item_count, 5)
        self.assertEqual(sale.net_total, 200.0)


if __name__ == "__main__":
    unittest.main()
