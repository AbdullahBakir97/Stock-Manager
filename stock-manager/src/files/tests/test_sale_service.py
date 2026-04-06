"""
tests/test_sale_service.py — Tests for SaleService.

Tests cover sale creation, stock deduction, retrieval, and deletion.
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
from app.services.sale_service import SaleService


class TestSaleServiceBase(unittest.TestCase):
    """Base test class with shared setup."""

    def setUp(self):
        """Create fresh services for each test with unique DB."""
        self.test_tmp_dir = tempfile.mkdtemp()
        self.test_db_file = os.path.join(self.test_tmp_dir, "test.db")
        self.original_db_path = db_mod.DB_PATH
        db_mod.DB_PATH = self.test_db_file
        db_mod.init_db()
        self.item_repo = ItemRepository()
        self.sale_svc = SaleService()

        # Create sample products with sufficient stock
        self.sample_product1 = self.item_repo.add_product(
            brand="Apple",
            name="Screen Protector",
            color="Clear",
            stock=100,
            barcode="TEST-SALE-1",
            min_stock=10,
            sell_price=9.99,
        )
        self.sample_product2 = self.item_repo.add_product(
            brand="Samsung",
            name="Battery",
            color="Black",
            stock=50,
            barcode="TEST-SALE-2",
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


class TestSaleCreation(TestSaleServiceBase):
    """Test sale creation and stock deduction."""

    def test_create_sale_with_valid_items_deducts_stock(self):
        """Test creating a sale deducts stock correctly."""
        items = [
            {"item_id": self.sample_product1, "quantity": 10, "unit_price": 9.99}
        ]

        item_before = self.item_repo.get_by_id(self.sample_product1)
        stock_before = item_before.stock

        sale_id = self.sale_svc.create_sale(
            customer_name="John Doe",
            items=items
        )

        self.assertIsNotNone(sale_id)
        self.assertGreater(sale_id, 0)

        item_after = self.item_repo.get_by_id(self.sample_product1)
        self.assertEqual(item_after.stock, stock_before - 10)

    def test_create_sale_with_multiple_items(self):
        """Test creating a sale with multiple items."""
        items = [
            {"item_id": self.sample_product1, "quantity": 5, "unit_price": 9.99},
            {"item_id": self.sample_product2, "quantity": 2, "unit_price": 29.99}
        ]

        sale_id = self.sale_svc.create_sale(
            customer_name="Jane Smith",
            items=items
        )

        self.assertGreater(sale_id, 0)

        item1_after = self.item_repo.get_by_id(self.sample_product1)
        item2_after = self.item_repo.get_by_id(self.sample_product2)

        self.assertEqual(item1_after.stock, 95)
        self.assertEqual(item2_after.stock, 48)

    def test_create_sale_with_no_items_raises_error(self):
        """Test creating a sale without items raises ValueError."""
        with self.assertRaises(ValueError):
            self.sale_svc.create_sale(customer_name="John")

        with self.assertRaises(ValueError):
            self.sale_svc.create_sale(customer_name="John", items=[])

    def test_create_sale_with_insufficient_stock_raises_error(self):
        """Test creating a sale with insufficient stock raises ValueError."""
        items = [
            {"item_id": self.sample_product1, "quantity": 200, "unit_price": 9.99}
        ]

        with self.assertRaises(ValueError):
            self.sale_svc.create_sale(customer_name="John", items=items)

    def test_create_sale_with_nonexistent_item_raises_error(self):
        """Test creating a sale with non-existent item raises ValueError."""
        items = [
            {"item_id": 9999, "quantity": 5, "unit_price": 9.99}
        ]

        with self.assertRaises(ValueError):
            self.sale_svc.create_sale(customer_name="John", items=items)

    def test_create_sale_with_zero_quantity_raises_error(self):
        """Test creating a sale with zero quantity raises ValueError."""
        items = [
            {"item_id": self.sample_product1, "quantity": 0, "unit_price": 9.99}
        ]

        with self.assertRaises(ValueError):
            self.sale_svc.create_sale(customer_name="John", items=items)

    def test_create_sale_with_discount(self):
        """Test creating a sale with discount."""
        items = [
            {"item_id": self.sample_product1, "quantity": 5, "unit_price": 9.99}
        ]

        sale_id = self.sale_svc.create_sale(
            customer_name="John",
            discount=10.0,
            items=items
        )

        self.assertGreater(sale_id, 0)

    def test_create_sale_with_note(self):
        """Test creating a sale with note."""
        items = [
            {"item_id": self.sample_product1, "quantity": 3, "unit_price": 9.99}
        ]

        sale_id = self.sale_svc.create_sale(
            customer_name="John",
            note="Cash payment",
            items=items
        )

        sale = self.sale_svc.get_sale(sale_id)
        self.assertEqual(sale.note, "Cash payment")


class TestSaleRetrieval(TestSaleServiceBase):
    """Test retrieving sales."""

    def test_get_sale_by_id(self):
        """Test retrieving a sale by ID."""
        items = [
            {"item_id": self.sample_product1, "quantity": 5, "unit_price": 9.99}
        ]

        sale_id = self.sale_svc.create_sale(
            customer_name="John",
            items=items
        )

        sale = self.sale_svc.get_sale(sale_id)
        self.assertIsNotNone(sale)
        self.assertEqual(sale.id, sale_id)

    def test_get_sale_returns_items(self):
        """Test retrieved sale includes items."""
        items = [
            {"item_id": self.sample_product1, "quantity": 5, "unit_price": 9.99},
            {"item_id": self.sample_product2, "quantity": 2, "unit_price": 29.99}
        ]

        sale_id = self.sale_svc.create_sale(
            customer_name="John",
            items=items
        )

        sale = self.sale_svc.get_sale(sale_id)
        self.assertIsNotNone(sale.items)
        self.assertEqual(len(sale.items), 2)

    def test_get_sales_returns_list(self):
        """Test get_sales returns list of sales."""
        items = [
            {"item_id": self.sample_product1, "quantity": 3, "unit_price": 9.99}
        ]

        sale_id1 = self.sale_svc.create_sale(customer_name="John", items=items)
        sale_id2 = self.sale_svc.create_sale(customer_name="Jane", items=items)

        sales = self.sale_svc.get_sales()
        self.assertIsInstance(sales, list)
        self.assertGreaterEqual(len(sales), 2)

    def test_get_sales_with_limit(self):
        """Test get_sales respects limit."""
        items = [
            {"item_id": self.sample_product1, "quantity": 1, "unit_price": 9.99}
        ]

        for i in range(5):
            self.sale_svc.create_sale(
                customer_name=f"Customer {i}",
                items=items
            )

        sales = self.sale_svc.get_sales(limit=2)
        self.assertLessEqual(len(sales), 2)


class TestSaleDeletion(TestSaleServiceBase):
    """Test deleting sales."""

    def test_delete_sale(self):
        """Test deleting a sale."""
        items = [
            {"item_id": self.sample_product1, "quantity": 5, "unit_price": 9.99}
        ]

        sale_id = self.sale_svc.create_sale(
            customer_name="John",
            items=items
        )

        result = self.sale_svc.delete_sale(sale_id)
        self.assertTrue(result)

    def test_delete_nonexistent_sale(self):
        """Test deleting non-existent sale does not raise error."""
        # Implementation returns True even for non-existent IDs (SQL DELETE is idempotent)
        result = self.sale_svc.delete_sale(9999)
        self.assertIsNotNone(result)

    def test_get_deleted_sale_returns_none(self):
        """Test getting deleted sale returns None."""
        items = [
            {"item_id": self.sample_product1, "quantity": 5, "unit_price": 9.99}
        ]

        sale_id = self.sale_svc.create_sale(
            customer_name="John",
            items=items
        )

        self.sale_svc.delete_sale(sale_id)
        sale = self.sale_svc.get_sale(sale_id)
        # Should be None or raise error
        if sale is not None:
            self.assertIsNone(sale)


class TestSaleIntegration(TestSaleServiceBase):
    """Integration tests for sales."""

    def test_multiple_sales_sequential(self):
        """Test creating multiple sales in sequence."""
        for i in range(3):
            items = [
                {"item_id": self.sample_product1, "quantity": 5, "unit_price": 9.99}
            ]
            sale_id = self.sale_svc.create_sale(
                customer_name=f"Customer {i}",
                items=items
            )
            self.assertGreater(sale_id, 0)

        item = self.item_repo.get_by_id(self.sample_product1)
        self.assertEqual(item.stock, 85)

    def test_sale_with_customer_id(self):
        """Test creating a sale with customer ID."""
        # Create a customer first so FK constraint is satisfied
        from app.repositories.customer_repo import CustomerRepository
        cust_repo = CustomerRepository()
        cust_id = cust_repo.add("Test Customer", phone="555-1234")

        items = [
            {"item_id": self.sample_product1, "quantity": 2, "unit_price": 9.99}
        ]

        sale_id = self.sale_svc.create_sale(
            customer_name="Test Customer",
            customer_id=cust_id,
            items=items
        )

        sale = self.sale_svc.get_sale(sale_id)
        self.assertEqual(sale.customer_id, cust_id)


if __name__ == "__main__":
    unittest.main()
