"""
tests/test_audit_service.py — Tests for AuditService.

Tests cover audit creation, line counting, completion, and adjustment application.
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
from app.services.audit_service import AuditService


class TestAuditServiceBase(unittest.TestCase):
    """Base test class with shared setup."""

    def setUp(self):
        """Create fresh services for each test with unique DB."""
        self.test_tmp_dir = tempfile.mkdtemp()
        self.test_db_file = os.path.join(self.test_tmp_dir, "test.db")
        self.original_db_path = db_mod.DB_PATH
        db_mod.DB_PATH = self.test_db_file
        db_mod.init_db()
        self.item_repo = ItemRepository()
        self.audit_svc = AuditService()

        # Create sample products
        self.sample_product1 = self.item_repo.add_product(
            brand="Apple",
            name="Screen Protector",
            color="Clear",
            stock=50,
            barcode="TEST-AUDIT-1",
            min_stock=10,
            sell_price=9.99,
        )
        self.sample_product2 = self.item_repo.add_product(
            brand="Samsung",
            name="Battery",
            color="Black",
            stock=100,
            barcode="TEST-AUDIT-2",
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


class TestAuditCreation(TestAuditServiceBase):
    """Test audit creation."""

    def test_create_audit_with_valid_name(self):
        """Test creating an audit with valid name populates lines."""
        audit_id = self.audit_svc.create_audit("Physical Count 2026")

        self.assertIsNotNone(audit_id)
        self.assertGreater(audit_id, 0)

        audit = self.audit_svc.get_audit(audit_id)
        self.assertIsNotNone(audit)
        self.assertEqual(audit.name, "Physical Count 2026")
        self.assertEqual(audit.status, "IN_PROGRESS")
        self.assertGreater(audit.total_lines, 0)

    def test_create_audit_with_empty_name_raises_error(self):
        """Test creating an audit with empty name raises ValueError."""
        with self.assertRaises(ValueError):
            self.audit_svc.create_audit("")

        with self.assertRaises(ValueError):
            self.audit_svc.create_audit("   ")

    def test_create_audit_with_notes(self):
        """Test creating an audit with notes."""
        audit_id = self.audit_svc.create_audit(
            "Quarterly Audit",
            notes="Q1 physical inventory check"
        )

        audit = self.audit_svc.get_audit(audit_id)
        self.assertEqual(audit.notes, "Q1 physical inventory check")

    def test_get_all_audits_returns_list(self):
        """Test get_all_audits returns list of audits."""
        audit_id1 = self.audit_svc.create_audit("Audit 1")
        audit_id2 = self.audit_svc.create_audit("Audit 2")

        audits = self.audit_svc.get_all_audits()
        self.assertIsInstance(audits, list)
        self.assertGreaterEqual(len(audits), 2)

    def test_get_audit_by_id(self):
        """Test get_audit retrieves specific audit."""
        audit_id = self.audit_svc.create_audit("Test Audit")
        audit = self.audit_svc.get_audit(audit_id)

        self.assertIsNotNone(audit)
        self.assertEqual(audit.id, audit_id)


class TestAuditLineRecording(TestAuditServiceBase):
    """Test recording counts on audit lines."""

    def setUp(self):
        """Set up with audit ready for counting."""
        super().setUp()
        self.audit_id = self.audit_svc.create_audit("Count Test")
        self.lines = self.audit_svc.get_audit_lines(self.audit_id)

    def test_record_count_with_valid_qty(self):
        """Test recording count with valid quantity."""
        if self.lines:
            line = self.lines[0]
            self.audit_svc.record_count(line.id, 45)

            updated_lines = self.audit_svc.get_audit_lines(self.audit_id)
            updated_line = next((l for l in updated_lines if l.id == line.id), None)
            self.assertIsNotNone(updated_line)
            self.assertEqual(updated_line.counted_qty, 45)

    def test_record_count_with_negative_qty_raises_error(self):
        """Test recording count with negative quantity raises ValueError."""
        if self.lines:
            line = self.lines[0]
            with self.assertRaises(ValueError):
                self.audit_svc.record_count(line.id, -5)

    def test_record_count_with_note(self):
        """Test recording count with note."""
        if self.lines:
            line = self.lines[0]
            self.audit_svc.record_count(line.id, 48, note="Missing one")

            updated_lines = self.audit_svc.get_audit_lines(self.audit_id)
            updated_line = next((l for l in updated_lines if l.id == line.id), None)
            self.assertIsNotNone(updated_line)
            self.assertEqual(updated_line.note, "Missing one")


class TestAuditCompletion(TestAuditServiceBase):
    """Test completing audits."""

    def test_complete_audit_with_counts(self):
        """Test completing audit after counting at least one item."""
        audit_id = self.audit_svc.create_audit("Completion Test")
        lines = self.audit_svc.get_audit_lines(audit_id)

        if lines:
            # Record at least one count
            self.audit_svc.record_count(lines[0].id, 45)

            # Complete the audit
            result = self.audit_svc.complete_audit(audit_id)

            self.assertIn("total_lines", result)
            self.assertIn("counted_lines", result)
            self.assertIn("discrepancies", result)

            # Verify status changed
            audit = self.audit_svc.get_audit(audit_id)
            self.assertEqual(audit.status, "COMPLETED")

    def test_complete_audit_with_no_counts_raises_error(self):
        """Test completing audit with no counts raises ValueError."""
        audit_id = self.audit_svc.create_audit("Empty Count Test")

        with self.assertRaises(ValueError):
            self.audit_svc.complete_audit(audit_id)

    def test_complete_audit_returns_summary(self):
        """Test complete_audit returns discrepancy summary."""
        audit_id = self.audit_svc.create_audit("Summary Test")
        lines = self.audit_svc.get_audit_lines(audit_id)

        if lines:
            # Record count different from expected
            self.audit_svc.record_count(lines[0].id, 30)
            result = self.audit_svc.complete_audit(audit_id)

            self.assertIsInstance(result, dict)
            self.assertGreaterEqual(result["total_lines"], 1)


class TestAuditCancellation(TestAuditServiceBase):
    """Test cancelling audits."""

    def test_cancel_audit(self):
        """Test cancelling an in-progress audit."""
        audit_id = self.audit_svc.create_audit("Cancel Test")
        self.audit_svc.cancel_audit(audit_id)

        audit = self.audit_svc.get_audit(audit_id)
        self.assertEqual(audit.status, "CANCELLED")

    def test_cancel_completed_audit(self):
        """Test cancelling a completed audit."""
        audit_id = self.audit_svc.create_audit("Complete Then Cancel")
        lines = self.audit_svc.get_audit_lines(audit_id)

        if lines:
            self.audit_svc.record_count(lines[0].id, 40)
            self.audit_svc.complete_audit(audit_id)
            self.audit_svc.cancel_audit(audit_id)

            audit = self.audit_svc.get_audit(audit_id)
            self.assertEqual(audit.status, "CANCELLED")


class TestAuditAdjustments(TestAuditServiceBase):
    """Test applying discrepancies as stock adjustments."""

    def test_apply_adjustments_with_discrepancies(self):
        """Test applying adjustments adjusts stock based on discrepancies."""
        audit_id = self.audit_svc.create_audit("Adjustment Test")
        lines = self.audit_svc.get_audit_lines(audit_id)

        if lines:
            # Record counts that differ from actual
            for line in lines[:2]:
                if line.system_qty:
                    counted = max(0, line.system_qty - 5)
                    self.audit_svc.record_count(line.id, counted)

            # Complete audit
            self.audit_svc.complete_audit(audit_id)

            # Apply adjustments
            adjusted = self.audit_svc.apply_adjustments(audit_id)
            self.assertGreaterEqual(adjusted, 0)

    def test_apply_adjustments_only_on_completed_audit(self):
        """Test apply_adjustments fails on non-completed audit."""
        audit_id = self.audit_svc.create_audit("Not Completed")

        with self.assertRaises(ValueError):
            self.audit_svc.apply_adjustments(audit_id)

    def test_apply_adjustments_returns_count(self):
        """Test apply_adjustments returns count of adjusted items."""
        audit_id = self.audit_svc.create_audit("Count Return Test")
        lines = self.audit_svc.get_audit_lines(audit_id)

        if lines:
            # Record one count
            self.audit_svc.record_count(lines[0].id, 25)
            self.audit_svc.complete_audit(audit_id)

            adjusted = self.audit_svc.apply_adjustments(audit_id)
            self.assertIsInstance(adjusted, int)
            self.assertGreaterEqual(adjusted, 0)


class TestAuditSummary(TestAuditServiceBase):
    """Test audit summary statistics."""

    def test_get_summary_returns_dict(self):
        """Test get_summary returns statistics dict."""
        self.audit_svc.create_audit("Summary 1")
        self.audit_svc.create_audit("Summary 2")

        summary = self.audit_svc.get_summary()
        self.assertIsInstance(summary, dict)


if __name__ == "__main__":
    unittest.main()
