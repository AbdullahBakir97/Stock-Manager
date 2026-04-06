"""
tests/test_purchase_order_service.py — Tests for PurchaseOrderService.

Tests cover PO creation, item addition, sending, receiving, and cancellation.
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
from app.services.purchase_order_service import PurchaseOrderService


class TestPurchaseOrderServiceBase(unittest.TestCase):
    """Base test class with shared setup."""

    def setUp(self):
        """Create fresh services for each test with unique DB."""
        self.test_tmp_dir = tempfile.mkdtemp()
        self.test_db_file = os.path.join(self.test_tmp_dir, "test.db")
        self.original_db_path = db_mod.DB_PATH
        db_mod.DB_PATH = self.test_db_file
        db_mod.init_db()
        self.item_repo = ItemRepository()
        self.po_svc = PurchaseOrderService()

        # Create sample products
        self.sample_product1 = self.item_repo.add_product(
            brand="Apple",
            name="Screen Protector",
            color="Clear",
            stock=50,
            barcode="TEST-PO-1",
            min_stock=10,
            sell_price=9.99,
        )
        self.sample_product2 = self.item_repo.add_product(
            brand="Samsung",
            name="Battery",
            color="Black",
            stock=100,
            barcode="TEST-PO-2",
            min_stock=20,
            sell_price=29.99,
        )

    def tearDown(self):
        """Clean up test database."""
        db_mod.DB_PATH = self.original_db_path
        try:
            shutil.rmtree(self.test_tmp_dir)
        except:
            pass


class TestPurchaseOrderCreation(TestPurchaseOrderServiceBase):
    """Test purchase order creation."""

    def test_create_order_returns_po_id(self):
        """Test creating a PO returns valid ID."""
        po_id = self.po_svc.create_order()

        self.assertIsNotNone(po_id)
        self.assertGreater(po_id, 0)

    def test_create_order_with_notes(self):
        """Test creating a PO with notes."""
        po_id = self.po_svc.create_order(notes="Urgent restock needed")

        po = self.po_svc._po_repo.get_by_id(po_id)
        self.assertIsNotNone(po)
        self.assertEqual(po.notes, "Urgent restock needed")

    def test_create_order_starts_in_draft(self):
        """Test new PO starts in DRAFT status."""
        po_id = self.po_svc.create_order()

        po = self.po_svc._po_repo.get_by_id(po_id)
        self.assertEqual(po.status, "DRAFT")


class TestPurchaseOrderItemManagement(TestPurchaseOrderServiceBase):
    """Test adding items to purchase orders."""

    def test_add_item_with_valid_qty(self):
        """Test adding item with valid quantity."""
        po_id = self.po_svc.create_order()
        line_id = self.po_svc.add_item(po_id, self.sample_product1, quantity=10)

        self.assertIsNotNone(line_id)
        self.assertGreater(line_id, 0)

    def test_add_item_with_cost_price(self):
        """Test adding item with cost price."""
        po_id = self.po_svc.create_order()
        line_id = self.po_svc.add_item(
            po_id, self.sample_product1,
            quantity=5, cost_price=5.50
        )

        self.assertGreater(line_id, 0)

    def test_add_item_with_zero_qty_raises_error(self):
        """Test adding item with zero quantity raises ValueError."""
        po_id = self.po_svc.create_order()

        with self.assertRaises(ValueError):
            self.po_svc.add_item(po_id, self.sample_product1, quantity=0)

    def test_add_item_with_negative_qty_raises_error(self):
        """Test adding item with negative quantity raises ValueError."""
        po_id = self.po_svc.create_order()

        with self.assertRaises(ValueError):
            self.po_svc.add_item(po_id, self.sample_product1, quantity=-5)

    def test_add_multiple_items(self):
        """Test adding multiple items to same PO."""
        po_id = self.po_svc.create_order()
        line1 = self.po_svc.add_item(po_id, self.sample_product1, quantity=10)
        line2 = self.po_svc.add_item(po_id, self.sample_product2, quantity=20)

        self.assertNotEqual(line1, line2)

        po = self.po_svc._po_repo.get_by_id(po_id)
        self.assertEqual(po.line_count, 2)


class TestPurchaseOrderSending(TestPurchaseOrderServiceBase):
    """Test sending purchase orders."""

    def test_send_order_on_draft_with_lines(self):
        """Test sending a draft PO with items."""
        po_id = self.po_svc.create_order()
        self.po_svc.add_item(po_id, self.sample_product1, quantity=10)

        self.po_svc.send_order(po_id)

        po = self.po_svc._po_repo.get_by_id(po_id)
        self.assertEqual(po.status, "SENT")

    def test_send_empty_order_raises_error(self):
        """Test sending an empty PO raises ValueError."""
        po_id = self.po_svc.create_order()

        with self.assertRaises(ValueError):
            self.po_svc.send_order(po_id)

    def test_send_non_draft_order_raises_error(self):
        """Test sending a non-draft PO raises ValueError."""
        po_id = self.po_svc.create_order()
        self.po_svc.add_item(po_id, self.sample_product1, quantity=5)
        self.po_svc.send_order(po_id)

        # Try to send again
        with self.assertRaises(ValueError):
            self.po_svc.send_order(po_id)


class TestPurchaseOrderReceiving(TestPurchaseOrderServiceBase):
    """Test receiving purchase orders."""

    def test_receive_order_stocks_in_items(self):
        """Test receiving order stocks in items."""
        po_id = self.po_svc.create_order()
        self.po_svc.add_item(po_id, self.sample_product1, quantity=10)
        self.po_svc.send_order(po_id)

        # Get stock before
        item_before = self.item_repo.get_by_id(self.sample_product1)
        stock_before = item_before.stock

        # Receive
        result = self.po_svc.receive_order(po_id)

        # Check stock increased
        item_after = self.item_repo.get_by_id(self.sample_product1)
        self.assertEqual(item_after.stock, stock_before + 10)

        self.assertEqual(result["items"], 1)
        self.assertEqual(result["units"], 10)

    def test_receive_order_partial(self):
        """Test partial receipt of PO."""
        po_id = self.po_svc.create_order()
        self.po_svc.add_item(po_id, self.sample_product1, quantity=10)
        self.po_svc.send_order(po_id)

        # Get lines
        lines = self.po_svc._po_repo.get_lines(po_id)
        if lines:
            # Receive only 5 of 10
            result = self.po_svc.receive_order(po_id, {lines[0].id: 5})

            po = self.po_svc._po_repo.get_by_id(po_id)
            self.assertEqual(po.status, "PARTIAL")

    def test_receive_order_full(self):
        """Test full receipt of PO."""
        po_id = self.po_svc.create_order()
        self.po_svc.add_item(po_id, self.sample_product1, quantity=10)
        self.po_svc.send_order(po_id)

        self.po_svc.receive_order(po_id)

        po = self.po_svc._po_repo.get_by_id(po_id)
        self.assertEqual(po.status, "RECEIVED")


class TestPurchaseOrderCancellation(TestPurchaseOrderServiceBase):
    """Test cancelling purchase orders."""

    def test_cancel_order_on_draft(self):
        """Test cancelling a draft PO."""
        po_id = self.po_svc.create_order()

        self.po_svc.cancel_order(po_id)

        po = self.po_svc._po_repo.get_by_id(po_id)
        self.assertEqual(po.status, "CANCELLED")

    def test_cancel_order_on_sent(self):
        """Test cancelling a sent PO."""
        po_id = self.po_svc.create_order()
        self.po_svc.add_item(po_id, self.sample_product1, quantity=5)
        self.po_svc.send_order(po_id)

        self.po_svc.cancel_order(po_id)

        po = self.po_svc._po_repo.get_by_id(po_id)
        self.assertEqual(po.status, "CANCELLED")

    def test_cancel_order_on_received_raises_error(self):
        """Test cancelling a received PO raises ValueError."""
        po_id = self.po_svc.create_order()
        self.po_svc.add_item(po_id, self.sample_product1, quantity=5)
        self.po_svc.send_order(po_id)
        self.po_svc.receive_order(po_id)

        with self.assertRaises(ValueError):
            self.po_svc.cancel_order(po_id)

    def test_cancel_order_on_partial_raises_error(self):
        """Test cancelling a partial PO raises ValueError."""
        po_id = self.po_svc.create_order()
        self.po_svc.add_item(po_id, self.sample_product1, quantity=10)
        self.po_svc.send_order(po_id)

        lines = self.po_svc._po_repo.get_lines(po_id)
        if lines:
            self.po_svc.receive_order(po_id, {lines[0].id: 5})

            with self.assertRaises(ValueError):
                self.po_svc.cancel_order(po_id)


if __name__ == "__main__":
    unittest.main()
