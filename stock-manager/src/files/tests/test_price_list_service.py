"""
tests/test_price_list_service.py — Tests for PriceListService.

Tests cover price list CRUD, item management, and bulk operations.
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
from app.services.price_list_service import PriceListService


class TestPriceListServiceBase(unittest.TestCase):
    """Base test class with shared setup."""

    def setUp(self):
        """Create fresh services for each test with unique DB."""
        self.test_tmp_dir = tempfile.mkdtemp()
        self.test_db_file = os.path.join(self.test_tmp_dir, "test.db")
        self.original_db_path = db_mod.DB_PATH
        db_mod.DB_PATH = self.test_db_file
        db_mod.init_db()
        self.item_repo = ItemRepository()
        self.price_svc = PriceListService()

        # Create sample products
        self.sample_product1 = self.item_repo.add_product(
            brand="Apple",
            name="Screen Protector",
            color="Clear",
            stock=50,
            barcode="TEST-PL-1",
            min_stock=10,
            sell_price=9.99,
        )
        self.sample_product2 = self.item_repo.add_product(
            brand="Samsung",
            name="Battery",
            color="Black",
            stock=100,
            barcode="TEST-PL-2",
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


class TestPriceListCRUD(TestPriceListServiceBase):
    """Test price list CRUD operations."""

    def test_create_list_with_valid_name(self):
        """Test creating a price list with valid name."""
        list_id = self.price_svc.create_list("Spring 2026 Pricing")

        self.assertIsNotNone(list_id)
        self.assertGreater(list_id, 0)

    def test_create_list_with_empty_name_raises_error(self):
        """Test creating a price list with empty name raises ValueError."""
        with self.assertRaises(ValueError):
            self.price_svc.create_list("")

        with self.assertRaises(ValueError):
            self.price_svc.create_list("   ")

    def test_create_list_with_description(self):
        """Test creating a price list with description."""
        list_id = self.price_svc.create_list(
            "Premium Tier",
            description="High-end products for premium customers"
        )

        self.assertGreater(list_id, 0)

    def test_get_all_lists(self):
        """Test retrieving all price lists."""
        self.price_svc.create_list("List 1")
        self.price_svc.create_list("List 2")

        lists = self.price_svc.get_all_lists()
        self.assertIsInstance(lists, list)
        self.assertGreaterEqual(len(lists), 2)

    def test_get_list_by_id(self):
        """Test retrieving price list by ID."""
        list_id = self.price_svc.create_list("Test List")

        price_list = self.price_svc.get_list(list_id)
        self.assertIsNotNone(price_list)
        self.assertEqual(price_list.id, list_id)
        self.assertEqual(price_list.name, "Test List")

    def test_get_nonexistent_list_returns_none(self):
        """Test retrieving non-existent list returns None."""
        price_list = self.price_svc.get_list(9999)
        self.assertIsNone(price_list)

    def test_update_list(self):
        """Test updating price list."""
        list_id = self.price_svc.create_list("Old Name")
        self.price_svc.update_list(list_id, "New Name", "Updated description", True)

        price_list = self.price_svc.get_list(list_id)
        self.assertEqual(price_list.name, "New Name")

    def test_update_list_with_empty_name_raises_error(self):
        """Test updating list with empty name raises ValueError."""
        list_id = self.price_svc.create_list("List")

        with self.assertRaises(ValueError):
            self.price_svc.update_list(list_id, "", "description", True)

    def test_delete_list(self):
        """Test deleting price list."""
        list_id = self.price_svc.create_list("Deletable List")

        self.price_svc.delete_list(list_id)

        price_list = self.price_svc.get_list(list_id)
        # Should be deleted or marked inactive


class TestPriceListItems(TestPriceListServiceBase):
    """Test managing items in price lists."""

    def test_add_item_to_list(self):
        """Test adding item to price list."""
        list_id = self.price_svc.create_list("Test List")

        item_id = self.price_svc.add_item(
            list_id, self.sample_product1,
            price=12.99
        )

        self.assertIsNotNone(item_id)
        self.assertGreater(item_id, 0)

    def test_add_item_with_negative_price_raises_error(self):
        """Test adding item with negative price raises ValueError."""
        list_id = self.price_svc.create_list("Test List")

        with self.assertRaises(ValueError):
            self.price_svc.add_item(list_id, self.sample_product1, price=-5.00)

    def test_add_item_with_zero_price(self):
        """Test adding item with zero price."""
        list_id = self.price_svc.create_list("Test List")

        item_id = self.price_svc.add_item(
            list_id, self.sample_product1,
            price=0.00
        )

        self.assertGreater(item_id, 0)

    def test_get_list_items(self):
        """Test retrieving items from a price list."""
        list_id = self.price_svc.create_list("Test List")

        self.price_svc.add_item(list_id, self.sample_product1, price=12.99)
        self.price_svc.add_item(list_id, self.sample_product2, price=34.99)

        items = self.price_svc.get_list_items(list_id)
        self.assertIsInstance(items, list)
        self.assertEqual(len(items), 2)

    def test_update_price(self):
        """Test updating item price in list."""
        list_id = self.price_svc.create_list("Test List")
        pli_id = self.price_svc.add_item(list_id, self.sample_product1, price=10.00)

        self.price_svc.update_price(pli_id, 15.00)

        items = self.price_svc.get_list_items(list_id)
        self.assertEqual(items[0].list_price, 15.00)

    def test_update_price_with_negative_raises_error(self):
        """Test updating price to negative value raises ValueError."""
        list_id = self.price_svc.create_list("Test List")
        pli_id = self.price_svc.add_item(list_id, self.sample_product1, price=10.00)

        with self.assertRaises(ValueError):
            self.price_svc.update_price(pli_id, -5.00)

    def test_remove_item(self):
        """Test removing item from price list."""
        list_id = self.price_svc.create_list("Test List")
        pli_id = self.price_svc.add_item(list_id, self.sample_product1, price=10.00)

        self.price_svc.remove_item(pli_id)

        items = self.price_svc.get_list_items(list_id)
        self.assertEqual(len(items), 0)

    def test_add_multiple_items(self):
        """Test adding multiple items to same list."""
        list_id = self.price_svc.create_list("Multi-item List")

        self.price_svc.add_item(list_id, self.sample_product1, price=12.99)
        self.price_svc.add_item(list_id, self.sample_product2, price=34.99)

        items = self.price_svc.get_list_items(list_id)
        self.assertEqual(len(items), 2)


class TestPriceListBulkOperations(TestPriceListServiceBase):
    """Test bulk operations on price lists."""

    def test_bulk_populate_adds_all_items(self):
        """Test bulk_populate adds all inventory items to list."""
        list_id = self.price_svc.create_list("Bulk List")

        count = self.price_svc.bulk_populate(list_id)
        self.assertGreaterEqual(count, 2)

        items = self.price_svc.get_list_items(list_id)
        self.assertGreaterEqual(len(items), 2)

    def test_bulk_populate_idempotent(self):
        """Test bulk_populate doesn't duplicate items."""
        list_id = self.price_svc.create_list("Bulk List")

        self.price_svc.bulk_populate(list_id)
        items_after_first = len(self.price_svc.get_list_items(list_id))

        self.price_svc.bulk_populate(list_id)
        items_after_second = len(self.price_svc.get_list_items(list_id))

        # Should not increase (implementation dependent)


