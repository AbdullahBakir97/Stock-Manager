"""
tests/test_return_service.py — Tests for ReturnService & ReturnRepository.

Tests cover return processing with RESTOCK and WRITEOFF actions,
stock integration, summary stats, and validation.
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
from app.repositories.return_repo import ReturnRepository
from app.services.return_service import ReturnService
from app.services.stock_service import StockService


class TestReturnBase(unittest.TestCase):
    """Base test class with shared setup for return tests."""

    def setUp(self):
        self.test_tmp_dir = tempfile.mkdtemp()
        self.test_db_file = os.path.join(self.test_tmp_dir, "test.db")
        self.original_db_path = db_mod.DB_PATH
        db_mod.DB_PATH = self.test_db_file
        db_mod.init_db()

        self.item_repo = ItemRepository()
        self.ret_repo = ReturnRepository()
        self.ret_svc = ReturnService()
        self.stock_svc = StockService()

        # Create sample inventory items
        self.item1_id = self.item_repo.add_product(
            brand="Apple", name="iPhone Case", color="Blue",
            stock=50, barcode="RET-TEST-001", min_stock=5, sell_price=19.99,
        )
        self.item2_id = self.item_repo.add_product(
            brand="Samsung", name="Charger Cable", color="White",
            stock=30, barcode="RET-TEST-002", min_stock=10, sell_price=14.99,
        )

    def tearDown(self):
        db_mod.DB_PATH = self.original_db_path
        try:
            shutil.rmtree(self.test_tmp_dir)
        except Exception:
            pass


# ── Repository Tests ─────────────────────────────────────────────────────────

class TestReturnRepoCreate(TestReturnBase):
    """Test ReturnRepository.create."""

    def test_create_return_returns_id(self):
        ret_id = self.ret_repo.create(
            item_id=self.item1_id, quantity=2, reason="Defective",
            action="RESTOCK", refund_amount=39.98,
        )
        self.assertIsNotNone(ret_id)
        self.assertGreater(ret_id, 0)

    def test_create_writeoff_return(self):
        ret_id = self.ret_repo.create(
            item_id=self.item1_id, quantity=1, reason="Damaged beyond repair",
            action="WRITEOFF", refund_amount=19.99,
        )
        self.assertGreater(ret_id, 0)

    def test_create_return_with_sale_id(self):
        # Create a fake sale for FK (sale_id is nullable, so None works too)
        ret_id = self.ret_repo.create(
            item_id=self.item1_id, quantity=1, reason="Wrong item",
            action="RESTOCK", sale_id=None,
        )
        self.assertGreater(ret_id, 0)


class TestReturnRepoGetAll(TestReturnBase):
    """Test ReturnRepository.get_all."""

    def test_get_all_empty(self):
        returns = self.ret_repo.get_all()
        self.assertEqual(len(returns), 0)

    def test_get_all_returns_records(self):
        self.ret_repo.create(item_id=self.item1_id, quantity=2, reason="A", action="RESTOCK")
        self.ret_repo.create(item_id=self.item2_id, quantity=1, reason="B", action="WRITEOFF")
        returns = self.ret_repo.get_all()
        self.assertEqual(len(returns), 2)

    def test_get_all_respects_limit(self):
        for i in range(5):
            self.ret_repo.create(item_id=self.item1_id, quantity=1, reason=f"R{i}", action="RESTOCK")
        returns = self.ret_repo.get_all(limit=3)
        self.assertEqual(len(returns), 3)

    def test_get_all_has_item_names(self):
        self.ret_repo.create(item_id=self.item1_id, quantity=1, reason="Test", action="RESTOCK")
        returns = self.ret_repo.get_all()
        self.assertIn("iPhone Case", returns[0].item_name)


class TestReturnRepoSummary(TestReturnBase):
    """Test ReturnRepository.get_summary."""

    def test_summary_empty(self):
        summary = self.ret_repo.get_summary()
        self.assertEqual(summary["total"], 0)

    def test_summary_counts_actions(self):
        self.ret_repo.create(item_id=self.item1_id, quantity=3, action="RESTOCK", refund_amount=59.97)
        self.ret_repo.create(item_id=self.item2_id, quantity=2, action="WRITEOFF", refund_amount=29.98)
        self.ret_repo.create(item_id=self.item1_id, quantity=1, action="RESTOCK", refund_amount=19.99)

        summary = self.ret_repo.get_summary()
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["restocked"], 4)   # 3 + 1
        self.assertEqual(summary["writeoff"], 2)
        self.assertAlmostEqual(summary["total_refunded"], 109.94, places=2)


# ── Service Tests ────────────────────────────────────────────────────────────

class TestReturnServiceRestock(TestReturnBase):
    """Test ReturnService.process_return with RESTOCK action."""

    def test_restock_increases_stock(self):
        original_item = self.item_repo.get_by_id(self.item1_id)
        original_stock = original_item.stock  # 50

        self.ret_svc.process_return(
            item_id=self.item1_id, quantity=5,
            reason="Customer changed mind", action="RESTOCK",
            refund_amount=99.95,
        )

        updated_item = self.item_repo.get_by_id(self.item1_id)
        self.assertEqual(updated_item.stock, original_stock + 5)

    def test_restock_creates_return_record(self):
        ret_id = self.ret_svc.process_return(
            item_id=self.item1_id, quantity=2,
            reason="Wrong color", action="RESTOCK",
        )
        self.assertGreater(ret_id, 0)
        returns = self.ret_repo.get_all()
        self.assertEqual(len(returns), 1)
        self.assertEqual(returns[0].action, "RESTOCK")

    def test_restock_creates_transaction_log(self):
        self.ret_svc.process_return(
            item_id=self.item1_id, quantity=3,
            reason="Return", action="RESTOCK",
        )
        conn = db_mod.get_connection()
        txns = conn.execute(
            "SELECT * FROM inventory_transactions WHERE item_id=? AND operation='IN'",
            (self.item1_id,),
        ).fetchall()
        conn.close()
        self.assertGreater(len(txns), 0)
        self.assertEqual(txns[-1]["quantity"], 3)


class TestReturnServiceWriteoff(TestReturnBase):
    """Test ReturnService.process_return with WRITEOFF action."""

    def test_writeoff_does_not_change_stock(self):
        original_item = self.item_repo.get_by_id(self.item1_id)
        original_stock = original_item.stock  # 50

        self.ret_svc.process_return(
            item_id=self.item1_id, quantity=2,
            reason="Broken beyond repair", action="WRITEOFF",
            refund_amount=39.98,
        )

        updated_item = self.item_repo.get_by_id(self.item1_id)
        self.assertEqual(updated_item.stock, original_stock)

    def test_writeoff_creates_return_record(self):
        ret_id = self.ret_svc.process_return(
            item_id=self.item1_id, quantity=1,
            reason="Shattered screen", action="WRITEOFF",
            refund_amount=19.99,
        )
        returns = self.ret_repo.get_all()
        self.assertEqual(len(returns), 1)
        self.assertEqual(returns[0].action, "WRITEOFF")
        self.assertEqual(returns[0].refund_amount, 19.99)

    def test_writeoff_no_stock_transaction(self):
        """WRITEOFF should NOT create an inventory_transactions IN record."""
        self.ret_svc.process_return(
            item_id=self.item1_id, quantity=1,
            reason="Lost", action="WRITEOFF",
        )
        conn = db_mod.get_connection()
        txns = conn.execute(
            "SELECT * FROM inventory_transactions WHERE item_id=? AND operation='IN' AND note LIKE 'Return%'",
            (self.item1_id,),
        ).fetchall()
        conn.close()
        self.assertEqual(len(txns), 0)


class TestReturnServiceValidation(TestReturnBase):
    """Test ReturnService validation."""

    def test_zero_quantity_raises(self):
        with self.assertRaises(ValueError):
            self.ret_svc.process_return(
                item_id=self.item1_id, quantity=0,
                reason="Test", action="RESTOCK",
            )

    def test_negative_quantity_raises(self):
        with self.assertRaises(ValueError):
            self.ret_svc.process_return(
                item_id=self.item1_id, quantity=-3,
                reason="Test", action="RESTOCK",
            )


class TestReturnServiceIntegration(TestReturnBase):
    """Integration tests combining returns with stock operations."""

    def test_multiple_returns_accumulate(self):
        original = self.item_repo.get_by_id(self.item1_id).stock  # 50
        self.ret_svc.process_return(item_id=self.item1_id, quantity=5, action="RESTOCK")
        self.ret_svc.process_return(item_id=self.item1_id, quantity=3, action="RESTOCK")
        updated = self.item_repo.get_by_id(self.item1_id).stock
        self.assertEqual(updated, original + 8)

    def test_mixed_restock_and_writeoff(self):
        original = self.item_repo.get_by_id(self.item1_id).stock  # 50
        self.ret_svc.process_return(item_id=self.item1_id, quantity=5, action="RESTOCK")
        self.ret_svc.process_return(item_id=self.item1_id, quantity=2, action="WRITEOFF")
        updated = self.item_repo.get_by_id(self.item1_id).stock
        # Only RESTOCK adds, WRITEOFF doesn't touch stock
        self.assertEqual(updated, original + 5)

    def test_return_after_stock_out(self):
        """Stock out → return → stock restored correctly."""
        self.stock_svc.stock_out(self.item1_id, 20, "Sale")
        mid = self.item_repo.get_by_id(self.item1_id).stock  # 30
        self.assertEqual(mid, 30)

        self.ret_svc.process_return(item_id=self.item1_id, quantity=10, action="RESTOCK")
        final = self.item_repo.get_by_id(self.item1_id).stock
        self.assertEqual(final, 40)

    def test_summary_after_multiple_returns(self):
        self.ret_svc.process_return(
            item_id=self.item1_id, quantity=3, action="RESTOCK", refund_amount=59.97,
        )
        self.ret_svc.process_return(
            item_id=self.item2_id, quantity=1, action="WRITEOFF", refund_amount=14.99,
        )
        summary = self.ret_repo.get_summary()
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["restocked"], 3)
        self.assertEqual(summary["writeoff"], 1)
        self.assertAlmostEqual(summary["total_refunded"], 74.96, places=2)


if __name__ == "__main__":
    unittest.main()
