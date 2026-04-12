"""
tests/test_customer_repo.py — Tests for CustomerRepository.

Covers CRUD, search, toggle active, delete guard, and summary counts.
"""
from __future__ import annotations

import os
import sys
import unittest
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging; logging.disable(logging.CRITICAL)

import app.core.database as db_mod


class _CustomerTestBase(unittest.TestCase):

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
        self.repo = CustomerRepository()


# ── CRUD ─────────────────────────────────────────────────────────────────────

class TestCustomerCRUD(_CustomerTestBase):

    def test_add_customer(self):
        cid = self.repo.add("Alice Smith")
        self.assertIsInstance(cid, int)
        self.assertGreater(cid, 0)

    def test_add_with_all_fields(self):
        cid = self.repo.add(
            "Bob Jones", phone="+1234", email="bob@test.com",
            address="123 Main St", notes="VIP customer",
        )
        cust = self.repo.get_by_id(cid)
        self.assertIsNotNone(cust)
        self.assertEqual(cust.name, "Bob Jones")
        self.assertEqual(cust.phone, "+1234")
        self.assertEqual(cust.email, "bob@test.com")
        self.assertEqual(cust.address, "123 Main St")
        self.assertEqual(cust.notes, "VIP customer")

    def test_get_by_id(self):
        cid = self.repo.add("Charlie Brown", phone="+49123")
        cust = self.repo.get_by_id(cid)
        self.assertIsNotNone(cust)
        self.assertEqual(cust.name, "Charlie Brown")
        self.assertEqual(cust.phone, "+49123")

    def test_get_by_id_not_found(self):
        self.assertIsNone(self.repo.get_by_id(999999))

    def test_get_all(self):
        self.repo.add("GetAll Customer")
        customers = self.repo.get_all()
        self.assertIsInstance(customers, list)
        self.assertGreater(len(customers), 0)

    def test_get_all_active_only(self):
        cid = self.repo.add("Inactive Customer")
        self.repo.set_active(cid, False)
        active = self.repo.get_all(active_only=True)
        ids = [c.id for c in active]
        self.assertNotIn(cid, ids)

    def test_update(self):
        cid = self.repo.add("Old Name")
        self.repo.update(cid, "New Name", email="new@test.com")
        cust = self.repo.get_by_id(cid)
        self.assertEqual(cust.name, "New Name")
        self.assertEqual(cust.email, "new@test.com")

    def test_set_active(self):
        cid = self.repo.add("Toggle Customer")
        self.repo.set_active(cid, False)
        cust = self.repo.get_by_id(cid)
        self.assertFalse(cust.is_active)
        self.repo.set_active(cid, True)
        cust = self.repo.get_by_id(cid)
        self.assertTrue(cust.is_active)

    def test_delete_no_sales(self):
        cid = self.repo.add("Delete Me")
        result = self.repo.delete(cid)
        self.assertTrue(result)
        self.assertIsNone(self.repo.get_by_id(cid))


# ── Search ───────────────────────────────────────────────────────────────────

class TestCustomerSearch(_CustomerTestBase):

    def test_search_by_name(self):
        self.repo.add("SearchTarget Alpha", phone="111")
        results = self.repo.search("SearchTarget")
        self.assertGreater(len(results), 0)
        self.assertTrue(any("SearchTarget" in c.name for c in results))

    def test_search_by_phone(self):
        self.repo.add("Phone Customer", phone="+99887766")
        results = self.repo.search("+99887766")
        self.assertGreater(len(results), 0)

    def test_search_by_email(self):
        self.repo.add("Email Customer", email="unique_test@example.com")
        results = self.repo.search("unique_test@example")
        self.assertGreater(len(results), 0)

    def test_search_empty(self):
        results = self.repo.search("zzzznonexistent99999")
        self.assertEqual(len(results), 0)


# ── Summary ──────────────────────────────────────────────────────────────────

class TestCustomerSummary(_CustomerTestBase):

    def test_count_returns_dict(self):
        summary = self.repo.count()
        self.assertIn("total", summary)
        self.assertIn("active", summary)
        self.assertIn("with_purchases", summary)
        self.assertIsInstance(summary["total"], int)


# ── Customer Model ───────────────────────────────────────────────────────────

class TestCustomerModel(_CustomerTestBase):

    def test_display_name(self):
        cid = self.repo.add("Display Name Test")
        cust = self.repo.get_by_id(cid)
        self.assertEqual(cust.display_name, "Display Name Test")

    def test_avg_order_zero(self):
        cid = self.repo.add("No Orders")
        cust = self.repo.get_by_id(cid)
        self.assertEqual(cust.avg_order, 0.0)

    def test_purchase_summary_defaults(self):
        cid = self.repo.add("Fresh Customer")
        cust = self.repo.get_by_id(cid)
        self.assertEqual(cust.total_purchases, 0)
        self.assertEqual(cust.total_spent, 0.0)
        self.assertEqual(cust.last_purchase, "")


if __name__ == "__main__":
    unittest.main()