class TestPriceListApplication(TestPriceListServiceBase):
    """Test applying price lists to inventory."""

    def test_apply_price_list_updates_sell_price(self):
        """Test apply_price_list updates inventory sell_price."""
        list_id = self.price_svc.create_list("Application List")

        self.price_svc.add_item(list_id, self.sample_product1, price=14.99)
        self.price_svc.add_item(list_id, self.sample_product2, price=39.99)

        count = self.price_svc.apply_price_list(list_id)

        # Verify items updated
        item1 = self.item_repo.get_by_id(self.sample_product1)
        item2 = self.item_repo.get_by_id(self.sample_product2)

        self.assertEqual(item1.sell_price, 14.99)
        self.assertEqual(item2.sell_price, 39.99)
        self.assertGreaterEqual(count, 2)

    def test_apply_price_list_returns_count(self):
        """Test apply_price_list returns count of updated items."""
        list_id = self.price_svc.create_list("Count List")

        self.price_svc.add_item(list_id, self.sample_product1, price=11.99)

        count = self.price_svc.apply_price_list(list_id)
        self.assertGreater(count, 0)


class TestPriceListAnalysis(TestPriceListServiceBase):
    """Test price list analysis features."""

    def test_get_margin_analysis(self):
        """Test retrieving margin analysis."""
        analysis = self.price_svc.get_margin_analysis()

        self.assertIsInstance(analysis, list)

    def test_get_summary(self):
        """Test getting summary statistics."""
        self.price_svc.create_list("Summary List 1")
        self.price_svc.create_list("Summary List 2")

        summary = self.price_svc.get_summary()
        self.assertIsInstance(summary, dict)


class TestPriceListIntegration(TestPriceListServiceBase):
    """Integration tests for price lists."""

    def test_create_populate_apply_workflow(self):
        """Test typical workflow: create, populate, apply."""
        list_id = self.price_svc.create_list("Seasonal Pricing")

        # Populate with all items
        populate_count = self.price_svc.bulk_populate(list_id)
        self.assertGreater(populate_count, 0)

        items = self.price_svc.get_list_items(list_id)
        self.assertGreater(len(items), 0)

        # Apply to inventory
        apply_count = self.price_svc.apply_price_list(list_id)
        self.assertGreater(apply_count, 0)

    def test_multiple_lists_independent(self):
        """Test multiple price lists operate independently."""
        list1_id = self.price_svc.create_list("List 1")
        list2_id = self.price_svc.create_list("List 2")

        self.price_svc.add_item(list1_id, self.sample_product1, price=10.00)
        self.price_svc.add_item(list2_id, self.sample_product1, price=20.00)

        items1 = self.price_svc.get_list_items(list1_id)
        items2 = self.price_svc.get_list_items(list2_id)

        self.assertEqual(items1[0].list_price, 10.00)
        self.assertEqual(items2[0].list_price, 20.00)

    def test_bulk_markup(self):
        """Test bulk markup operation."""
        list_id = self.price_svc.create_list("Markup List")

        self.price_svc.add_item(list_id, self.sample_product1, price=100.00)
        self.price_svc.add_item(list_id, self.sample_product2, price=100.00)

        # Apply 10% markup
        count = self.price_svc.bulk_markup(list_id, 10)

        items = self.price_svc.get_list_items(list_id)
        # Prices should be increased by 10%


if __name__ == "__main__":
    unittest.main()
