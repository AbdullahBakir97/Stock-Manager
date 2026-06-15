"""tests/test_schema_parity.py — guards against schema drift.

The base ``_DDL`` must already contain every column that a later migration
adds via ``ALTER TABLE``. Otherwise a database created directly from ``_DDL``
— a fresh Turso *cloud* database, or a local DB stamped straight to the current
version — is missing columns and breaks at runtime.

This is exactly the class of bug that shipped as ``no such column: cost_price``:
``cost_price`` lived only in the V16 migration, not in ``_DDL``.
"""
from __future__ import annotations

import os
import re
import sys
import sqlite3
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging; logging.disable(logging.CRITICAL)

import app.core.database as db_mod


class TestSchemaParity(unittest.TestCase):
    def test_ddl_contains_every_migration_added_column(self):
        # Build the schema from _DDL alone (the "fresh / cloud" code path).
        conn = sqlite3.connect(":memory:")
        conn.executescript(db_mod._DDL)
        ddl_tables = {
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

        # Every column any migration (or the startup column-ensure) adds via
        # ALTER TABLE ... ADD COLUMN must already exist in the base schema.
        src = open(db_mod.__file__, encoding="utf-8").read()
        adds = re.findall(r"ALTER TABLE (\w+) ADD COLUMN (\w+)", src)

        missing = []
        for table, col in sorted(set(adds)):
            if table not in ddl_tables:
                continue  # table itself is created by a migration, not _DDL
            cols = {r[1] for r in conn.execute(
                f"PRAGMA table_info({table})").fetchall()}
            if col not in cols:
                missing.append(f"{table}.{col}")
        conn.close()

        self.assertEqual(
            missing, [],
            "Base _DDL is missing migration-added column(s): "
            f"{missing}. Add them to the CREATE TABLE in _DDL so databases "
            "built directly from the schema (fresh/cloud) include them.",
        )

    def test_synced_tables_are_in_fk_dependency_order(self):
        """Every table in _SYNCED_TABLES must appear AFTER every table it
        references with a FOREIGN KEY, so push_local_to_turso() inserts parents
        before children and never hits 'FOREIGN KEY constraint failed'."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(db_mod._DDL)
        order = {name: i for i, name in enumerate(db_mod._SYNCED_TABLES)}

        problems = []
        for table in db_mod._SYNCED_TABLES:
            try:
                fks = conn.execute(
                    f"PRAGMA foreign_key_list({table})").fetchall()
            except sqlite3.OperationalError:
                continue
            for fk in fks:
                parent = fk[2]  # referenced table
                if parent in order and order[parent] > order[table]:
                    problems.append(f"{table} -> {parent} (parent pushed later)")
        conn.close()

        self.assertEqual(
            problems, [],
            "_SYNCED_TABLES violates FK dependency order: "
            + "; ".join(problems)
            + ". Move the referenced (parent) table earlier in the tuple.",
        )


if __name__ == "__main__":
    unittest.main()
