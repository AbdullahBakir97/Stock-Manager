"""
tests/conftest.py — Shared fixtures and utilities for Stock Manager Pro tests.

This module provides setup/teardown utilities for tests.
Note: This uses unittest patterns instead of pytest due to environment constraints.
"""
from __future__ import annotations

import sys
import os
import sqlite3
import tempfile
import shutil

# Add src/files to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBase:
    """Base class for test setup and teardown."""

    @classmethod
    def setup_test_db(cls, tmp_path):
        """Create an in-memory SQLite database with the full schema."""
        cls.tmp_db_dir = tmp_path
        db_file = os.path.join(tmp_path, "test.db")

        import app.core.database as db_mod
        original_db_path = db_mod.DB_PATH
        db_mod.DB_PATH = db_file

        # Initialize schema
        db_mod.init_db()

        cls.db_file = db_file
        cls.original_db_path = original_db_path
        return db_file

    @classmethod
    def teardown_test_db(cls, db_mod):
        """Clean up test database."""
        db_mod.DB_PATH = cls.original_db_path
        if os.path.exists(cls.db_file):
            try:
                os.remove(cls.db_file)
            except:
                pass


def create_sample_product(item_repo):
    """Create a sample product and return its ID."""
    pid = item_repo.add_product(
        brand="Apple",
        name="Screen Protector",
        color="Clear",
        stock=50,
        barcode="TEST-001",
        min_stock=10,
        sell_price=9.99,
    )
    return pid


def create_sample_product_low_stock(item_repo):
    """Create a product with low stock alert."""
    pid = item_repo.add_product(
        brand="Samsung",
        name="Battery",
        color="Black",
        stock=5,
        barcode="TEST-LOW-001",
        min_stock=10,
        sell_price=25.99,
    )
    return pid
