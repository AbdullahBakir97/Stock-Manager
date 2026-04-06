"""
tests/test_price_list_repo.py — Tests for PriceListRepository.

Tests cover create, get_by_id, get_all, update, delete, add_item, get_items,
update_item_price, remove_item, bulk_add_all_items, and get_summary.
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
from app.repositories.price_list_repo import PriceListRepository
from app.repositories.item_repo import ItemRepository


class TestPriceListRepositoryBase(unittest.TestCase):
    """Base test class with shared setup."""

    def setUp(self):
        """Create fresh PriceListRepository with unique DB."""
        self.test_tmp_dir = tempfile.mkdtemp()
        self.test_db_file = os.path.join(self.test_tmp_dir, "test.db")
        self.original_db_path = db_mod.DB_PATH
        db_mod.DB_PATH = self.test_db_file
        db_mod.init_db()
        self.price_list_repo = PriceListRepository()
        self.item_repo = ItemRepository()

        # Create sample products for testing
        self.sample_product_1 = self.item_repo.add_product(
            brand="Apple",
            name="Screen Protector",
            color="Clear",
            stock=50,
            barcode="TEST-PRICE-1",
            min_stock=10,
            sell_price=9.99,
        )
        self.sample_product_2 = self.item_repo.add_product(
            brand="Samsung",
            name="Phone Case",
            color="Black",
            stock=30,
            barcode="TEST-PRICE-2",
            min_stock=5,
            sell_price=14.99,
        )
        self.sample_product_3 = self.item_repo.add_product(
            brand="Generic",
            name="USB Cable",
            color="White",
            stock=100,
            barcode="TEST-PRICE-3",
            min_stock=20,
            sell_price=4.99,
        )

    def tearDown(self):
        """Clean up test database."""
        db_mod.DB_PATH = self.original_db_path
        try:
            shutil.rmtree(self.test_tmp_dir)
        except:
            pass


class TestPriceListCreate(TestPriceListRepositoryBase):
    """Test price list creation."""

    def test_create_returns_price_list_id(self):
        """Test create() returns a valid price list ID."""
        list_id = self.price_list_repo.create("Retail Prices", "Standard retail pricing")

        self.assertIsInstance(list_id, int)
        self.assertGreater(list_id, 0)

    def test_create_stores_name(self):
        """Test create() stores the price list name."""
        name = "Wholesale Prices"
        list_id = self.price_list_repo.create(name)
        price_list = self.price_list_repo.get_by_id(list_id)

        self.assertEqual(price_list.name, name)

    def test_create_stores_description(self):
        """Test create() stores the description."""
        description = "Winter season pricing"
        list_id = self.price_list_repo.create("Winter Prices", description)
        price_list = self.price_list_repo.get_by_id(list_id)

        self.assertEqual(price_list.description, description)

    def test_create_initializes_as_active(self):
        """Test create() initializes is_active as True."""
        list_id = self.price_list_repo.create("Test Price List")
        price_list = self.price_list_repo.get_by_id(list_id)

        self.assertTrue(price_list.is_active)

    def test_create_sets_created_at_timestamp(self):
        """Test create() sets created_at timestamp."""
        list_id = self.price_list_repo.create("Test Price List")
        price_list = self.price_list_repo.get_by_id(list_id)

        self.assertIsNotNone(price_list.created_at)
        self.assertGreater(len(price_list.created_at), 0)


class TestPriceListGetById(TestPriceListRepositoryBase):
    """Test price list retrieval by ID."""

    def test_get_by_id_returns_price_list(self):
        """Test get_by_id() returns correct price list."""
        list_id = self.price_list_repo.create("Test List")
        price_list = self.price_list_repo.get_by_id(list_id)

        self.assertIsNotNone(price_list)
        self.assertEqual(price_list.id, list_id)
        self.assertEqual(price_list.name, "Test List")

    def test_get_by_id_returns_none_for_nonexistent(self):
        """Test get_by_id() returns None for non-existent price list."""
        price_list = self.price_list_repo.get_by_id(9999)

        self.assertIsNone(price_list)

    def test_get_by_id_returns_item_count(self):
        """Test get_by_id() includes computed item_count."""
        list_id = self.price_list_repo.create("Test List")
        self.price_list_repo.add_item(list_id, self.sample_product_1, 19.99)
        self.price_list_repo.add_item(list_id, self.sample_product_2, 24.99)

        price_list = self.price_list_repo.get_by_id(list_id)

        self.assertEqual(price_list.item_count, 2)


class TestPriceListGetAll(TestPriceListRepositoryBase):
    """Test get_all() method."""

    def test_get_all_returns_list(self):
        """Test get_all() returns a list."""
        result = self.price_list_repo.get_all()

        self.assertIsInstance(result, list)

    def test_get_all_returns_empty_on_no_lists(self):
        """Test get_all() returns empty list when no price lists exist."""
        result = self.price_list_repo.get_all()

        self.assertEqual(len(result), 0)

    def test_get_all_returns_all_lists(self):
        """Test get_all() returns all price lists."""
        self.price_list_repo.create("List 1")
        self.price_list_repo.create("List 2")
        self.price_list_repo.create("List 3")

        result = self.price_list_repo.get_all()

        self.assertEqual(len(result), 3)

    def test_get_all_includes_item_count(self):
        """Test get_all() includes item_count for each list."""
        list_id = self.price_list_repo.create("Test List")
        self.price_list_repo.add_item(list_id, self.sample_product_1, 19.99)

        result = self.price_list_repo.get_all()

        self.assertGreater(len(result), 0)
        self.assertEqual(result[0].item_count, 1)


class TestPriceListUpdate(TestPriceListRepositoryBase):
    """Test update() method."""

    def test_update_changes_name(self):
        """Test update() changes the price list name."""
        list_id = self.price_list_repo.create("Original Name")
        self.price_list_repo.update(list_id, "Updated Name", "Description", True)
        price_list = self.price_list_repo.get_by_id(list_id)

        self.assertEqual(price_list.name, "Updated Name")

    def test_update_changes_description(self):
        """Test update() changes the description."""
        list_id = self.price_list_repo.create("Test List", "Old description")
        new_desc = "New description"
        self.price_list_repo.update(list_id, "Test List", new_desc, True)
        price_list = self.price_list_repo.get_by_id(list_id)

        self.assertEqual(price_list.description, new_desc)

    def test_update_changes_is_active_true(self):
        """Test update() changes is_active to True."""
        list_id = self.price_list_repo.create("Test List")
        self.price_list_repo.update(list_id, "Test List", "", False)
        self.price_list_repo.update(list_id, "Test List", "", True)
        price_list = self.price_list_repo.get_by_id(list_id)

        self.assertTrue(price_list.is_active)

    def test_update_changes_is_active_false(self):
        """Test update() changes is_active to False."""
        list_id = self.price_list_repo.create("Test List")
        self.price_list_repo.update(list_id, "Test List", "", False)
        price_list = self.price_list_repo.get_by_id(list_id)

        self.assertFalse(price_list.is_active)


class TestPriceListDelete(TestPriceListRepositoryBase):
    """Test delete() method."""

    def test_delete_removes_price_list(self):
        """Test delete() removes a price list."""
        list_id = self.price_list_repo.create("Test List")
        self.price_list_repo.delete(list_id)
        price_list = self.price_list_repo.get_by_id(list_id)

        self.assertIsNone(price_list)

    def test_delete_removes_price_list_items(self):
        """Test delete() also removes associated price list items."""
        list_id = self.price_list_repo.create("Test List")
        self.price_list_repo.add_item(list_id, self.sample_product_1, 19.99)
        self.price_list_repo.add_item(list_id, self.sample_product_2, 24.99)

        self.price_list_repo.delete(list_id)
        items = self.price_list_repo.get_items(list_id)

        self.assertEqual(len(items), 0)

    def test_delete_only_removes_specific_list(self):
        """Test delete() only removes the specified price list."""
        list_id_1 = self.price_list_repo.create("List 1")
        list_id_2 = self.price_list_repo.create("List 2")

        self.price_list_repo.delete(list_id_1)

        price_list = self.price_list_repo.get_by_id(list_id_2)
        self.assertIsNotNone(price_list)


class TestPriceListAddItem(TestPriceListRepositoryBase):
    """Test add_item() method."""

    def test_add_item_returns_item_id(self):
        """Test add_item() returns a valid price list item ID."""
        list_id = self.price_list_repo.create("Test List")
        item_id = self.price_list_repo.add_item(list_id, self.sample_product_1, 19.99)

        self.assertIsInstance(item_id, int)
        self.assertGreater(item_id, 0)

    def test_add_item_stores_price(self):
        """Test add_item() stores the price correctly."""
        list_id = self.price_list_repo.create("Test List")
        price = 24.99
        self.price_list_repo.add_item(list_id, self.sample_product_1, price)
        items = self.price_list_repo.get_items(list_id)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].list_price, price)


class TestPriceListGetItems(TestPriceListRepositoryBase):
    """Test get_items() method."""

    def test_get_items_returns_list(self):
        """Test get_items() returns a list."""
        list_id = self.price_list_repo.create("Test List")
        items = self.price_list_repo.get_items(list_id)

        self.assertIsInstance(items, list)

    def test_get_items_returns_empty_for_new_list(self):
        """Test get_items() returns empty list for new list with no items."""
        list_id = self.price_list_repo.create("Test List")
        items = self.price_list_repo.get_items(list_id)

        self.assertEqual(len(items), 0)

    def test_get_items_returns_all_items(self):
        """Test get_items() returns all items in list."""
        list_id = self.price_list_repo.create("Test List")
        self.price_list_repo.add_item(list_id, self.sample_product_1, 19.99)
        self.price_list_repo.add_item(list_id, self.sample_product_2, 24.99)
        self.price_list_repo.add_item(list_id, self.sample_product_3, 7.99)

        items = self.price_list_repo.get_items(list_id)

        self.assertEqual(len(items), 3)

    def test_get_items_includes_item_details(self):
        """Test get_items() includes item details like barcode and stock."""
        list_id = self.price_list_repo.create("Test List")
        self.price_list_repo.add_item(list_id, self.sample_product_1, 19.99)
        items = self.price_list_repo.get_items(list_id)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].barcode, "TEST-PRICE-1")
        self.assertEqual(items[0].stock, 50)


class TestPriceListUpdateItemPrice(TestPriceListRepositoryBase):
    """Test update_item_price() method."""

    def test_update_item_price_changes_price(self):
        """Test update_item_price() changes the item price."""
        list_id = self.price_list_repo.create("Test List")
        pli_id = self.price_list_repo.add_item(list_id, self.sample_product_1, 19.99)

        new_price = 29.99
        self.price_list_repo.update_item_price(pli_id, new_price)
        items = self.price_list_repo.get_items(list_id)

        self.assertEqual(items[0].list_price, new_price)

    def test_update_item_price_only_updates_specific_item(self):
        """Test update_item_price() only updates the specified item."""
        list_id = self.price_list_repo.create("Test List")
        pli_id_1 = self.price_list_repo.add_item(list_id, self.sample_product_1, 19.99)
        pli_id_2 = self.price_list_repo.add_item(list_id, self.sample_product_2, 24.99)

        self.price_list_repo.update_item_price(pli_id_1, 29.99)
        items = self.price_list_repo.get_items(list_id)

        # Items may be returned in display_name order, so find by item_id
        prices = {i.item_id: i.list_price for i in items}
        self.assertEqual(prices[self.sample_product_1], 29.99)
        self.assertEqual(prices[self.sample_product_2], 24.99)


class TestPriceListRemoveItem(TestPriceListRepositoryBase):
    """Test remove_item() method."""

    def test_remove_item_deletes_item(self):
        """Test remove_item() removes an item from the price list."""
        list_id = self.price_list_repo.create("Test List")
        pli_id = self.price_list_repo.add_item(list_id, self.sample_product_1, 19.99)

        self.price_list_repo.remove_item(pli_id)
        items = self.price_list_repo.get_items(list_id)

        self.assertEqual(len(items), 0)

    def test_remove_item_only_removes_specific_item(self):
        """Test remove_item() only removes the specified item."""
        list_id = self.price_list_repo.create("Test List")
        pli_id_1 = self.price_list_repo.add_item(list_id, self.sample_product_1, 19.99)
        pli_id_2 = self.price_list_repo.add_item(list_id, self.sample_product_2, 24.99)

        self.price_list_repo.remove_item(pli_id_1)
        items = self.price_list_repo.get_items(list_id)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].item_id, self.sample_product_2)


class TestPriceListBulkAddAllItems(TestPriceListRepositoryBase):
    """Test bulk_add_all_items() method."""

    def test_bulk_add_all_items_returns_count(self):
        """Test bulk_add_all_items() returns count of added items."""
        list_id = self.price_list_repo.create("Test List")
        count = self.price_list_repo.bulk_add_all_items(list_id)

        self.assertIsInstance(count, int)
        self.assertGreater(count, 0)

    def test_bulk_add_all_items_adds_all_active_items(self):
        """Test bulk_add_all_items() adds all active inventory items."""
        list_id = self.price_list_repo.create("Test List")
        count = self.price_list_repo.bulk_add_all_items(list_id)
        items = self.price_list_repo.get_items(list_id)

        self.assertEqual(len(items), count)
        self.assertEqual(count, 3)  # We created 3 sample products

    def test_bulk_add_all_items_uses_current_sell_price(self):
        """Test bulk_add_all_items() uses current sell price from inventory."""
        list_id = self.price_list_repo.create("Test List")
        self.price_list_repo.bulk_add_all_items(list_id)
        items = self.price_list_repo.get_items(list_id)

        # Verify prices match sell_price from sample products
        prices = sorted([item.list_price for item in items])
        self.assertEqual(prices, [4.99, 9.99, 14.99])

    def test_bulk_add_all_items_does_not_add_duplicates(self):
        """Test bulk_add_all_items() doesn't add items already in list."""
        list_id = self.price_list_repo.create("Test List")
        self.price_list_repo.add_item(list_id, self.sample_product_1, 19.99)

        count = self.price_list_repo.bulk_add_all_items(list_id)
        items = self.price_list_repo.get_items(list_id)

        # Should add 2 more (3 total - 1 already there)
        self.assertEqual(count, 2)
        self.assertEqual(len(items), 3)


