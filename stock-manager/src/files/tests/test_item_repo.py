"""
tests/test_item_repo.py — Tests for ItemRepository.

Tests cover CRUD operations for inventory items including
products and matrix entries.
"""
from __future__ import annotations

import unittest
import tempfile
import os
import sys
import shutil

# Add src/files to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.core.database as db_mod
from app.repositories.item_repo import ItemRepository


class TestItemRepoBase(unittest.TestCase):
    """Base test class with shared setup."""

    @classmethod
    def setUpClass(cls):
        """Set up test database."""
        cls.tmp_dir = tempfile.mkdtemp()
        cls.db_file = os.path.join(cls.tmp_dir, "test.db")
        cls.original_db_path = db_mod.DB_PATH
        db_mod.DB_PATH = cls.db_file
        db_mod.init_db()

    @classmethod
    def tearDownClass(cls):
        """Clean up test database."""
        db_mod.DB_PATH = cls.original_db_path
        try:
            shutil.rmtree(cls.tmp_dir)
        except:
            pass

    def setUp(self):
        """Create fresh repo for each test with unique DB."""
        # Create a unique DB for each test to avoid constraint issues
        self.test_tmp_dir = tempfile.mkdtemp()
        self.test_db_file = os.path.join(self.test_tmp_dir, "test.db")
        db_mod.DB_PATH = self.test_db_file
        db_mod.init_db()
        self.item_repo = ItemRepository()

    def tearDown(self):
        """Clean up test database."""
        try:
            shutil.rmtree(self.test_tmp_dir)
        except:
            pass


class TestItemRepoRead(TestItemRepoBase):
    """Test read operations on ItemRepository."""

    def test_get_all_items_empty(self):
        """Test get_all_items returns empty list on fresh database."""
        items = self.item_repo.get_all_items()
        self.assertIsInstance(items, list)
        self.assertEqual(len(items), 0)

    def test_get_all_items_with_product(self):
        """Test get_all_items returns created product."""
        pid = self.item_repo.add_product(
            brand="Apple", name="Screen Protector", color="Clear",
            stock=50, barcode="TEST-001", min_stock=10, sell_price=9.99
        )
        items = self.item_repo.get_all_items()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, pid)

    def test_get_by_id_returns_correct_item(self):
        """Test get_by_id returns the correct item."""
        pid = self.item_repo.add_product(
            brand="Apple", name="Screen Protector", color="Clear",
            stock=50, barcode="TEST-001", min_stock=10, sell_price=9.99
        )
        item = self.item_repo.get_by_id(pid)

        self.assertIsNotNone(item)
        self.assertEqual(item.id, pid)
        self.assertEqual(item.brand, "Apple")
        self.assertEqual(item.name, "Screen Protector")
        self.assertEqual(item.stock, 50)

    def test_get_by_id_invalid_returns_none(self):
        """Test get_by_id with invalid ID returns None."""
        item = self.item_repo.get_by_id(9999)
        self.assertIsNone(item)

    def test_get_by_barcode_returns_correct_item(self):
        """Test get_by_barcode returns the correct item."""
        pid = self.item_repo.add_product(
            brand="Apple", name="Screen Protector", color="Clear",
            stock=50, barcode="BC-UNIQUE-001", min_stock=10, sell_price=9.99
        )
        item = self.item_repo.get_by_barcode("BC-UNIQUE-001")

        self.assertIsNotNone(item)
        self.assertEqual(item.id, pid)
        self.assertEqual(item.barcode, "BC-UNIQUE-001")

    def test_get_by_barcode_invalid_returns_none(self):
        """Test get_by_barcode with invalid barcode returns None."""
        item = self.item_repo.get_by_barcode("NONEXISTENT")
        self.assertIsNone(item)

    def test_get_all_products_returns_standalone_only(self):
        """Test get_all_products returns only standalone products."""
        pid = self.item_repo.add_product(
            brand="Apple", name="Screen Protector", color="Clear",
            stock=50, barcode="BC-PROD-001", min_stock=10
        )
        items = self.item_repo.get_all_products()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, pid)
        self.assertTrue(items[0].is_product)

    def test_get_low_stock_empty_when_no_low_stock(self):
        """Test get_low_stock returns empty when no items are low."""
        self.item_repo.add_product(
            brand="Apple", name="Screen Protector", color="Clear",
            stock=50, barcode="BC-GOOD-001", min_stock=10
        )
        items = self.item_repo.get_low_stock()
        self.assertEqual(len(items), 0)

    def test_get_low_stock_returns_low_stock_items(self):
        """Test get_low_stock returns items at or below min_stock."""
        pid = self.item_repo.add_product(
            brand="Samsung", name="Battery", color="Black",
            stock=5, barcode="BC-LOW-001", min_stock=10, sell_price=25.99
        )
        items = self.item_repo.get_low_stock()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, pid)
        self.assertEqual(items[0].stock, 5)
        self.assertEqual(items[0].min_stock, 10)

    def test_get_summary(self):
        """Test get_summary returns correct aggregates."""
        self.item_repo.add_product(
            brand="Apple", name="Screen Protector", color="Clear",
            stock=50, barcode="BC-SUM-001", min_stock=10
        )
        summary = self.item_repo.get_summary()

        self.assertEqual(summary["total_products"], 1)
        self.assertEqual(summary["total_units"], 50)
        self.assertEqual(summary["out_of_stock_count"], 0)


