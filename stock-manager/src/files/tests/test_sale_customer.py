"""
tests/test_sale_customer.py — Tests for customer_id linkage in sales.

Verifies that sales correctly store and retrieve customer_id.
"""
from __future__ import annotations

import os
import sys
import unittest
import tempfile
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging; logging.disable(logging.CRITICAL)

import app.core.database as db_mod


class _SaleCustomerBase(unittest.TestCase):

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
        from app.repositories.customer_repo import CustomerRepository
        from app.repositories.sale_repo import SaleRepository
        from app.repositories.item_repo import ItemRepository
        self.cust_repo = CustomerRepository()
        self.sale_repo = SaleRepository()
        self.item_repo = ItemRepository()


class TestSaleCustomerLink(_SaleCustomerBase):

    def _create_product(self) -> int:
        """Helper to create a product for sale items with unique barcode."""
        barcode = f"SC-{uuid.uuid4().hex[:8].upper()}"
        return self.item_repo.add_product(
            brand="Test", name="Widget", color="Blue",
            stock=100, barcode=barcode, min_stock=5,
            sell_price=19.99,
        )

    def test_sale_with_customer_id(self):
        """Sale should store and retrieve customer_id."""
        cid = self.cust_repo.add("Sale Customer", phone="+123")
        pid = self._create_product()
        items = [{"item_id": pid, "quantity": 1, "unit_price": 19.99, "cost_price": 10.0}]
        sale_id = self.sale_repo.create(
            customer_name="Sale Customer", items=items, customer_id=cid,
        )
        sale = self.sale_repo.get_by_id(sale_id)
        self.assertIsNotNone(sale)
        self.assertEqual(sale.customer_id, cid)
        self.assertEqual(sale.customer_name, "Sale Customer")

    def test_sale_without_customer_id(self):
        """Walk-in sale should have customer_id=None."""
        pid = self._create_product()
        items = [{"item_id": pid, "quantity": 1, "unit_price": 19.99, "cost_price": 10.0}]
        sale_id = self.sale_repo.create(
            customer_name="Walk-in", items=items,
        )
        sale = self.sale_repo.get_by_id(sale_id)
        self.assertIsNotNone(sale)
        self.assertIsNone(sale.customer_id)

    def test_customer_purchase_summary(self):
        """Customer repo should reflect purchase stats from linked sales."""
        cid = self.cust_repo.add("Summary Customer")
        pid = self._create_product()
        items = [{"item_id": pid, "quantity": 2, "unit_price": 19.99, "cost_price": 10.0}]
        self.sale_repo.create(
            customer_name="Summary Customer", items=items, customer_id=cid,
        )
        cust = self.cust_repo.get_by_id(cid)
        self.assertEqual(cust.total_purchases, 1)
        self.assertGreater(cust.total_spent, 0)

    def test_delete_customer_with_sales_blocked(self):
        """Deleting a customer with linked sales should fail."""
        cid = self.cust_repo.add("Has Sales")
        pid = self._create_product()
        items = [{"item_id": pid, "quantity": 1, "unit_price": 19.99, "cost_price": 10.0}]
        self.sale_repo.create(
            customer_name="Has Sales", items=items, customer_id=cid,
        )
        result = self.cust_repo.delete(cid)
        self.assertFalse(result)
        # Customer should still exist
        self.assertIsNotNone(self.cust_repo.get_by_id(cid))


if __name__ == "__main__":
    unittest.main()
