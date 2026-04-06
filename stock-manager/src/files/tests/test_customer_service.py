"""
tests/test_customer_service.py — Tests for CustomerService.

Covers business logic: validation, toggle, summary delegation.
"""
from __future__ import annotations

import os
import sys
import unittest
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging; logging.disable(logging.CRITICAL)

import app.core.database as db_mod


class _CustomerSvcBase(unittest.TestCase):

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
        from app.services.customer_service import CustomerService
        self.svc = CustomerService()


# ── Add / Update ─────────────────────────────────────────────────────────────

class TestCustomerServiceAdd(_CustomerSvcBase):

    def test_add_customer(self):
        cid = self.svc.add_customer("Service Test")
        self.assertIsInstance(cid, int)
        self.assertGreater(cid, 0)

    def test_add_customer_strips_whitespace(self):
        cid = self.svc.add_customer("  Whitespace  ", phone=" 123 ")
        cust = self.svc.get_by_id(cid)
        self.assertEqual(cust.name, "Whitespace")
        self.assertEqual(cust.phone, "123")

    def test_add_customer_empty_name_raises(self):
        with self.assertRaises(ValueError):
            self.svc.add_customer("")

    def test_add_customer_whitespace_only_raises(self):
        with self.assertRaises(ValueError):
            self.svc.add_customer("   ")

    def test_update_customer(self):
        cid = self.svc.add_customer("Before Update")
        self.svc.update_customer(cid, "After Update", email="test@test.com")
        cust = self.svc.get_by_id(cid)
        self.assertEqual(cust.name, "After Update")
        self.assertEqual(cust.email, "test@test.com")

    def test_update_empty_name_raises(self):
        cid = self.svc.add_customer("Valid Name")
        with self.assertRaises(ValueError):
            self.svc.update_customer(cid, "")


# ── Toggle / Delete ──────────────────────────────────────────────────────────

class TestCustomerServiceToggle(_CustomerSvcBase):

    def test_toggle_active(self):
        cid = self.svc.add_customer("Toggle Test")
        cust = self.svc.get_by_id(cid)
        self.assertTrue(cust.is_active)
        self.svc.toggle_active(cid)
        cust = self.svc.get_by_id(cid)
        self.assertFalse(cust.is_active)
        self.svc.toggle_active(cid)
        cust = self.svc.get_by_id(cid)
        self.assertTrue(cust.is_active)

    def test_delete_customer(self):
        cid = self.svc.add_customer("Delete Via Service")
        result = self.svc.delete_customer(cid)
        self.assertTrue(result)
        self.assertIsNone(self.svc.get_by_id(cid))


# ── Summary / Search ────────────────────────────────────────────────────────

class TestCustomerServiceQuery(_CustomerSvcBase):

    def test_get_summary(self):
        summary = self.svc.get_summary()
        self.assertIn("total", summary)
        self.assertIn("active", summary)
        self.assertIn("with_purchases", summary)

    def test_search(self):
        self.svc.add_customer("UniqueSearchSvc99")
        results = self.svc.search("UniqueSearchSvc99")
        self.assertGreater(len(results), 0)

    def test_get_all(self):
        self.svc.add_customer("GetAll Svc Test")
        results = self.svc.get_all()
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    def test_get_all_active_only(self):
        cid = self.svc.add_customer("Inactive Svc Test")
        self.svc.toggle_active(cid)
        active = self.svc.get_all(active_only=True)
        ids = [c.id for c in active]
        self.assertNotIn(cid, ids)


if __name__ == "__main__":
    unittest.main()