class TestItemRepoWrite(TestItemRepoBase):
    """Test write operations on ItemRepository."""

    def test_add_product_returns_id(self):
        """Test add_product returns a valid ID."""
        pid = self.item_repo.add_product(
            brand="Samsung", name="Battery", color="Black",
            stock=25, barcode="BC-WRITE-001", min_stock=5, sell_price=29.99
        )

        self.assertGreater(pid, 0)

    def test_add_product_creates_entry(self):
        """Test add_product creates a database entry."""
        pid = self.item_repo.add_product(
            brand="LG", name="Display", color="White",
            stock=10, barcode="BC-CREATE-001", min_stock=2, sell_price=150.00
        )

        item = self.item_repo.get_by_id(pid)
        self.assertIsNotNone(item)
        self.assertEqual(item.brand, "LG")
        self.assertEqual(item.name, "Display")
        self.assertEqual(item.color, "White")

    def test_add_product_without_barcode(self):
        """Test add_product with None barcode."""
        pid = self.item_repo.add_product(
            brand="Generic", name="Cable", color="Black",
            stock=100, barcode=None, min_stock=10, sell_price=5.99
        )

        item = self.item_repo.get_by_id(pid)
        self.assertIsNone(item.barcode)

    def test_update_product(self):
        """Test update_product modifies existing product."""
        pid = self.item_repo.add_product(
            brand="Apple", name="Screen Protector", color="Clear",
            stock=50, barcode="BC-UPD-001", min_stock=10, sell_price=9.99
        )

        self.item_repo.update_product(
            pid, brand="Apple Inc", name="Premium Screen Protector",
            color="Clear Matte", barcode="BC-UPD-001", min_stock=15, sell_price=12.99
        )

        item = self.item_repo.get_by_id(pid)
        self.assertEqual(item.brand, "Apple Inc")
        self.assertEqual(item.name, "Premium Screen Protector")
        self.assertEqual(item.min_stock, 15)

    def test_delete_product(self):
        """Test delete_product removes item."""
        pid = self.item_repo.add_product(
            brand="Apple", name="Screen Protector", color="Clear",
            stock=50, barcode="BC-DEL-001", min_stock=10
        )

        self.item_repo.delete(pid)

        item = self.item_repo.get_by_id(pid)
        self.assertIsNone(item)

    def test_apply_delta_positive(self):
        """Test apply_delta with positive delta increases stock."""
        pid = self.item_repo.add_product(
            brand="Apple", name="Item", color="", stock=50, barcode="BC-DELTA-P", min_stock=10
        )

        conn = db_mod.get_connection()
        before, after = self.item_repo.apply_delta(conn, pid, 10)
        conn.close()

        self.assertEqual(before, 50)
        self.assertEqual(after, 60)

    def test_apply_delta_negative(self):
        """Test apply_delta with negative delta decreases stock."""
        pid = self.item_repo.add_product(
            brand="Apple", name="Item", color="", stock=50, barcode="BC-DELTA-N", min_stock=10
        )

        conn = db_mod.get_connection()
        before, after = self.item_repo.apply_delta(conn, pid, -15)
        conn.close()

        self.assertEqual(before, 50)
        self.assertEqual(after, 35)

    def test_set_exact(self):
        """Test set_exact sets stock to exact value."""
        pid = self.item_repo.add_product(
            brand="Apple", name="Item", color="", stock=50, barcode="BC-EXACT", min_stock=10
        )

        conn = db_mod.get_connection()
        before, after = self.item_repo.set_exact(conn, pid, 100)
        conn.close()

        self.assertEqual(before, 50)
        self.assertEqual(after, 100)

    def test_update_min_stock(self):
        """Test update_min_stock changes threshold."""
        pid = self.item_repo.add_product(
            brand="Apple", name="Item", color="", stock=50, barcode="BC-MINST", min_stock=10
        )

        self.item_repo.update_min_stock(pid, 25)

        item = self.item_repo.get_by_id(pid)
        self.assertEqual(item.min_stock, 25)

    def test_update_barcode(self):
        """Test update_barcode changes or sets barcode."""
        pid = self.item_repo.add_product(
            brand="Apple", name="Item", color="", stock=50, barcode="BC-OLDBAR", min_stock=10
        )

        self.item_repo.update_barcode(pid, "BC-NEWBAR")

        item = self.item_repo.get_by_id(pid)
        self.assertEqual(item.barcode, "BC-NEWBAR")