class TestPriceListGetSummary(TestPriceListRepositoryBase):
    """Test get_summary() method."""

    def test_get_summary_returns_dict(self):
        """Test get_summary() returns a dictionary."""
        summary = self.price_list_repo.get_summary()

        self.assertIsInstance(summary, dict)

    def test_get_summary_counts_total_lists(self):
        """Test get_summary() counts total price lists."""
        self.price_list_repo.create("List 1")
        self.price_list_repo.create("List 2")

        summary = self.price_list_repo.get_summary()

        self.assertEqual(summary["total_lists"], 2)

    def test_get_summary_counts_active_lists(self):
        """Test get_summary() counts active price lists."""
        list_id_1 = self.price_list_repo.create("List 1")
        list_id_2 = self.price_list_repo.create("List 2")
        self.price_list_repo.update(list_id_1, "List 1", "", False)

        summary = self.price_list_repo.get_summary()

        self.assertEqual(summary["active_lists"], 1)

    def test_get_summary_counts_total_items_priced(self):
        """Test get_summary() counts total items across all price lists."""
        list_id_1 = self.price_list_repo.create("List 1")
        list_id_2 = self.price_list_repo.create("List 2")

        self.price_list_repo.add_item(list_id_1, self.sample_product_1, 19.99)
        self.price_list_repo.add_item(list_id_1, self.sample_product_2, 24.99)
        self.price_list_repo.add_item(list_id_2, self.sample_product_3, 7.99)

        summary = self.price_list_repo.get_summary()

        self.assertEqual(summary["total_items_priced"], 3)

    def test_get_summary_returns_zeros_when_empty(self):
        """Test get_summary() returns zeros when no lists exist."""
        summary = self.price_list_repo.get_summary()

        self.assertEqual(summary["total_lists"], 0)
        self.assertEqual(summary["active_lists"], 0)
        self.assertEqual(summary["total_items_priced"], 0)

    def test_get_summary_includes_avg_margin(self):
        """Test get_summary() includes average margin."""
        summary = self.price_list_repo.get_summary()

        self.assertIn("avg_margin", summary)
        self.assertIsInstance(summary["avg_margin"], float)


if __name__ == "__main__":
    unittest.main()
