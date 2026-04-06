"""
tests/test_export_service.py — Tests for ExportService.

Tests cover CSV export for inventory, transactions, and low stock items.
"""
from __future__ import annotations

import unittest
import tempfile
import os
import csv
import sys
import shutil

# Add src/files to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.core.database as db_mod
from app.repositories.item_repo import ItemRepository
from app.repositories.transaction_repo import TransactionRepository
from app.services.export_service import ExportService


class TestExportServiceBase(unittest.TestCase):
    """Base test class with shared setup."""

    def setUp(self):
        """Create fresh services for each test with unique DB."""
        self.test_tmp_dir = tempfile.mkdtemp()
        self.test_db_file = os.path.join(self.test_tmp_dir, "test.db")
        self.export_dir = os.path.join(self.test_tmp_dir, "exports")
        os.makedirs(self.export_dir, exist_ok=True)
        self.original_db_path = db_mod.DB_PATH
        db_mod.DB_PATH = self.test_db_file
        db_mod.init_db()
        self.item_repo = ItemRepository()
        self.export_svc = ExportService()

    def tearDown(self):
        """Clean up test database."""
        db_mod.DB_PATH = self.original_db_path
        try:
            shutil.rmtree(self.test_tmp_dir)
        except:
            pass

    def _add_stock_transaction(self, item_id: int, operation: str, quantity: int):
        """Helper to manually add a transaction."""
        conn = db_mod.get_connection()
        conn.execute(
            """INSERT INTO inventory_transactions
               (item_id, operation, quantity, stock_before, stock_after, note)
               VALUES (?, ?, ?, 0, ?, ?)""",
            (item_id, operation, quantity, quantity, f"Test {operation}")
        )
        conn.commit()
        conn.close()


class TestExportServiceInventory(TestExportServiceBase):
    """Test inventory CSV export."""

    def test_export_inventory_csv_creates_file(self):
        """Test export_inventory_csv creates a file."""
        pid = self.item_repo.add_product(
            brand="Apple", name="Item", color="", stock=50, barcode="TEST-EXP", min_stock=10
        )
        export_path = os.path.join(self.export_dir, "inventory.csv")

        result = self.export_svc.export_inventory_csv(export_path)

        self.assertEqual(result, export_path)
        self.assertTrue(os.path.isfile(export_path))

    def test_export_inventory_csv_valid_content(self):
        """Test export_inventory_csv contains correct headers and data."""
        pid = self.item_repo.add_product(
            brand="Apple", name="Screen Protector", color="Clear",
            stock=50, barcode="TEST-CONTENT", min_stock=10
        )
        export_path = os.path.join(self.export_dir, "inv_content.csv")
        self.export_svc.export_inventory_csv(export_path)

        with open(export_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        headers = rows[0]
        self.assertIn("ID", headers)
        self.assertIn("Brand", headers)
        self.assertIn("Stock", headers)

        self.assertGreater(len(rows), 1)
        data_row = rows[1]
        self.assertEqual(data_row[1], "Apple")
        self.assertEqual(data_row[2], "Screen Protector")

    def test_export_inventory_csv_empty_database(self):
        """Test export_inventory_csv with empty database."""
        export_path = os.path.join(self.export_dir, "inv_empty.csv")
        result = self.export_svc.export_inventory_csv(export_path)

        self.assertTrue(os.path.isfile(export_path))

        with open(export_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        self.assertEqual(len(rows), 1)  # Headers only


class TestExportServiceTransactions(TestExportServiceBase):
    """Test transaction CSV export."""

    def test_export_transactions_csv_creates_file(self):
        """Test export_transactions_csv creates a file."""
        pid = self.item_repo.add_product(
            brand="Apple", name="Item", color="", stock=50, barcode="TEST-TXN", min_stock=10
        )
        self._add_stock_transaction(pid, "IN", 10)

        export_path = os.path.join(self.export_dir, "transactions.csv")
        result = self.export_svc.export_transactions_csv(export_path)

        self.assertEqual(result, export_path)
        self.assertTrue(os.path.isfile(export_path))

    def test_export_transactions_csv_valid_content(self):
        """Test export_transactions_csv contains correct data."""
        pid = self.item_repo.add_product(
            brand="Apple", name="Item", color="", stock=50, barcode="TEST-TXNC", min_stock=10
        )
        self._add_stock_transaction(pid, "IN", 15)

        export_path = os.path.join(self.export_dir, "txn_content.csv")
        self.export_svc.export_transactions_csv(export_path)

        with open(export_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        headers = rows[0]
        self.assertIn("Operation", headers)
        self.assertIn("Quantity", headers)

    def test_export_transactions_csv_empty_database(self):
        """Test export_transactions_csv with no transactions."""
        export_path = os.path.join(self.export_dir, "txn_empty.csv")
        result = self.export_svc.export_transactions_csv(export_path)

        self.assertTrue(os.path.isfile(export_path))

        with open(export_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        self.assertEqual(len(rows), 1)  # Headers only


class TestExportServiceLowStock(TestExportServiceBase):
    """Test low stock CSV export."""

    def test_export_low_stock_csv_creates_file(self):
        """Test export_low_stock_csv creates a file."""
        pid = self.item_repo.add_product(
            brand="Samsung", name="Battery", color="",
            stock=5, barcode="TEST-LOW", min_stock=10
        )
        export_path = os.path.join(self.export_dir, "low_stock.csv")
        result = self.export_svc.export_low_stock_csv(export_path)

        self.assertEqual(result, export_path)
        self.assertTrue(os.path.isfile(export_path))

    def test_export_low_stock_csv_empty_when_no_low_stock(self):
        """Test export_low_stock_csv is empty when no items are low."""
        pid = self.item_repo.add_product(
            brand="Apple", name="Item", color="", stock=50, barcode="TEST-NOLOW", min_stock=10
        )
        export_path = os.path.join(self.export_dir, "low_empty.csv")
        self.export_svc.export_low_stock_csv(export_path)

        with open(export_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        self.assertEqual(len(rows), 1)  # Headers only

    def test_export_low_stock_csv_includes_low_items(self):
        """Test export_low_stock_csv includes items at/below threshold."""
        pid = self.item_repo.add_product(
            brand="Samsung", name="Battery", color="",
            stock=5, barcode="TEST-LOWSTK", min_stock=10
        )
        export_path = os.path.join(self.export_dir, "low_items.csv")
        self.export_svc.export_low_stock_csv(export_path)

        with open(export_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        self.assertEqual(len(rows), 2)  # Headers + 1 item


class TestExportServiceDirectoryCreation(TestExportServiceBase):
    """Test directory creation during export."""

    def test_export_creates_missing_directory(self):
        """Test export creates missing directory structure."""
        nested_path = os.path.join(self.test_tmp_dir, "nested", "export", "inv.csv")
        self.export_svc.export_inventory_csv(nested_path)

        self.assertTrue(os.path.isdir(os.path.dirname(nested_path)))
        self.assertTrue(os.path.isfile(nested_path))


if __name__ == "__main__":
    unittest.main()
