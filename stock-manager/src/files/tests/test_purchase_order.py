"""
tests/test_purchase_order.py — Tests for PurchaseOrderService & PurchaseOrderRepository.

Tests cover PO creation, sending, receiving (full & partial),
closing, cancelling, line management, and stock-in integration.
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
from app.repositories.purchase_order_repo import PurchaseOrderRepository
from app.services.purchase_order_service import PurchaseOrderService
from app.services.stock_service import StockService


class TestPurchaseOrderBase(unittest.TestCase):
    """Base test class with shared setup for PO tests."""

    def setUp(self):
        self.test_tmp_dir = tempfile.mkdtemp()
        self.test_db_file = os.path.join(self.test_tmp_dir, "test.db")
        self.original_db_path = db_mod.DB_PATH
        db_mod.DB_PATH = self.test_db_file
        db_mod.init_db()

        self.item_repo = ItemRepository()
        self.po_repo = PurchaseOrderRepository()
        self.po_svc = PurchaseOrderService()
        self.stock_svc = StockService()

        # Create a supplier
        conn = db_mod.get_connection()
        cur = conn.execute(
            "INSERT INTO suppliers (name, phone) VALUES (?, ?)",
            ("Test Supplier", "+49 123"),
        )
        self.supplier_id = cur.lastrowid
        conn.commit()
        conn.close()

        # Create sample inventory items
        self.item1_id = self.item_repo.add_product(
            brand="Apple", name="iPhone 15 Screen", color="Black",
            stock=10, barcode="PO-TEST-001", min_stock=5, sell_price=49.99,
        )
        self.item2_id = self.item_repo.add_product(
            brand="Samsung", name="Galaxy S24 Battery", color="",
            stock=5, barcode="PO-TEST-002", min_stock=3, sell_price=29.99,
        )

    def tearDown(self):
        db_mod.DB_PATH = self.original_db_path
        try:
            shutil.rmtree(self.test_tmp_dir)
        except Exception:
            pass


# ── Repository Tests ─────────────────────────────────────────────────────────

class TestPOCreation(TestPurchaseOrderBase):
    """Test PO creation and basic CRUD."""

    def test_create_po_returns_id(self):
        po_id = self.po_repo.create(supplier_id=self.supplier_id, notes="First order")
        self.assertIsNotNone(po_id)
        self.assertGreater(po_id, 0)

    def test_create_po_generates_po_number(self):
        po_id = self.po_repo.create(supplier_id=self.supplier_id)
        po = self.po_repo.get_by_id(po_id)
        self.assertIsNotNone(po)
        self.assertTrue(po.po_number.startswith("PO-"))
        self.assertEqual(po.status, "DRAFT")

    def test_po_numbers_auto_increment(self):
        id1 = self.po_repo.create(supplier_id=self.supplier_id)
        id2 = self.po_repo.create(supplier_id=self.supplier_id)
        po1 = self.po_repo.get_by_id(id1)
        po2 = self.po_repo.get_by_id(id2)
        num1 = int(po1.po_number.split("-")[-1])
        num2 = int(po2.po_number.split("-")[-1])
        self.assertEqual(num2, num1 + 1)

    def test_create_po_without_supplier(self):
        po_id = self.po_repo.create(notes="No supplier yet")
        po = self.po_repo.get_by_id(po_id)
        self.assertIsNotNone(po)
        self.assertIsNone(po.supplier_id)

    def test_get_all_returns_list(self):
        self.po_repo.create(supplier_id=self.supplier_id, notes="Order A")
        self.po_repo.create(supplier_id=self.supplier_id, notes="Order B")
        all_pos = self.po_repo.get_all()
        self.assertEqual(len(all_pos), 2)

    def test_get_all_filter_by_status(self):
        id1 = self.po_repo.create(supplier_id=self.supplier_id)
        id2 = self.po_repo.create(supplier_id=self.supplier_id)
        self.po_repo.set_status(id2, "SENT")
        drafts = self.po_repo.get_all(status="DRAFT")
        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0].id, id1)

    def test_get_by_id_nonexistent(self):
        result = self.po_repo.get_by_id(9999)
        self.assertIsNone(result)


class TestPOLineItems(TestPurchaseOrderBase):
    """Test PO line item management."""

    def setUp(self):
        super().setUp()
        self.po_id = self.po_repo.create(supplier_id=self.supplier_id)

    def test_add_line_returns_id(self):
        line_id = self.po_repo.add_line(self.po_id, self.item1_id, 20, 35.00)
        self.assertIsNotNone(line_id)
        self.assertGreater(line_id, 0)

    def test_get_lines_returns_correct_data(self):
        self.po_repo.add_line(self.po_id, self.item1_id, 20, 35.00)
        self.po_repo.add_line(self.po_id, self.item2_id, 10, 18.50)
        lines = self.po_repo.get_lines(self.po_id)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0].quantity, 20)
        self.assertEqual(lines[0].cost_price, 35.00)
        self.assertEqual(lines[1].quantity, 10)

    def test_update_line(self):
        line_id = self.po_repo.add_line(self.po_id, self.item1_id, 5, 10.00)
        self.po_repo.update_line(line_id, 15, 30.00)
        lines = self.po_repo.get_lines(self.po_id)
        self.assertEqual(lines[0].quantity, 15)
        self.assertEqual(lines[0].cost_price, 30.00)

    def test_remove_line(self):
        line_id = self.po_repo.add_line(self.po_id, self.item1_id, 5, 10.00)
        self.po_repo.remove_line(line_id)
        lines = self.po_repo.get_lines(self.po_id)
        self.assertEqual(len(lines), 0)

    def test_receive_line_updates_received_qty(self):
        line_id = self.po_repo.add_line(self.po_id, self.item1_id, 20, 35.00)
        self.po_repo.receive_line(line_id, 15)
        lines = self.po_repo.get_lines(self.po_id)
        self.assertEqual(lines[0].received_qty, 15)

    def test_po_total_value_calculated(self):
        self.po_repo.add_line(self.po_id, self.item1_id, 10, 50.00)
        self.po_repo.add_line(self.po_id, self.item2_id, 5, 20.00)
        po = self.po_repo.get_by_id(self.po_id)
        # 10*50 + 5*20 = 600
        self.assertEqual(po.total_value, 600.0)

    def test_po_line_count(self):
        self.po_repo.add_line(self.po_id, self.item1_id, 10, 50.00)
        self.po_repo.add_line(self.po_id, self.item2_id, 5, 20.00)
        po = self.po_repo.get_by_id(self.po_id)
        self.assertEqual(po.line_count, 2)


class TestPOSummary(TestPurchaseOrderBase):
    """Test PO summary/stats."""

    def test_summary_empty(self):
        summary = self.po_repo.get_summary()
        self.assertEqual(summary["total"], 0)

    def test_summary_counts_statuses(self):
        id1 = self.po_repo.create(supplier_id=self.supplier_id)
        id2 = self.po_repo.create(supplier_id=self.supplier_id)
        id3 = self.po_repo.create(supplier_id=self.supplier_id)
        self.po_repo.set_status(id2, "SENT")
        self.po_repo.set_status(id3, "RECEIVED")
        summary = self.po_repo.get_summary()
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["draft_count"], 1)
        self.assertEqual(summary["sent_count"], 1)
        self.assertEqual(summary["received_count"], 1)


class TestPODelete(TestPurchaseOrderBase):
    """Test PO deletion rules."""

    def test_delete_draft_succeeds(self):
        po_id = self.po_repo.create(supplier_id=self.supplier_id)
        result = self.po_repo.delete(po_id)
        self.assertTrue(result)
        self.assertIsNone(self.po_repo.get_by_id(po_id))

    def test_delete_sent_fails(self):
        po_id = self.po_repo.create(supplier_id=self.supplier_id)
        self.po_repo.set_status(po_id, "SENT")
        result = self.po_repo.delete(po_id)
        self.assertFalse(result)

    def test_delete_received_fails(self):
        po_id = self.po_repo.create(supplier_id=self.supplier_id)
        self.po_repo.set_status(po_id, "RECEIVED")
        result = self.po_repo.delete(po_id)
        self.assertFalse(result)

    def test_delete_cancelled_succeeds(self):
        po_id = self.po_repo.create(supplier_id=self.supplier_id)
        self.po_repo.set_status(po_id, "CANCELLED")
        result = self.po_repo.delete(po_id)
        self.assertTrue(result)

    def test_delete_nonexistent_fails(self):
        result = self.po_repo.delete(9999)
        self.assertFalse(result)


# ── Service Tests ────────────────────────────────────────────────────────────

class TestPOServiceCreate(TestPurchaseOrderBase):
    """Test PurchaseOrderService.create_order."""

    def test_create_order_returns_id(self):
        po_id = self.po_svc.create_order(supplier_id=self.supplier_id, notes="Test")
        self.assertIsNotNone(po_id)
        po = self.po_repo.get_by_id(po_id)
        self.assertEqual(po.status, "DRAFT")

    def test_add_item_to_order(self):
        po_id = self.po_svc.create_order(supplier_id=self.supplier_id)
        line_id = self.po_svc.add_item(po_id, self.item1_id, 20, 35.00)
        self.assertGreater(line_id, 0)

    def test_add_item_zero_qty_raises(self):
        po_id = self.po_svc.create_order(supplier_id=self.supplier_id)
        with self.assertRaises(ValueError):
            self.po_svc.add_item(po_id, self.item1_id, 0, 35.00)

    def test_add_item_negative_qty_raises(self):
        po_id = self.po_svc.create_order(supplier_id=self.supplier_id)
        with self.assertRaises(ValueError):
            self.po_svc.add_item(po_id, self.item1_id, -5, 35.00)


class TestPOServiceSend(TestPurchaseOrderBase):
    """Test PurchaseOrderService.send_order."""

    def test_send_draft_with_lines(self):
        po_id = self.po_svc.create_order(supplier_id=self.supplier_id)
        self.po_svc.add_item(po_id, self.item1_id, 10, 35.00)
        self.po_svc.send_order(po_id)
        po = self.po_repo.get_by_id(po_id)
        self.assertEqual(po.status, "SENT")

    def test_send_empty_po_raises(self):
        po_id = self.po_svc.create_order(supplier_id=self.supplier_id)
        with self.assertRaises(ValueError):
            self.po_svc.send_order(po_id)

    def test_send_already_sent_raises(self):
        po_id = self.po_svc.create_order(supplier_id=self.supplier_id)
        self.po_svc.add_item(po_id, self.item1_id, 10, 35.00)
        self.po_svc.send_order(po_id)
        with self.assertRaises(ValueError):
            self.po_svc.send_order(po_id)

    def test_send_nonexistent_po_raises(self):
        with self.assertRaises(ValueError):
            self.po_svc.send_order(9999)


class TestPOServiceReceive(TestPurchaseOrderBase):
    """Test PurchaseOrderService.receive_order — the core workflow."""

    def _create_and_send_po(self):
        """Helper: create a PO with 2 lines and send it."""
        po_id = self.po_svc.create_order(supplier_id=self.supplier_id)
        self.po_svc.add_item(po_id, self.item1_id, 20, 35.00)
        self.po_svc.add_item(po_id, self.item2_id, 10, 18.50)
        self.po_svc.send_order(po_id)
        return po_id

    def test_receive_full_order(self):
        """Receiving all lines fully → status RECEIVED, stock increased."""
        po_id = self._create_and_send_po()
        result = self.po_svc.receive_order(po_id)

        self.assertEqual(result["items"], 2)
        self.assertEqual(result["units"], 30)

        po = self.po_repo.get_by_id(po_id)
        self.assertEqual(po.status, "RECEIVED")

        # Verify stock increased
        item1 = self.item_repo.get_by_id(self.item1_id)
        item2 = self.item_repo.get_by_id(self.item2_id)
        self.assertEqual(item1.stock, 30)  # 10 + 20
        self.assertEqual(item2.stock, 15)  # 5 + 10

    def test_receive_partial_order(self):
        """Partial receive → status PARTIAL, stock updated for received lines only."""
        po_id = self._create_and_send_po()
        lines = self.po_repo.get_lines(po_id)
        line1_id = lines[0].id

        result = self.po_svc.receive_order(po_id, {line1_id: 12})

        self.assertEqual(result["items"], 1)
        self.assertEqual(result["units"], 12)

        po = self.po_repo.get_by_id(po_id)
        self.assertEqual(po.status, "PARTIAL")

        item1 = self.item_repo.get_by_id(self.item1_id)
        self.assertEqual(item1.stock, 22)  # 10 + 12

        item2 = self.item_repo.get_by_id(self.item2_id)
        self.assertEqual(item2.stock, 5)  # unchanged

    def test_receive_partial_then_full(self):
        """Two-step receive: partial first, then remaining → RECEIVED."""
        po_id = self._create_and_send_po()
        lines = self.po_repo.get_lines(po_id)

        # First: partial receive on line 1 only
        self.po_svc.receive_order(po_id, {lines[0].id: 10})
        po = self.po_repo.get_by_id(po_id)
        self.assertEqual(po.status, "PARTIAL")

        # Second: receive remaining
        self.po_svc.receive_order(po_id)
        po = self.po_repo.get_by_id(po_id)
        self.assertEqual(po.status, "RECEIVED")

        # Total stock: item1=10+20, item2=5+10
        item1 = self.item_repo.get_by_id(self.item1_id)
        item2 = self.item_repo.get_by_id(self.item2_id)
        self.assertEqual(item1.stock, 30)
        self.assertEqual(item2.stock, 15)

    def test_receive_draft_raises(self):
        """Cannot receive a DRAFT PO."""
        po_id = self.po_svc.create_order(supplier_id=self.supplier_id)
        self.po_svc.add_item(po_id, self.item1_id, 10, 35.00)
        with self.assertRaises(ValueError):
            self.po_svc.receive_order(po_id)

    def test_receive_nonexistent_raises(self):
        with self.assertRaises(ValueError):
            self.po_svc.receive_order(9999)

    def test_receive_creates_inventory_transactions(self):
        """Receiving should create IN transactions in the audit log."""
        po_id = self._create_and_send_po()
        self.po_svc.receive_order(po_id)

        conn = db_mod.get_connection()
        txns = conn.execute(
            "SELECT * FROM inventory_transactions WHERE operation='IN' AND note LIKE 'PO %'"
        ).fetchall()
        conn.close()

        self.assertEqual(len(txns), 2)


class TestPOServiceCancel(TestPurchaseOrderBase):
    """Test PurchaseOrderService.cancel_order."""

    def test_cancel_draft(self):
        po_id = self.po_svc.create_order(supplier_id=self.supplier_id)
        self.po_svc.cancel_order(po_id)
        po = self.po_repo.get_by_id(po_id)
        self.assertEqual(po.status, "CANCELLED")

    def test_cancel_sent(self):
        po_id = self.po_svc.create_order(supplier_id=self.supplier_id)
        self.po_svc.add_item(po_id, self.item1_id, 10, 35.00)
        self.po_svc.send_order(po_id)
        self.po_svc.cancel_order(po_id)
        po = self.po_repo.get_by_id(po_id)
        self.assertEqual(po.status, "CANCELLED")

    def test_cancel_received_raises(self):
        po_id = self.po_svc.create_order(supplier_id=self.supplier_id)
        self.po_svc.add_item(po_id, self.item1_id, 10, 35.00)
        self.po_svc.send_order(po_id)
        self.po_svc.receive_order(po_id)
        with self.assertRaises(ValueError):
            self.po_svc.cancel_order(po_id)

    def test_cancel_nonexistent_raises(self):
        with self.assertRaises(ValueError):
            self.po_svc.cancel_order(9999)


class TestPOServiceClose(TestPurchaseOrderBase):
    """Test PurchaseOrderService.close_order."""

    def test_close_received_po(self):
        po_id = self.po_svc.create_order(supplier_id=self.supplier_id)
        self.po_svc.add_item(po_id, self.item1_id, 10, 35.00)
        self.po_svc.send_order(po_id)
        self.po_svc.receive_order(po_id)
        self.po_svc.close_order(po_id)
        po = self.po_repo.get_by_id(po_id)
        self.assertEqual(po.status, "CLOSED")

    def test_close_nonexistent_raises(self):
        with self.assertRaises(ValueError):
            self.po_svc.close_order(9999)


if __name__ == "__main__":
    unittest.main()
