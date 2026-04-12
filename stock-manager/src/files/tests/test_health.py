"""
tests/test_health.py — Tests for database health check module.

Tests cover health report generation and integrity validation.
"""
from __future__ import annotations

import unittest
import tempfile
import os
import sys
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.core.database as db_mod
from app.core.health import check_database_health, run_startup_checks


class TestHealthCheckBase(unittest.TestCase):
    """Base class with isolated DB setup."""

    def setUp(self):
        self.test_tmp_dir = tempfile.mkdtemp()
        self.test_db_file = os.path.join(self.test_tmp_dir, "test.db")
        self.original_db_path = db_mod.DB_PATH
        db_mod.DB_PATH = self.test_db_file
        db_mod.init_db()

    def tearDown(self):
        db_mod.DB_PATH = self.original_db_path
        try:
            shutil.rmtree(self.test_tmp_dir)
        except Exception:
            pass


class TestHealthyDatabase(TestHealthCheckBase):
    """Test health check on a properly initialized database."""

    def test_report_ok(self):
        report = check_database_health()
        self.assertTrue(report.ok)

    def test_db_exists(self):
        report = check_database_health()
        self.assertTrue(report.db_exists)

    def test_integrity_ok(self):
        report = check_database_health()
        self.assertTrue(report.integrity_ok)

    def test_foreign_key_ok(self):
        report = check_database_health()
        self.assertTrue(report.foreign_key_ok)

    def test_no_missing_tables(self):
        report = check_database_health()
        self.assertEqual(len(report.missing_tables), 0)

    def test_schema_version_positive(self):
        report = check_database_health()
        self.assertGreater(report.schema_version, 0)

    def test_table_count_positive(self):
        report = check_database_health()
        self.assertGreater(report.table_count, 0)

    def test_db_size_positive(self):
        report = check_database_health()
        self.assertGreater(report.db_size_bytes, 0)

    def test_no_errors(self):
        report = check_database_health()
        self.assertEqual(len(report.errors), 0)

    def test_summary_string(self):
        report = check_database_health()
        self.assertIn("Healthy", report.summary)


class TestCorruptDatabase(TestHealthCheckBase):
    """Test health check with a corrupt/empty database."""

    def test_empty_file_reports_failure(self):
        """An empty file (not a real SQLite DB) should fail health checks."""
        empty_db = os.path.join(self.test_tmp_dir, "empty.db")
        with open(empty_db, "w") as f:
            f.write("")  # 0-byte file
        db_mod.DB_PATH = empty_db
        report = check_database_health()
        self.assertFalse(report.ok)
        self.assertGreater(len(report.errors), 0)

    def test_non_sqlite_file(self):
        """A non-SQLite file should fail health checks."""
        bad_db = os.path.join(self.test_tmp_dir, "bad.db")
        with open(bad_db, "w") as f:
            f.write("this is not a database")
        db_mod.DB_PATH = bad_db
        report = check_database_health()
        self.assertFalse(report.ok)


class TestStartupChecks(TestHealthCheckBase):
    """Test the run_startup_checks wrapper."""

    def test_startup_checks_returns_report(self):
        report = run_startup_checks()
        self.assertTrue(report.ok)

    def test_startup_checks_on_healthy_db(self):
        report = run_startup_checks()
        self.assertEqual(len(report.errors), 0)


if __name__ == "__main__":
    unittest.main()
