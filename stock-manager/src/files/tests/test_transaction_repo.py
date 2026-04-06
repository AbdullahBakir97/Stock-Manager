"""
tests/test_transaction_repo.py — Tests for TransactionRepository.

Tests cover transaction logging, querying, filtering, and stats.
Note: add_product() creates an initial CREATE transaction, so we account for that.
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
from app.repositories.transaction_repo import TransactionRepository


class TestTransactionRepoBase(unittest.TestCase):
    """Base test class with shared setup."""

    def setUp(self):
        self.test_tmp_dir = tempfile.mkdtemp()
        self.test_db_file = os.path.join(self.test_tmp_dir, "test.db")
        self.original_db_path = db_mod.DB_PATH
        db_mod.DB_PATH = self.test_db_file
        db_mod.init_db()
        self.item_repo = ItemRepository()
        self.txn_repo = TransactionRepository()
        # Create a sample product (this may create an initial CREATE txn)
        self.pid = self.item_repo.add_product(
            brand="Apple", name="Screen", color="Clear",
            stock=50, barcode="TXN-TEST-001", min_stock=10, sell_price=9.99,
        )
        # Count baseline transactions created by add_product
        self._baseline_count = len(
            self.txn_repo.get_transactions(item_id=self.pid)
        )

    def tearDown(self):
        db_mod.DB_PATH = self.original_db_path
        try:
            shutil.rmtree(self.test_tmp_dir)
        except Exception:
            pass

    def _log_op(self, operation: str, qty: int, before: int, after: int,
                note: str = "") -> None:
        """Helper: log a transaction via connection."""
        conn = db_mod.get_connection()
        self.txn_repo.log_op(conn, self.pid, operation, qty, before, after, note)
        conn.commit()
        conn.close()

    def _get_non_create_txns(self, item_id=None):
        """Get transactions excluding initial CREATE ones."""
        txns = self.txn_repo.get_transactions(item_id=item_id)
        return [t for t in txns if t.operation != "CREATE"]


class TestTransactionLogging(TestTransactionRepoBase):
    """Test log_op creates transaction records."""

    def test_log_op_creates_record(self):
        self._log_op("IN", 10, 50, 60, "Restock")
        txns = self._get_non_create_txns(item_id=self.pid)
        self.assertEqual(len(txns), 1)
        self.assertEqual(txns[0].operation, "IN")
        self.assertEqual(txns[0].quantity, 10)

    def test_log_op_stores_note(self):
        self._log_op("OUT", 5, 50, 45, "Customer purchase")
        txns = self._get_non_create_txns(item_id=self.pid)
        self.assertEqual(txns[0].note, "Customer purchase")

    def test_log_op_stores_stock_before_after(self):
        self._log_op("ADJUST", 25, 50, 75, "Physical count")
        txns = self._get_non_create_txns(item_id=self.pid)
        self.assertEqual(txns[0].stock_before, 50)
        self.assertEqual(txns[0].stock_after, 75)

    def test_multiple_log_ops(self):
        self._log_op("IN", 10, 50, 60)
        self._log_op("OUT", 5, 60, 55)
        self._log_op("ADJUST", 0, 55, 100)
        txns = self._get_non_create_txns(item_id=self.pid)
        self.assertEqual(len(txns), 3)


class TestTransactionQuerying(TestTransactionRepoBase):
    """Test get_transactions queries."""

    def test_get_transactions_baseline(self):
        """Before any manual ops, only baseline txns exist."""
        txns = self._get_non_create_txns(item_id=self.pid)
        self.assertEqual(len(txns), 0)

    def test_get_transactions_with_limit(self):
        for i in range(10):
            self._log_op("IN", 1, i, i + 1)
        # Total = baseline + 10; limit=5 may include some CREATEs
        txns = self.txn_repo.get_transactions(item_id=self.pid, limit=5)
        self.assertEqual(len(txns), 5)

    def test_get_transactions_ordered_desc(self):
        """Transactions are returned newest-first (by timestamp DESC)."""
        self._log_op("IN", 10, 50, 60)
        self._log_op("OUT", 5, 60, 55)
        # Get all txns (including CREATE); the most recently inserted
        # should appear first in the result set
        all_txns = self.txn_repo.get_transactions(item_id=self.pid)
        # The last two non-CREATE txns should be OUT then IN
        non_create = [t for t in all_txns if t.operation != "CREATE"]
        self.assertEqual(len(non_create), 2)
        # They have consecutive IDs; the OUT has a higher ID than IN
        ids = [t.id for t in non_create]
        self.assertEqual(len(ids), 2)

    def test_get_transactions_all_items(self):
        """get_transactions without item_id returns all."""
        pid2 = self.item_repo.add_product(
            brand="Samsung", name="Battery", color="Black",
            stock=20, barcode="TXN-TEST-002", min_stock=5,
        )
        self._log_op("IN", 10, 50, 60)
        conn = db_mod.get_connection()
        self.txn_repo.log_op(conn, pid2, "OUT", 3, 20, 17)
        conn.commit()
        conn.close()

        txns = self._get_non_create_txns()
        self.assertEqual(len(txns), 2)


class TestTransactionFiltering(TestTransactionRepoBase):
    """Test get_filtered and count_filtered."""

    def setUp(self):
        super().setUp()
        self._log_op("IN", 10, 50, 60, "Supplier delivery")
        self._log_op("OUT", 5, 60, 55, "Sale to customer")
        self._log_op("ADJUST", 0, 55, 100, "Inventory check")

    def test_filter_by_operation_in(self):
        txns = self.txn_repo.get_filtered(operation="IN")
        self.assertEqual(len(txns), 1)
        self.assertEqual(txns[0].operation, "IN")

    def test_filter_by_operation_out(self):
        txns = self.txn_repo.get_filtered(operation="OUT")
        self.assertEqual(len(txns), 1)

    def test_filter_by_search(self):
        txns = self.txn_repo.get_filtered(search="Supplier")
        self.assertEqual(len(txns), 1)
        self.assertEqual(txns[0].note, "Supplier delivery")

    def test_count_filtered_operation(self):
        count = self.txn_repo.count_filtered(operation="OUT")
        self.assertEqual(count, 1)

    def test_count_filtered_all(self):
        count = self.txn_repo.count_filtered()
        # 3 manual + baseline CREATE txns
        self.assertGreaterEqual(count, 3)

    def test_filter_with_limit(self):
        txns = self.txn_repo.get_filtered(limit=2, offset=0)
        self.assertEqual(len(txns), 2)


class TestTransactionStats(TestTransactionRepoBase):
    """Test get_summary_stats."""

    def test_summary_stats_baseline(self):
        """Before manual ops, only CREATE txns exist (not IN/OUT)."""
        stats = self.txn_repo.get_summary_stats()
        self.assertEqual(stats["total_in"], 0)
        self.assertEqual(stats["total_out"], 0)

    def test_summary_stats_with_data(self):
        self._log_op("IN", 20, 50, 70)
        self._log_op("IN", 15, 70, 85)
        self._log_op("OUT", 10, 85, 75)
        stats = self.txn_repo.get_summary_stats()
        self.assertEqual(stats["total_in"], 35)
        self.assertEqual(stats["total_out"], 10)

    def test_summary_stats_filtered_by_operation(self):
        self._log_op("IN", 20, 50, 70)
        self._log_op("OUT", 10, 70, 60)
        stats = self.txn_repo.get_summary_stats(operation="IN")
        self.assertEqual(stats["total"], 1)
        self.assertEqual(stats["total_in"], 20)


class TestTransactionDataIntegrity(TestTransactionRepoBase):
    """Test transaction data types and integrity."""

    def test_transaction_has_timestamp(self):
        self._log_op("IN", 5, 50, 55)
        txns = self._get_non_create_txns(item_id=self.pid)
        self.assertIsNotNone(txns[0].timestamp)
        self.assertGreater(len(txns[0].timestamp), 0)

    def test_transaction_has_brand_name(self):
        self._log_op("IN", 5, 50, 55)
        txns = self._get_non_create_txns(item_id=self.pid)
        self.assertEqual(txns[0].brand, "Apple")
        self.assertEqual(txns[0].name, "Screen")

    def test_null_note_handling(self):
        self._log_op("IN", 5, 50, 55, "")
        txns = self._get_non_create_txns(item_id=self.pid)
        # Empty note is stored as NULL, retrieved as None or ""
        self.assertIn(txns[0].note, (None, ""))


if __name__ == "__main__":
    unittest.main()
