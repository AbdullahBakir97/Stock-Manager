"""
tests/test_stock_service.py — Tests for StockService.

Tests cover stock_in, stock_out, and stock_adjust operations with valid
and invalid inputs.
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
from app.services.stock_service import StockService


class TestStockServiceBase(unittest.TestCase):
    """Base test class with shared setup."""

    def setUp(self):
        """Create fresh services for each test with unique DB."""
        self.test_tmp_dir = tempfile.mkdtemp()
        self.test_db_file = os.path.join(self.test_tmp_dir, "test.db")
        self.original_db_path = db_mod.DB_PATH
        db_mod.DB_PATH = self.test_db_file
        db_mod.init_db()
        self.item_repo = ItemRepository()
        self.stock_svc = StockService()
        self.sample_product = self.item_repo.add_product(
            brand="Apple",
            name="Screen Protector",
            color="Clear",
            stock=50,
            barcode="TEST-STOCK",
            min_stock=10,
            sell_price=9.99,
        )

    def tearDown(self):
        """Clean up test database."""
        db_mod.DB_PATH = self.original_db_path
        try:
            shutil.rmtree(self.test_tmp_dir)
        except:
            pass


class TestStockIn(TestStockServiceBase):
    """Test stock_in operation."""

    def test_stock_in_normal_operation(self):
        """Test normal stock_in increases inventory."""
        result = self.stock_svc.stock_in(self.sample_product, 20, note="Restock")

        self.assertEqual(result["before"], 50)
        self.assertEqual(result["after"], 70)
        self.assertEqual(result["delta"], 20)

    def test_stock_in_zero_quantity_raises_error(self):
        """Test stock_in with zero quantity raises ValueError."""
        with self.assertRaises(ValueError):
            self.stock_svc.stock_in(self.sample_product, 0)

    def test_stock_in_negative_quantity_raises_error(self):
        """Test stock_in with negative quantity raises ValueError."""
        with self.assertRaises(ValueError):
            self.stock_svc.stock_in(self.sample_product, -10)

    def test_stock_in_invalid_item_raises_error(self):
        """Test stock_in with non-existent item raises ValueError."""
        with self.assertRaises(ValueError):
            self.stock_svc.stock_in(9999, 10)

    def test_stock_in_creates_transaction(self):
        """Test stock_in creates a transaction record."""
        self.stock_svc.stock_in(self.sample_product, 15, note="Supplier delivery")

        conn = db_mod.get_connection()
        rows = conn.execute(
            "SELECT * FROM inventory_transactions WHERE item_id=? ORDER BY id DESC LIMIT 1",
            (self.sample_product,)
        ).fetchall()
        conn.close()

        self.assertGreater(len(rows), 0)
        txn = rows[0]
        self.assertEqual(txn["operation"], "IN")
        self.assertEqual(txn["quantity"], 15)
        self.assertEqual(txn["note"], "Supplier delivery")


class TestStockOut(TestStockServiceBase):
    """Test stock_out operation."""

    def test_stock_out_normal_operation(self):
        """Test normal stock_out decreases inventory."""
        result = self.stock_svc.stock_out(self.sample_product, 10, note="Sale")

        self.assertEqual(result["before"], 50)
        self.assertEqual(result["after"], 40)
        self.assertEqual(result["delta"], -10)

    def test_stock_out_zero_quantity_raises_error(self):
        """Test stock_out with zero quantity raises ValueError."""
        with self.assertRaises(ValueError):
            self.stock_svc.stock_out(self.sample_product, 0)

    def test_stock_out_negative_quantity_raises_error(self):
        """Test stock_out with negative quantity raises ValueError."""
        with self.assertRaises(ValueError):
            self.stock_svc.stock_out(self.sample_product, -5)

    def test_stock_out_insufficient_stock_raises_error(self):
        """Test stock_out with insufficient stock raises ValueError."""
        with self.assertRaises(ValueError):
            self.stock_svc.stock_out(self.sample_product, 100)

    def test_stock_out_invalid_item_raises_error(self):
        """Test stock_out with non-existent item raises ValueError."""
        with self.assertRaises(ValueError):
            self.stock_svc.stock_out(9999, 10)

    def test_stock_out_creates_transaction(self):
        """Test stock_out creates a transaction record."""
        self.stock_svc.stock_out(self.sample_product, 5, note="Customer purchase")

        conn = db_mod.get_connection()
        rows = conn.execute(
            "SELECT * FROM inventory_transactions WHERE item_id=? ORDER BY id DESC LIMIT 1",
            (self.sample_product,)
        ).fetchall()
        conn.close()

        self.assertGreater(len(rows), 0)
        txn = rows[0]
        self.assertEqual(txn["operation"], "OUT")
        self.assertEqual(txn["quantity"], 5)
        self.assertEqual(txn["stock_before"], 50)
        self.assertEqual(txn["stock_after"], 45)

    def test_stock_out_multiple_times(self):
        """Test multiple stock_out operations in sequence."""
        self.stock_svc.stock_out(self.sample_product, 10)
        self.stock_svc.stock_out(self.sample_product, 15)

        item = self.item_repo.get_by_id(self.sample_product)
        self.assertEqual(item.stock, 25)


class TestStockAdjust(TestStockServiceBase):
    """Test stock_adjust operation."""

    def test_stock_adjust_increase(self):
        """Test stock_adjust increases inventory to exact value."""
        result = self.stock_svc.stock_adjust(self.sample_product, 100, note="Inventory check")

        self.assertEqual(result["before"], 50)
        self.assertEqual(result["after"], 100)
        self.assertEqual(result["delta"], 50)

    def test_stock_adjust_decrease(self):
        """Test stock_adjust decreases inventory to exact value."""
        result = self.stock_svc.stock_adjust(self.sample_product, 20, note="Shrinkage adjustment")

        self.assertEqual(result["before"], 50)
        self.assertEqual(result["after"], 20)
        self.assertEqual(result["delta"], -30)

    def test_stock_adjust_to_zero(self):
        """Test stock_adjust sets stock to zero."""
        result = self.stock_svc.stock_adjust(self.sample_product, 0, note="Clearance")

        self.assertEqual(result["after"], 0)

    def test_stock_adjust_negative_raises_error(self):
        """Test stock_adjust with negative stock raises ValueError."""
        with self.assertRaises(ValueError):
            self.stock_svc.stock_adjust(self.sample_product, -10)

    def test_stock_adjust_invalid_item_raises_error(self):
        """Test stock_adjust with non-existent item raises ValueError."""
        with self.assertRaises(ValueError):
            self.stock_svc.stock_adjust(9999, 50)

    def test_stock_adjust_creates_transaction(self):
        """Test stock_adjust creates a transaction record."""
        self.stock_svc.stock_adjust(self.sample_product, 75, note="Physical count")

        conn = db_mod.get_connection()
        rows = conn.execute(
            "SELECT * FROM inventory_transactions WHERE item_id=? ORDER BY id DESC LIMIT 1",
            (self.sample_product,)
        ).fetchall()
        conn.close()

        self.assertGreater(len(rows), 0)
        txn = rows[0]
        self.assertEqual(txn["operation"], "ADJUST")
        self.assertEqual(txn["stock_before"], 50)
        self.assertEqual(txn["stock_after"], 75)


class TestStockServiceIntegration(TestStockServiceBase):
    """Integration tests combining multiple operations."""

    def test_stock_in_then_out(self):
        """Test stock_in followed by stock_out."""
        self.stock_svc.stock_in(self.sample_product, 30)
        result = self.stock_svc.stock_out(self.sample_product, 25)

        self.assertEqual(result["before"], 80)
        self.assertEqual(result["after"], 55)

    def test_multiple_operations_sequence(self):
        """Test sequence of mixed operations."""
        self.stock_svc.stock_in(self.sample_product, 10)
        self.stock_svc.stock_out(self.sample_product, 20)
        self.stock_svc.stock_adjust(self.sample_product, 45)

        item = self.item_repo.get_by_id(self.sample_product)
        self.assertEqual(item.stock, 45)

    def test_stock_changes_persist(self):
        """Test that stock changes persist in repository."""
        self.stock_svc.stock_in(self.sample_product, 25)

        item = self.item_repo.get_by_id(self.sample_product)
        self.assertEqual(item.stock, 75)


if __name__ == "__main__":
    unittest.main()
