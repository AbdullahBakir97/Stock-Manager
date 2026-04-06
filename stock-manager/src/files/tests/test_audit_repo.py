"""
tests/test_audit_repo.py — Tests for AuditRepository.

Tests cover create, get_by_id, get_all, update_status, delete, add_line,
get_lines, update_line_count, populate_from_inventory, and get_summary.
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
from app.repositories.audit_repo import AuditRepository
from app.repositories.item_repo import ItemRepository


class TestAuditRepositoryBase(unittest.TestCase):
    """Base test class with shared setup."""

    def setUp(self):
        """Create fresh AuditRepository with unique DB."""
        self.test_tmp_dir = tempfile.mkdtemp()
        self.test_db_file = os.path.join(self.test_tmp_dir, "test.db")
        self.original_db_path = db_mod.DB_PATH
        db_mod.DB_PATH = self.test_db_file
        db_mod.init_db()
        self.audit_repo = AuditRepository()
        self.item_repo = ItemRepository()

        # Create sample products for testing
        self.sample_product_1 = self.item_repo.add_product(
            brand="Apple",
            name="Screen Protector",
            color="Clear",
            stock=50,
            barcode="TEST-AUDIT-1",
            min_stock=10,
            sell_price=9.99,
        )
        self.sample_product_2 = self.item_repo.add_product(
            brand="Samsung",
            name="Phone Case",
            color="Black",
            stock=30,
            barcode="TEST-AUDIT-2",
            min_stock=5,
            sell_price=14.99,
        )

    def tearDown(self):
        """Clean up test database."""
        db_mod.DB_PATH = self.original_db_path
        try:
            shutil.rmtree(self.test_tmp_dir)
        except:
            pass


class TestAuditCreate(TestAuditRepositoryBase):
    """Test audit creation."""

    def test_create_returns_audit_id(self):
        """Test create() returns a valid audit ID."""
        audit_id = self.audit_repo.create("Monthly Stock Check", "Regular inventory audit")

        self.assertIsInstance(audit_id, int)
        self.assertGreater(audit_id, 0)

    def test_create_sets_status_in_progress(self):
        """Test create() sets status to IN_PROGRESS."""
        audit_id = self.audit_repo.create("Test Audit")
        audit = self.audit_repo.get_by_id(audit_id)

        self.assertEqual(audit.status, "IN_PROGRESS")

    def test_create_stores_name_and_notes(self):
        """Test create() stores name and notes."""
        name = "Quarterly Audit"
        notes = "Year-end inventory check"
        audit_id = self.audit_repo.create(name, notes)
        audit = self.audit_repo.get_by_id(audit_id)

        self.assertEqual(audit.name, name)
        self.assertEqual(audit.notes, notes)

    def test_create_sets_started_at_timestamp(self):
        """Test create() sets started_at timestamp."""
        audit_id = self.audit_repo.create("Test Audit")
        audit = self.audit_repo.get_by_id(audit_id)

        self.assertIsNotNone(audit.started_at)
        self.assertGreater(len(audit.started_at), 0)


class TestAuditGetById(TestAuditRepositoryBase):
    """Test audit retrieval by ID."""

    def test_get_by_id_returns_audit(self):
        """Test get_by_id() returns correct audit."""
        audit_id = self.audit_repo.create("Test Audit")
        audit = self.audit_repo.get_by_id(audit_id)

        self.assertIsNotNone(audit)
        self.assertEqual(audit.id, audit_id)
        self.assertEqual(audit.name, "Test Audit")

    def test_get_by_id_returns_none_for_nonexistent(self):
        """Test get_by_id() returns None for non-existent audit."""
        audit = self.audit_repo.get_by_id(9999)

        self.assertIsNone(audit)

    def test_get_by_id_returns_computed_counts(self):
        """Test get_by_id() returns computed total_lines, counted_lines, discrepancies."""
        audit_id = self.audit_repo.create("Test Audit")
        self.audit_repo.add_line(audit_id, self.sample_product_1, 50)
        self.audit_repo.add_line(audit_id, self.sample_product_2, 30)

        audit = self.audit_repo.get_by_id(audit_id)

        self.assertEqual(audit.total_lines, 2)
        self.assertEqual(audit.counted_lines, 0)
        self.assertEqual(audit.discrepancies, 0)


class TestAuditGetAll(TestAuditRepositoryBase):
    """Test get_all() method."""

    def test_get_all_returns_list(self):
        """Test get_all() returns a list."""
        result = self.audit_repo.get_all()

        self.assertIsInstance(result, list)

    def test_get_all_returns_empty_on_no_audits(self):
        """Test get_all() returns empty list when no audits exist."""
        result = self.audit_repo.get_all()

        self.assertEqual(len(result), 0)

    def test_get_all_returns_all_audits(self):
        """Test get_all() returns all audits."""
        self.audit_repo.create("Audit 1")
        self.audit_repo.create("Audit 2")
        self.audit_repo.create("Audit 3")

        result = self.audit_repo.get_all()

        self.assertEqual(len(result), 3)

    def test_get_all_returns_audits_with_computed_counts(self):
        """Test get_all() returns audits with computed counts."""
        audit_id = self.audit_repo.create("Test Audit")
        self.audit_repo.add_line(audit_id, self.sample_product_1, 50)

        result = self.audit_repo.get_all()

        self.assertGreater(len(result), 0)
        self.assertEqual(result[0].total_lines, 1)


class TestAuditUpdateStatus(TestAuditRepositoryBase):
    """Test update_status() method."""

    def test_update_status_changes_status(self):
        """Test update_status() changes the status."""
        audit_id = self.audit_repo.create("Test Audit")
        self.audit_repo.update_status(audit_id, "CANCELLED")
        audit = self.audit_repo.get_by_id(audit_id)

        self.assertEqual(audit.status, "CANCELLED")

    def test_update_status_completed_sets_completed_at(self):
        """Test update_status() with COMPLETED sets completed_at timestamp."""
        audit_id = self.audit_repo.create("Test Audit")
        self.audit_repo.update_status(audit_id, "COMPLETED")
        audit = self.audit_repo.get_by_id(audit_id)

        self.assertEqual(audit.status, "COMPLETED")
        self.assertIsNotNone(audit.completed_at)
        self.assertGreater(len(audit.completed_at), 0)

    def test_update_status_uses_provided_completed_at(self):
        """Test update_status() uses provided completed_at timestamp."""
        audit_id = self.audit_repo.create("Test Audit")
        custom_time = "2026-04-06T12:00:00"
        self.audit_repo.update_status(audit_id, "COMPLETED", custom_time)
        audit = self.audit_repo.get_by_id(audit_id)

        self.assertEqual(audit.completed_at, custom_time)


class TestAuditDelete(TestAuditRepositoryBase):
    """Test delete() method."""

    def test_delete_removes_audit(self):
        """Test delete() removes an audit."""
        audit_id = self.audit_repo.create("Test Audit")
        self.audit_repo.delete(audit_id)
        audit = self.audit_repo.get_by_id(audit_id)

        self.assertIsNone(audit)

    def test_delete_removes_audit_lines(self):
        """Test delete() also removes associated lines."""
        audit_id = self.audit_repo.create("Test Audit")
        self.audit_repo.add_line(audit_id, self.sample_product_1, 50)
        self.audit_repo.add_line(audit_id, self.sample_product_2, 30)

        self.audit_repo.delete(audit_id)
        lines = self.audit_repo.get_lines(audit_id)

        self.assertEqual(len(lines), 0)

    def test_delete_only_removes_specific_audit(self):
        """Test delete() only removes the specified audit."""
        audit_id_1 = self.audit_repo.create("Audit 1")
        audit_id_2 = self.audit_repo.create("Audit 2")

        self.audit_repo.delete(audit_id_1)

        audit = self.audit_repo.get_by_id(audit_id_2)
        self.assertIsNotNone(audit)


class TestAuditAddLine(TestAuditRepositoryBase):
    """Test add_line() method."""

    def test_add_line_returns_line_id(self):
        """Test add_line() returns a valid line ID."""
        audit_id = self.audit_repo.create("Test Audit")
        line_id = self.audit_repo.add_line(audit_id, self.sample_product_1, 50)

        self.assertIsInstance(line_id, int)
        self.assertGreater(line_id, 0)

    def test_add_line_stores_system_qty(self):
        """Test add_line() stores system_qty correctly."""
        audit_id = self.audit_repo.create("Test Audit")
        line_id = self.audit_repo.add_line(audit_id, self.sample_product_1, 50)
        lines = self.audit_repo.get_lines(audit_id)

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].system_qty, 50)

    def test_add_line_initializes_counted_qty_as_none(self):
        """Test add_line() initializes counted_qty as None."""
        audit_id = self.audit_repo.create("Test Audit")
        line_id = self.audit_repo.add_line(audit_id, self.sample_product_1, 50)
        lines = self.audit_repo.get_lines(audit_id)

        self.assertIsNone(lines[0].counted_qty)


class TestAuditGetLines(TestAuditRepositoryBase):
    """Test get_lines() method."""

    def test_get_lines_returns_list(self):
        """Test get_lines() returns a list."""
        audit_id = self.audit_repo.create("Test Audit")
        lines = self.audit_repo.get_lines(audit_id)

        self.assertIsInstance(lines, list)

    def test_get_lines_returns_empty_for_new_audit(self):
        """Test get_lines() returns empty list for new audit with no lines."""
        audit_id = self.audit_repo.create("Test Audit")
        lines = self.audit_repo.get_lines(audit_id)

        self.assertEqual(len(lines), 0)

    def test_get_lines_returns_all_lines(self):
        """Test get_lines() returns all lines for an audit."""
        audit_id = self.audit_repo.create("Test Audit")
        self.audit_repo.add_line(audit_id, self.sample_product_1, 50)
        self.audit_repo.add_line(audit_id, self.sample_product_2, 30)

        lines = self.audit_repo.get_lines(audit_id)

        self.assertEqual(len(lines), 2)

    def test_get_lines_includes_item_details(self):
        """Test get_lines() includes item_name and barcode from inventory_items."""
        audit_id = self.audit_repo.create("Test Audit")
        self.audit_repo.add_line(audit_id, self.sample_product_1, 50)

        lines = self.audit_repo.get_lines(audit_id)

        self.assertEqual(len(lines), 1)
        self.assertGreater(len(lines[0].item_name), 0)
        self.assertEqual(lines[0].barcode, "TEST-AUDIT-1")


class TestAuditUpdateLineCount(TestAuditRepositoryBase):
    """Test update_line_count() method."""

    def test_update_line_count_sets_counted_qty(self):
        """Test update_line_count() sets counted_qty."""
        audit_id = self.audit_repo.create("Test Audit")
        line_id = self.audit_repo.add_line(audit_id, self.sample_product_1, 50)

        self.audit_repo.update_line_count(line_id, 48)
        lines = self.audit_repo.get_lines(audit_id)

        self.assertEqual(lines[0].counted_qty, 48)

    def test_update_line_count_computes_difference_correctly(self):
        """Test update_line_count() computes difference as counted - system."""
        audit_id = self.audit_repo.create("Test Audit")
        line_id = self.audit_repo.add_line(audit_id, self.sample_product_1, 50)

        self.audit_repo.update_line_count(line_id, 45)
        lines = self.audit_repo.get_lines(audit_id)

        self.assertEqual(lines[0].difference, -5)

    def test_update_line_count_positive_difference(self):
        """Test update_line_count() computes positive difference correctly."""
        audit_id = self.audit_repo.create("Test Audit")
        line_id = self.audit_repo.add_line(audit_id, self.sample_product_1, 50)

        self.audit_repo.update_line_count(line_id, 52)
        lines = self.audit_repo.get_lines(audit_id)

        self.assertEqual(lines[0].difference, 2)

    def test_update_line_count_zero_difference(self):
        """Test update_line_count() computes zero difference when counts match."""
        audit_id = self.audit_repo.create("Test Audit")
        line_id = self.audit_repo.add_line(audit_id, self.sample_product_1, 50)

        self.audit_repo.update_line_count(line_id, 50)
        lines = self.audit_repo.get_lines(audit_id)

        self.assertEqual(lines[0].difference, 0)

    def test_update_line_count_stores_note(self):
        """Test update_line_count() stores optional note."""
        audit_id = self.audit_repo.create("Test Audit")
        line_id = self.audit_repo.add_line(audit_id, self.sample_product_1, 50)

        self.audit_repo.update_line_count(line_id, 48, "Damaged items excluded")
        lines = self.audit_repo.get_lines(audit_id)

        self.assertEqual(lines[0].note, "Damaged items excluded")


class TestAuditPopulateFromInventory(TestAuditRepositoryBase):
    """Test populate_from_inventory() method."""

    def test_populate_from_inventory_returns_count(self):
        """Test populate_from_inventory() returns count of inserted lines."""
        audit_id = self.audit_repo.create("Test Audit")
        count = self.audit_repo.populate_from_inventory(audit_id)

        self.assertIsInstance(count, int)
        self.assertGreater(count, 0)

    def test_populate_from_inventory_adds_all_items(self):
        """Test populate_from_inventory() adds all inventory items as lines."""
        audit_id = self.audit_repo.create("Test Audit")
        count = self.audit_repo.populate_from_inventory(audit_id)
        lines = self.audit_repo.get_lines(audit_id)

        self.assertEqual(len(lines), count)
        self.assertEqual(count, 2)  # We created 2 sample products

    def test_populate_from_inventory_sets_system_qty_correctly(self):
        """Test populate_from_inventory() sets system_qty from current_qty."""
        audit_id = self.audit_repo.create("Test Audit")
        self.audit_repo.populate_from_inventory(audit_id)
        lines = self.audit_repo.get_lines(audit_id)

        # Lines should be sorted by name
        self.assertEqual(lines[0].system_qty, 30)  # Samsung case (stock=30)
        self.assertEqual(lines[1].system_qty, 50)  # Apple protector (stock=50)

    def test_populate_from_inventory_initializes_counted_qty_none(self):
        """Test populate_from_inventory() initializes all counted_qty as None."""
        audit_id = self.audit_repo.create("Test Audit")
        self.audit_repo.populate_from_inventory(audit_id)
        lines = self.audit_repo.get_lines(audit_id)

        for line in lines:
            self.assertIsNone(line.counted_qty)


class TestAuditGetSummary(TestAuditRepositoryBase):
    """Test get_summary() method."""

    def test_get_summary_returns_dict(self):
        """Test get_summary() returns a dictionary."""
        summary = self.audit_repo.get_summary()

        self.assertIsInstance(summary, dict)

    def test_get_summary_counts_all_audits(self):
        """Test get_summary() counts all audits."""
        self.audit_repo.create("Audit 1")
        self.audit_repo.create("Audit 2")

        summary = self.audit_repo.get_summary()

        self.assertEqual(summary["total_audits"], 2)

    def test_get_summary_counts_in_progress_audits(self):
        """Test get_summary() counts IN_PROGRESS audits."""
        audit_id_1 = self.audit_repo.create("Audit 1")
        audit_id_2 = self.audit_repo.create("Audit 2")
        self.audit_repo.update_status(audit_id_1, "COMPLETED")

        summary = self.audit_repo.get_summary()

        self.assertEqual(summary["in_progress"], 1)
        self.assertEqual(summary["completed"], 1)

    def test_get_summary_counts_completed_audits(self):
        """Test get_summary() counts COMPLETED audits."""
        audit_id = self.audit_repo.create("Test Audit")
        self.audit_repo.update_status(audit_id, "COMPLETED")

        summary = self.audit_repo.get_summary()

        self.assertEqual(summary["completed"], 1)

    def test_get_summary_counts_cancelled_audits(self):
        """Test get_summary() counts CANCELLED audits."""
        audit_id = self.audit_repo.create("Test Audit")
        self.audit_repo.update_status(audit_id, "CANCELLED")

        summary = self.audit_repo.get_summary()

        self.assertEqual(summary["cancelled"], 1)

    def test_get_summary_counts_discrepancies(self):
        """Test get_summary() counts total discrepancies."""
        audit_id = self.audit_repo.create("Test Audit")
        line_id_1 = self.audit_repo.add_line(audit_id, self.sample_product_1, 50)
        line_id_2 = self.audit_repo.add_line(audit_id, self.sample_product_2, 30)

        # Create one discrepancy
        self.audit_repo.update_line_count(line_id_1, 45)
        # Create no discrepancy
        self.audit_repo.update_line_count(line_id_2, 30)

        summary = self.audit_repo.get_summary()

        self.assertEqual(summary["total_discrepancies"], 1)

    def test_get_summary_empty_when_no_audits(self):
        """Test get_summary() returns zeros when no audits exist."""
        summary = self.audit_repo.get_summary()

        self.assertEqual(summary["total_audits"], 0)
        self.assertEqual(summary["in_progress"], 0)
        self.assertEqual(summary["completed"], 0)
        self.assertEqual(summary["cancelled"], 0)
        self.assertEqual(summary["total_discrepancies"], 0)


if __name__ == "__main__":
    unittest.main()
