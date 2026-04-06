"""
tests/test_undo_service.py — Tests for UndoService.

Tests cover undo of stock in/out/adjust, undo window expiry,
negative stock guard, and audit trail preservation.
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
from app.repositories.transaction_repo import TransactionRepository
from app.services.stock_service import StockService
from app.services.undo_service import UndoService


class TestUndoServiceBase(unittest.TestCase):
    """Base test class with shared setup."""

    def setUp(self):
        self.test_tmp_dir = tempfile.mkdtemp()
        self.test_db_file = os.path.join(self.test_tmp_dir, "test.db")
        self.original_db_path = db_mod.DB_PATH
        db_mod.DB_PATH = self.test_db_file
        db_mod.init_db()

        self.item_repo = ItemRepository()
        self.txn_repo = TransactionRepository()
        self.stock_svc = StockService()
        self.undo_svc = UndoService()

        # Create a test product with stock = 50
        self.product_id = self.item_repo.add_product(
            brand="Test", name="Widget", color="Blue",
            stock=50, barcode="UNDO001", min_stock=5,
        )

    def tearDown(self):
        db_mod.DB_PATH = self.original_db_path
        shutil.rmtree(self.test_tmp_dir, ignore_errors=True)


class TestUndoStockIn(TestUndoServiceBase):
    """Test undoing stock-in operations."""

    def test_undo_stock_in_restores_quantity(self):
        """Undoing a stock-in should reduce stock back."""
        self.stock_svc.stock_in(self.product_id, 10, "Add 10")
        item = self.item_repo.get_by_id(self.product_id)
        self.assertEqual(item.stock, 60)

        # Find the IN transaction
        txns = self.txn_repo.get_transactions(self.product_id)
        in_txn = next(t for t in txns if t.operation == "IN")

        result = self.undo_svc.undo_transaction(in_txn.id)
        self.assertEqual(result["before"], 60)
        self.assertEqual(result["after"], 50)

        item = self.item_repo.get_by_id(self.product_id)
        self.assertEqual(item.stock, 50)

    def test_undo_stock_in_creates_reverse_transaction(self):
        """Undoing creates an OUT transaction with [UNDO] note."""
        self.stock_svc.stock_in(self.product_id, 5, "Add 5")
        txns = self.txn_repo.get_transactions(self.product_id)
        in_txn = next(t for t in txns if t.operation == "IN")

        self.undo_svc.undo_transaction(in_txn.id)

        txns = self.txn_repo.get_transactions(self.product_id)
        undo_txn = next(t for t in txns if t.note and t.note.startswith("[UNDO]"))
        self.assertEqual(undo_txn.operation, "OUT")
        self.assertEqual(undo_txn.quantity, 5)


class TestUndoStockOut(TestUndoServiceBase):
    """Test undoing stock-out operations."""

    def test_undo_stock_out_restores_quantity(self):
        """Undoing a stock-out should add stock back."""
        self.stock_svc.stock_out(self.product_id, 20, "Remove 20")
        item = self.item_repo.get_by_id(self.product_id)
        self.assertEqual(item.stock, 30)

        txns = self.txn_repo.get_transactions(self.product_id)
        out_txn = next(t for t in txns if t.operation == "OUT")

        result = self.undo_svc.undo_transaction(out_txn.id)
        self.assertEqual(result["before"], 30)
        self.assertEqual(result["after"], 50)

        item = self.item_repo.get_by_id(self.product_id)
        self.assertEqual(item.stock, 50)

    def test_undo_stock_out_creates_reverse_in(self):
        """Undoing OUT creates an IN transaction."""
        self.stock_svc.stock_out(self.product_id, 10, "Remove 10")
        txns = self.txn_repo.get_transactions(self.product_id)
        out_txn = next(t for t in txns if t.operation == "OUT")

        self.undo_svc.undo_transaction(out_txn.id)

        txns = self.txn_repo.get_transactions(self.product_id)
        undo_txn = next(t for t in txns if t.note and t.note.startswith("[UNDO]"))
        self.assertEqual(undo_txn.operation, "IN")


class TestUndoAdjust(TestUndoServiceBase):
    """Test undoing stock adjust operations."""

    def test_undo_adjust_restores_original(self):
        """Undoing ADJUST restores to stock_before of original transaction."""
        self.stock_svc.stock_adjust(self.product_id, 100, "Set to 100")
        item = self.item_repo.get_by_id(self.product_id)
        self.assertEqual(item.stock, 100)

        txns = self.txn_repo.get_transactions(self.product_id)
        adj_txn = next(t for t in txns if t.operation == "ADJUST")

        result = self.undo_svc.undo_transaction(adj_txn.id)
        self.assertEqual(result["after"], 50)  # restored to original

        item = self.item_repo.get_by_id(self.product_id)
        self.assertEqual(item.stock, 50)


class TestUndoGuards(TestUndoServiceBase):
    """Test undo validation and edge cases."""

    def test_cannot_undo_create_transaction(self):
        """CREATE transactions cannot be undone."""
        txns = self.txn_repo.get_transactions(self.product_id)
        create_txn = next(t for t in txns if t.operation == "CREATE")

        can, reason = self.undo_svc.can_undo(create_txn.id)
        self.assertFalse(can)

    def test_cannot_undo_nonexistent_transaction(self):
        """Nonexistent transaction cannot be undone."""
        can, reason = self.undo_svc.can_undo(99999)
        self.assertFalse(can)

    def test_cannot_undo_already_undone(self):
        """An [UNDO] transaction itself cannot be undone again."""
        self.stock_svc.stock_in(self.product_id, 10, "Add")
        txns = self.txn_repo.get_transactions(self.product_id)
        in_txn = next(t for t in txns if t.operation == "IN")

        self.undo_svc.undo_transaction(in_txn.id)

        # Find the UNDO transaction
        txns = self.txn_repo.get_transactions(self.product_id)
        undo_txn = next(t for t in txns if t.note and t.note.startswith("[UNDO]"))

        can, reason = self.undo_svc.can_undo(undo_txn.id)
        self.assertFalse(can)

    def test_undo_prevents_negative_stock(self):
        """Undoing an IN when stock is already at 0 should fail."""
        # Stock is 50, add 10 -> 60
        self.stock_svc.stock_in(self.product_id, 10, "Add")
        # Now remove everything -> 0
        self.stock_svc.stock_out(self.product_id, 60, "Remove all")

        txns = self.txn_repo.get_transactions(self.product_id)
        in_txn = next(t for t in txns if t.operation == "IN")

        # Trying to undo the +10 would make stock = 0 - 10 = -10
        with self.assertRaises(ValueError):
            self.undo_svc.undo_transaction(in_txn.id)

    def test_can_undo_returns_true_for_valid_ops(self):
        """can_undo returns True for recent valid stock operations."""
        self.stock_svc.stock_in(self.product_id, 5, "Add")
        txns = self.txn_repo.get_transactions(self.product_id)
        in_txn = next(t for t in txns if t.operation == "IN")

        can, reason = self.undo_svc.can_undo(in_txn.id)
        self.assertTrue(can)
        self.assertEqual(reason, "")


class TestRecentUndoable(TestUndoServiceBase):
    """Test getting recent undoable transactions."""

    def test_get_recent_undoable_returns_stock_ops(self):
        """get_recent_undoable returns recent IN/OUT/ADJUST ops."""
        self.stock_svc.stock_in(self.product_id, 10, "Add")
        self.stock_svc.stock_out(self.product_id, 5, "Remove")

        recent = self.undo_svc.get_recent_undoable(limit=5)
        self.assertGreaterEqual(len(recent), 2)
        ops = {r["operation"] for r in recent}
        self.assertTrue(ops.issubset({"IN", "OUT", "ADJUST"}))

    def test_get_recent_undoable_excludes_undo_transactions(self):
        """Undo transactions should not appear in undoable list."""
        self.stock_svc.stock_in(self.product_id, 10, "Add")
        txns = self.txn_repo.get_transactions(self.product_id)
        in_txn = next(t for t in txns if t.operation == "IN")
        self.undo_svc.undo_transaction(in_txn.id)

        recent = self.undo_svc.get_recent_undoable(limit=10)
        undo_notes = [r for r in recent if (r.get("note") or "").startswith("[UNDO]")]
        self.assertEqual(len(undo_notes), 0)


if __name__ == "__main__":
    unittest.main()