class TestItemRepoSearch(TestItemRepoBase):
    """Test search functionality."""

    def test_search_by_brand(self):
        """Test get_all_items search by brand."""
        pid = self.item_repo.add_product(
            brand="AppleSearch", name="Screen", color="Clear",
            stock=50, barcode="BC-SBRAND", min_stock=10
        )
        items = self.item_repo.get_all_items(search="AppleSearch")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, pid)

    def test_search_by_name(self):
        """Test get_all_items search by name."""
        self.item_repo.add_product(
            brand="Apple", name="ScreenSearch", color="Clear",
            stock=50, barcode="BC-SNAME", min_stock=10
        )
        items = self.item_repo.get_all_items(search="ScreenSearch")
        self.assertEqual(len(items), 1)

    def test_search_by_barcode(self):
        """Test get_all_items search by barcode."""
        self.item_repo.add_product(
            brand="Apple", name="Screen", color="Clear",
            stock=50, barcode="BC-SBCODE", min_stock=10
        )
        items = self.item_repo.get_all_items(search="BC-SBCODE")
        self.assertEqual(len(items), 1)

    def test_search_no_results(self):
        """Test search returns empty list when no matches."""
        self.item_repo.add_product(
            brand="Apple", name="Screen", color="Clear",
            stock=50, barcode="BC-SEARCH", min_stock=10
        )
        items = self.item_repo.get_all_items(search="NonExistent")
        self.assertEqual(len(items), 0)


class TestItemProperties(TestItemRepoBase):
    """Test computed properties of InventoryItem."""

    def test_is_product_true_for_standalone(self):
        """Test is_product is True for standalone products."""
        pid = self.item_repo.add_product(
            brand="Apple", name="Item", color="",
            stock=50, barcode="BC-PROP-IS", min_stock=10
        )
        item = self.item_repo.get_by_id(pid)
        self.assertTrue(item.is_product)

    def test_best_bung_calculation(self):
        """Test best_bung (surplus above minimum)."""
        pid = self.item_repo.add_product(
            brand="Apple", name="Item", color="",
            stock=50, barcode="BC-PROP-BB", min_stock=10
        )
        item = self.item_repo.get_by_id(pid)
        self.assertEqual(item.best_bung, 40)

    def test_needs_reorder_false_when_above_minimum(self):
        """Test needs_reorder is False when stock > min_stock."""
        pid = self.item_repo.add_product(
            brand="Apple", name="Item", color="",
            stock=50, barcode="BC-PROP-NRF", min_stock=10
        )
        item = self.item_repo.get_by_id(pid)
        self.assertFalse(item.needs_reorder)

    def test_needs_reorder_true_when_below_minimum(self):
        """Test needs_reorder is True when stock < min_stock."""
        pid = self.item_repo.add_product(
            brand="Samsung", name="Battery", color="",
            stock=5, barcode="BC-PROP-NRT", min_stock=10
        )
        item = self.item_repo.get_by_id(pid)
        self.assertTrue(item.needs_reorder)

    def test_is_out_true_when_zero_stock(self):
        """Test is_out is True when stock == 0."""
        pid = self.item_repo.add_product(
            brand="Test", name="Item", color="",
            stock=0, barcode="BC-PROP-OUT", min_stock=5
        )
        item = self.item_repo.get_by_id(pid)
        self.assertTrue(item.is_out)


if __name__ == "__main__":
    unittest.main()
