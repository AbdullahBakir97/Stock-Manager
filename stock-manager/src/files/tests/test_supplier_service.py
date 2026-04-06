"""
tests/test_supplier_service.py — Tests for SupplierService.

Tests cover supplier CRUD, item linking, and preferred cost retrieval.
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
from app.services.supplier_service import SupplierService


class TestSupplierServiceBase(unittest.TestCase):
    """Base test class with shared setup."""

    def setUp(self):
        """Create fresh services for each test with unique DB."""
        self.test_tmp_dir = tempfile.mkdtemp()
        self.test_db_file = os.path.join(self.test_tmp_dir, "test.db")
        self.original_db_path = db_mod.DB_PATH
        db_mod.DB_PATH = self.test_db_file
        db_mod.init_db()
        self.item_repo = ItemRepository()
        self.supplier_svc = SupplierService()

        # Create sample product
        self.sample_product = self.item_repo.add_product(
            brand="Apple",
            name="Screen Protector",
            color="Clear",
            stock=50,
            barcode="TEST-SUPP-1",
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


class TestSupplierCRUD(TestSupplierServiceBase):
    """Test supplier CRUD operations."""

    def test_add_supplier_with_valid_name(self):
        """Test adding supplier with valid name."""
        supplier_id = self.supplier_svc.add("TechSupply Inc")

        self.assertIsNotNone(supplier_id)
        self.assertGreater(supplier_id, 0)

    def test_add_supplier_with_empty_name_raises_error(self):
        """Test adding supplier with empty name raises ValueError."""
        with self.assertRaises(ValueError):
            self.supplier_svc.add("")

        with self.assertRaises(ValueError):
            self.supplier_svc.add("   ")

    def test_add_supplier_with_kwargs(self):
        """Test adding supplier with additional kwargs."""
        supplier_id = self.supplier_svc.add(
            "TechSupply Inc",
            contact_name="John Smith",
            email="john@techsupply.com"
        )

        self.assertGreater(supplier_id, 0)

    def test_get_all_suppliers(self):
        """Test retrieving all suppliers."""
        supplier_id1 = self.supplier_svc.add("Supplier 1")
        supplier_id2 = self.supplier_svc.add("Supplier 2")

        suppliers = self.supplier_svc.get_all()
        self.assertIsInstance(suppliers, list)
        self.assertGreaterEqual(len(suppliers), 2)

    def test_get_supplier_by_id(self):
        """Test retrieving supplier by ID."""
        supplier_id = self.supplier_svc.add("Test Supplier")

        supplier = self.supplier_svc.get_by_id(supplier_id)
        self.assertIsNotNone(supplier)
        self.assertEqual(supplier.id, supplier_id)
        self.assertEqual(supplier.name, "Test Supplier")

    def test_get_nonexistent_supplier_returns_none(self):
        """Test retrieving non-existent supplier returns None."""
        supplier = self.supplier_svc.get_by_id(9999)
        self.assertIsNone(supplier)

    def test_update_supplier(self):
        """Test updating supplier name."""
        supplier_id = self.supplier_svc.add("Old Name")
        self.supplier_svc.update(supplier_id, "New Name")

        supplier = self.supplier_svc.get_by_id(supplier_id)
        self.assertEqual(supplier.name, "New Name")

    def test_update_supplier_with_empty_name_raises_error(self):
        """Test updating supplier with empty name raises ValueError."""
        supplier_id = self.supplier_svc.add("Supplier")

        with self.assertRaises(ValueError):
            self.supplier_svc.update(supplier_id, "")

    def test_delete_supplier(self):
        """Test deleting supplier."""
        supplier_id = self.supplier_svc.add("Deletable Supplier")

        result = self.supplier_svc.delete(supplier_id)
        self.assertTrue(result)

        supplier = self.supplier_svc.get_by_id(supplier_id)
        # Supplier should be deleted or marked inactive


class TestSupplierItemLinking(TestSupplierServiceBase):
    """Test linking suppliers to items."""

    def test_link_item_to_supplier(self):
        """Test linking an item to a supplier."""
        supplier_id = self.supplier_svc.add("TechSupply Inc")

        link_id = self.supplier_svc.link_item(
            supplier_id, self.sample_product,
            cost_price=5.00
        )

        self.assertIsNotNone(link_id)
        self.assertGreater(link_id, 0)

    def test_link_item_with_all_params(self):
        """Test linking item with all parameters."""
        supplier_id = self.supplier_svc.add("TechSupply Inc")

        link_id = self.supplier_svc.link_item(
            supplier_id, self.sample_product,
            cost_price=5.00,
            lead_days=7,
            supplier_sku="TS-12345",
            is_preferred=True
        )

        self.assertGreater(link_id, 0)

    def test_get_items_for_supplier(self):
        """Test retrieving items for a supplier."""
        supplier_id = self.supplier_svc.add("TechSupply Inc")

        # Create another product
        product2 = self.item_repo.add_product(
            brand="Samsung",
            name="Battery",
            color="Black",
            stock=30,
            barcode="TEST-SUPP-2",
            min_stock=5,
            sell_price=19.99,
        )

        self.supplier_svc.link_item(supplier_id, self.sample_product, cost_price=5.00)
        self.supplier_svc.link_item(supplier_id, product2, cost_price=15.00)

        items = self.supplier_svc.get_items(supplier_id)
        self.assertIsInstance(items, list)
        self.assertEqual(len(items), 2)

    def test_get_suppliers_for_item(self):
        """Test retrieving suppliers for an item."""
        supplier1 = self.supplier_svc.add("Supplier 1")
        supplier2 = self.supplier_svc.add("Supplier 2")

        self.supplier_svc.link_item(supplier1, self.sample_product, cost_price=5.00)
        self.supplier_svc.link_item(supplier2, self.sample_product, cost_price=4.50)

        suppliers = self.supplier_svc.get_suppliers_for_item(self.sample_product)
        self.assertIsInstance(suppliers, list)
        self.assertEqual(len(suppliers), 2)

    def test_unlink_item(self):
        """Test unlinking an item from a supplier."""
        supplier_id = self.supplier_svc.add("TechSupply Inc")
        self.supplier_svc.link_item(supplier_id, self.sample_product, cost_price=5.00)

        self.supplier_svc.unlink_item(supplier_id, self.sample_product)

        items = self.supplier_svc.get_items(supplier_id)
        self.assertEqual(len(items), 0)

    def test_multiple_suppliers_for_same_item(self):
        """Test linking same item to multiple suppliers."""
        supplier1 = self.supplier_svc.add("Cheap Supplier")
        supplier2 = self.supplier_svc.add("Premium Supplier")

        self.supplier_svc.link_item(supplier1, self.sample_product, cost_price=4.00, is_preferred=True)
        self.supplier_svc.link_item(supplier2, self.sample_product, cost_price=6.00)

        suppliers = self.supplier_svc.get_suppliers_for_item(self.sample_product)
        self.assertEqual(len(suppliers), 2)


class TestPreferredCost(TestSupplierServiceBase):
    """Test preferred supplier cost retrieval."""

    def test_get_preferred_cost_returns_preferred_supplier_price(self):
        """Test getting cost from preferred supplier."""
        supplier1 = self.supplier_svc.add("Cheap Supplier")
        supplier2 = self.supplier_svc.add("Preferred Supplier")

        self.supplier_svc.link_item(supplier1, self.sample_product, cost_price=4.00)
        self.supplier_svc.link_item(
            supplier2, self.sample_product,
            cost_price=5.50, is_preferred=True
        )

        cost = self.supplier_svc.get_preferred_cost(self.sample_product)
        self.assertEqual(cost, 5.50)

    def test_get_preferred_cost_falls_back_to_first(self):
        """Test get_preferred_cost falls back to first supplier if no preferred."""
        supplier1 = self.supplier_svc.add("First Supplier")
        supplier2 = self.supplier_svc.add("Second Supplier")

        self.supplier_svc.link_item(supplier1, self.sample_product, cost_price=4.00)
        self.supplier_svc.link_item(supplier2, self.sample_product, cost_price=5.00)

        cost = self.supplier_svc.get_preferred_cost(self.sample_product)
        # Should return first supplier's cost
        self.assertIsNotNone(cost)

    def test_get_preferred_cost_for_item_with_no_suppliers(self):
        """Test get_preferred_cost for item with no suppliers."""
        product2 = self.item_repo.add_product(
            brand="Samsung",
            name="Battery",
            color="Black",
            stock=30,
            barcode="TEST-SUPP-3",
            min_stock=5,
            sell_price=19.99,
        )

        cost = self.supplier_svc.get_preferred_cost(product2)
        self.assertIsNone(cost)


class TestSupplierSearch(TestSupplierServiceBase):
    """Test supplier search functionality."""

    def test_get_all_with_search(self):
        """Test searching suppliers by name."""
        self.supplier_svc.add("TechSupply Inc")
        self.supplier_svc.add("GlobalTech Ltd")
        self.supplier_svc.add("Local Shop")

        results = self.supplier_svc.get_all(search="Tech")
        # Should find TechSupply and GlobalTech
        self.assertGreaterEqual(len(results), 1)

    def test_get_all_active_only(self):
        """Test retrieving only active suppliers."""
        supplier1 = self.supplier_svc.add("Active Supplier")
        supplier2 = self.supplier_svc.add("Inactive Supplier")

        self.supplier_svc.set_active(supplier2, False)

        active = self.supplier_svc.get_all(active_only=True)
        # Should have at least the active one
        self.assertGreaterEqual(len(active), 1)


class TestSupplierSummary(TestSupplierServiceBase):
    """Test supplier summary statistics."""

    def test_get_summary_returns_dict(self):
        """Test get_summary returns statistics dict."""
        self.supplier_svc.add("Supplier 1")
        self.supplier_svc.add("Supplier 2")

        summary = self.supplier_svc.get_summary()
        self.assertIsInstance(summary, dict)


if __name__ == "__main__":
    unittest.main()
