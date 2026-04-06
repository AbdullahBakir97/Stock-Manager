"""
tests/test_location_service.py — Tests for LocationService.

Tests cover location CRUD, stock transfers, and availability checks.
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
from app.services.location_service import LocationService


class TestLocationServiceBase(unittest.TestCase):
    """Base test class with shared setup."""

    def setUp(self):
        """Create fresh services for each test with unique DB."""
        self.test_tmp_dir = tempfile.mkdtemp()
        self.test_db_file = os.path.join(self.test_tmp_dir, "test.db")
        self.original_db_path = db_mod.DB_PATH
        db_mod.DB_PATH = self.test_db_file
        db_mod.init_db()
        self.item_repo = ItemRepository()
        self.location_svc = LocationService()

        # Create sample product
        self.sample_product = self.item_repo.add_product(
            brand="Apple",
            name="Screen Protector",
            color="Clear",
            stock=100,
            barcode="TEST-LOC-1",
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


class TestLocationCRUD(TestLocationServiceBase):
    """Test location CRUD operations."""

    def test_add_location_with_valid_name(self):
        """Test adding location with valid name."""
        location_id = self.location_svc.add("Main Store")

        self.assertIsNotNone(location_id)
        self.assertGreater(location_id, 0)

    def test_add_location_with_empty_name_raises_error(self):
        """Test adding location with empty name raises ValueError."""
        with self.assertRaises(ValueError):
            self.location_svc.add("")

        with self.assertRaises(ValueError):
            self.location_svc.add("   ")

    def test_add_location_with_description(self):
        """Test adding location with description."""
        location_id = self.location_svc.add(
            "Main Store",
            description="Primary retail location"
        )

        self.assertGreater(location_id, 0)

    def test_add_location_as_default(self):
        """Test adding location as default."""
        location_id = self.location_svc.add(
            "Default Location",
            is_default=True
        )

        location = self.location_svc.get_by_id(location_id)
        self.assertTrue(location.is_default)

    def test_get_all_locations(self):
        """Test retrieving all locations."""
        self.location_svc.add("Location 1")
        self.location_svc.add("Location 2")

        locations = self.location_svc.get_all()
        self.assertIsInstance(locations, list)
        self.assertGreaterEqual(len(locations), 2)

    def test_get_location_by_id(self):
        """Test retrieving location by ID."""
        location_id = self.location_svc.add("Test Location")

        location = self.location_svc.get_by_id(location_id)
        self.assertIsNotNone(location)
        self.assertEqual(location.id, location_id)
        self.assertEqual(location.name, "Test Location")

    def test_get_nonexistent_location_returns_none(self):
        """Test retrieving non-existent location returns None."""
        location = self.location_svc.get_by_id(9999)
        self.assertIsNone(location)

    def test_get_default_location(self):
        """Test retrieving default location."""
        default_id = self.location_svc.add("Default", is_default=True)

        default = self.location_svc.get_default()
        if default:
            self.assertEqual(default.id, default_id)

    def test_update_location(self):
        """Test updating location name."""
        location_id = self.location_svc.add("Old Name")
        self.location_svc.update(location_id, "New Name")

        location = self.location_svc.get_by_id(location_id)
        self.assertEqual(location.name, "New Name")

    def test_update_location_with_empty_name_raises_error(self):
        """Test updating location with empty name raises ValueError."""
        location_id = self.location_svc.add("Location")

        with self.assertRaises(ValueError):
            self.location_svc.update(location_id, "")

    def test_delete_location(self):
        """Test deleting location."""
        location_id = self.location_svc.add("Deletable Location")

        result = self.location_svc.delete(location_id)
        self.assertTrue(result)


class TestStockTransfer(TestLocationServiceBase):
    """Test stock transfer operations."""

    def setUp(self):
        """Set up with multiple locations and stock at location1."""
        super().setUp()
        self.location1 = self.location_svc.add("Warehouse A")
        self.location2 = self.location_svc.add("Warehouse B")
        # Set stock at source location so transfers can succeed
        from app.repositories.location_repo import LocationRepository
        loc_repo = LocationRepository()
        loc_repo.set_stock(self.sample_product, self.location1, 100)

    def test_transfer_with_valid_params(self):
        """Test transferring stock between locations."""
        transfer_id = self.location_svc.transfer(
            self.sample_product,
            self.location1,
            self.location2,
            quantity=10,
            note="Regular restock"
        )

        self.assertIsNotNone(transfer_id)
        self.assertGreater(transfer_id, 0)

    def test_transfer_with_zero_qty_raises_error(self):
        """Test transferring zero quantity raises ValueError."""
        with self.assertRaises(ValueError):
            self.location_svc.transfer(
                self.sample_product,
                self.location1,
                self.location2,
                quantity=0
            )

    def test_transfer_with_negative_qty_raises_error(self):
        """Test transferring negative quantity raises ValueError."""
        with self.assertRaises(ValueError):
            self.location_svc.transfer(
                self.sample_product,
                self.location1,
                self.location2,
                quantity=-5
            )

    def test_transfer_same_source_dest_raises_error(self):
        """Test transferring to same location raises ValueError."""
        with self.assertRaises(ValueError):
            self.location_svc.transfer(
                self.sample_product,
                self.location1,
                self.location1,
                quantity=5
            )

    def test_transfer_insufficient_stock_raises_error(self):
        """Test transferring more than available raises ValueError."""
        with self.assertRaises(ValueError):
            self.location_svc.transfer(
                self.sample_product,
                self.location1,
                self.location2,
                quantity=1000
            )

    def test_transfer_with_note(self):
        """Test transferring with note."""
        transfer_id = self.location_svc.transfer(
            self.sample_product,
            self.location1,
            self.location2,
            quantity=5,
            note="Emergency restock"
        )

        self.assertGreater(transfer_id, 0)

    def test_get_transfers_for_item(self):
        """Test retrieving transfers for an item."""
        self.location_svc.transfer(
            self.sample_product,
            self.location1,
            self.location2,
            quantity=5
        )
        self.location_svc.transfer(
            self.sample_product,
            self.location2,
            self.location1,
            quantity=3
        )

        transfers = self.location_svc.get_transfers(item_id=self.sample_product)
        self.assertIsInstance(transfers, list)
        self.assertGreaterEqual(len(transfers), 2)

    def test_get_all_transfers(self):
        """Test retrieving all transfers."""
        self.location_svc.transfer(
            self.sample_product,
            self.location1,
            self.location2,
            quantity=5
        )

        transfers = self.location_svc.get_transfers()
        self.assertIsInstance(transfers, list)
        self.assertGreaterEqual(len(transfers), 1)


class TestLocationStock(TestLocationServiceBase):
    """Test stock-related location queries."""

    def setUp(self):
        """Set up with multiple locations."""
        super().setUp()
        self.location1 = self.location_svc.add("Warehouse A")
        self.location2 = self.location_svc.add("Warehouse B")

    def test_get_stock_breakdown_for_item(self):
        """Test getting stock breakdown across locations."""
        stock = self.location_svc.get_stock_breakdown(self.sample_product)

        self.assertIsInstance(stock, list)
        # Should have entries for locations with stock

    def test_get_location_items(self):
        """Test getting all items at a location."""
        items = self.location_svc.get_location_items(self.location1)

        self.assertIsInstance(items, list)


class TestLocationIntegration(TestLocationServiceBase):
    """Integration tests for locations."""

    def test_multiple_transfers_sequential(self):
        """Test multiple transfers in sequence."""
        location1 = self.location_svc.add("Location 1")
        location2 = self.location_svc.add("Location 2")
        location3 = self.location_svc.add("Location 3")

        # Set stock at source location
        from app.repositories.location_repo import LocationRepository
        loc_repo = LocationRepository()
        loc_repo.set_stock(self.sample_product, location1, 100)

        # Transfer from 1 to 2
        self.location_svc.transfer(
            self.sample_product, location1, location2, quantity=30
        )

        # Transfer from 2 to 3
        self.location_svc.transfer(
            self.sample_product, location2, location3, quantity=20
        )

        # Check transfers logged
        transfers = self.location_svc.get_transfers(
            item_id=self.sample_product
        )
        self.assertGreaterEqual(len(transfers), 2)

    def test_active_only_filter(self):
        """Test retrieving only active locations."""
        location1 = self.location_svc.add("Active Location")
        location2 = self.location_svc.add("Inactive Location")

        self.location_svc.update(location2, "Inactive Location", is_active=False)

        active = self.location_svc.get_all(active_only=True)
        self.assertIsInstance(active, list)


if __name__ == "__main__":
    unittest.main()
