"""
tests/test_alert_service.py — Tests for AlertService.

Tests cover low stock detection, out of stock detection, and summary stats.
"""
from __future__ import annotations

import unittest
import tempfile
import os
import sys
import shutil
import types

# Add src/files to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock PyQt6 before importing app modules
if 'PyQt6' not in sys.modules:
    class MockQt:
        class LayoutDirection:
            RightToLeft = 1

    class MockQApplication:
        @staticmethod
        def setLayoutDirection(direction):
            pass

    mock_qt = types.ModuleType('PyQt6')
    mock_qtcore = types.ModuleType('QtCore')
    mock_qtwidgets = types.ModuleType('QtWidgets')
    mock_qtcore.Qt = MockQt()
    mock_qtwidgets.QApplication = MockQApplication()
    mock_qt.QtCore = mock_qtcore
    mock_qt.QtWidgets = mock_qtwidgets
    sys.modules['PyQt6'] = mock_qt
    sys.modules['PyQt6.QtCore'] = mock_qtcore
    sys.modules['PyQt6.QtWidgets'] = mock_qtwidgets

import app.core.database as db_mod
from app.repositories.item_repo import ItemRepository
from app.services.alert_service import AlertService


class TestAlertServiceBase(unittest.TestCase):
    """Base class with DB setup."""

    def setUp(self):
        self.test_tmp_dir = tempfile.mkdtemp()
        self.test_db_file = os.path.join(self.test_tmp_dir, "test.db")
        self.original_db_path = db_mod.DB_PATH
        db_mod.DB_PATH = self.test_db_file
        db_mod.init_db()
        self.item_repo = ItemRepository()
        self.alert_svc = AlertService()

    def tearDown(self):
        db_mod.DB_PATH = self.original_db_path
        try:
            shutil.rmtree(self.test_tmp_dir)
        except Exception:
            pass


class TestLowStockDetection(TestAlertServiceBase):
    """Test get_low_stock_items."""

    def test_no_low_stock_when_all_healthy(self):
        self.item_repo.add_product(
            brand="A", name="Item", color="", stock=50,
            barcode="ALERT-001", min_stock=10,
        )
        items = self.alert_svc.get_low_stock_items()
        self.assertEqual(len(items), 0)

    def test_detects_low_stock(self):
        self.item_repo.add_product(
            brand="A", name="Item", color="", stock=5,
            barcode="ALERT-002", min_stock=10,
        )
        items = self.alert_svc.get_low_stock_items()
        self.assertEqual(len(items), 1)

    def test_detects_at_threshold(self):
        self.item_repo.add_product(
            brand="A", name="Item", color="", stock=10,
            barcode="ALERT-003", min_stock=10,
        )
        items = self.alert_svc.get_low_stock_items()
        self.assertEqual(len(items), 1)

    def test_ignores_zero_threshold(self):
        """Items with min_stock=0 should not appear as low stock."""
        self.item_repo.add_product(
            brand="A", name="Item", color="", stock=0,
            barcode="ALERT-004", min_stock=0,
        )
        items = self.alert_svc.get_low_stock_items()
        self.assertEqual(len(items), 0)


class TestOutOfStockDetection(TestAlertServiceBase):
    """Test get_out_of_stock_items."""

    def test_detects_out_of_stock(self):
        self.item_repo.add_product(
            brand="A", name="Item", color="", stock=0,
            barcode="ALERT-OOS-001", min_stock=5,
        )
        items = self.alert_svc.get_out_of_stock_items()
        self.assertEqual(len(items), 1)

    def test_low_not_out(self):
        self.item_repo.add_product(
            brand="A", name="Item", color="", stock=3,
            barcode="ALERT-OOS-002", min_stock=10,
        )
        items = self.alert_svc.get_out_of_stock_items()
        self.assertEqual(len(items), 0)


class TestAlertSummary(TestAlertServiceBase):
    """Test summary method."""

    def test_empty_summary(self):
        s = self.alert_svc.summary()
        self.assertEqual(s["low_count"], 0)
        self.assertEqual(s["out_count"], 0)

    def test_summary_with_mixed_stock(self):
        self.item_repo.add_product(
            brand="A", name="OK", color="", stock=50,
            barcode="SUM-001", min_stock=10,
        )
        self.item_repo.add_product(
            brand="B", name="Low", color="", stock=3,
            barcode="SUM-002", min_stock=10,
        )
        self.item_repo.add_product(
            brand="C", name="Out", color="", stock=0,
            barcode="SUM-003", min_stock=5,
        )
        s = self.alert_svc.summary()
        self.assertGreaterEqual(s["low_count"], 2)  # low includes out
        self.assertGreaterEqual(s["out_count"], 1)

    def test_summary_has_inventory_value(self):
        self.item_repo.add_product(
            brand="A", name="Item", color="", stock=10,
            barcode="SUM-VAL", min_stock=2, sell_price=100.0,
        )
        s = self.alert_svc.summary()
        self.assertGreaterEqual(s["inventory_value"], 1000.0)


if __name__ == "__main__":
    unittest.main()
