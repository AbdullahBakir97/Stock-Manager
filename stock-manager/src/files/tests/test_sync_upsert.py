"""tests/test_sync_upsert.py — the cloud push must be non-destructive.

Guards the fix for the "phones disappeared after sync" incident: the push now
UPSERTs by primary key instead of DROP + recreate, so a push from a PC that
holds less data can never wipe rows that exist only in the cloud.

Runs standalone (`python tests/test_sync_upsert.py`) and under pytest.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import (  # noqa: E402
    _build_upsert_sql, _table_pk_columns, delete_inventory_where_safe,
)


def _mk() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE phones(id INTEGER PRIMARY KEY, imei TEXT, status TEXT)")
    return c


class TestUpsert(unittest.TestCase):
    def test_pk_detection(self):
        c = _mk()
        self.assertEqual(_table_pk_columns(c, "phones"), ["id"])

    def test_build_sql_shapes(self):
        sql = _build_upsert_sql("phones", ["id", "imei", "status"], ["id"])
        self.assertIn("ON CONFLICT(id) DO UPDATE SET", sql)
        self.assertIn("imei=excluded.imei", sql)
        self.assertNotIn("id=excluded.id", sql)  # PK cols are never in SET
        # keyless fallback
        self.assertIn("INSERT OR IGNORE",
                      _build_upsert_sql("t", ["a", "b"], []))
        # all-PK table -> DO NOTHING
        self.assertIn("DO NOTHING",
                      _build_upsert_sql("j", ["a", "b"], ["a", "b"]))

    def test_push_is_non_destructive(self):
        """Local push must: insert new, update matching, KEEP cloud-only rows."""
        local, remote = _mk(), _mk()
        local.executemany("INSERT INTO phones VALUES(?,?,?)", [
            (1, "A", "in_stock"), (2, "B", "in_stock"), (3, "C", "sold")])
        remote.executemany("INSERT INTO phones VALUES(?,?,?)", [
            (1, "A", "in_stock"), (3, "C-OLD", "in_stock"), (99, "CLOUD", "in_stock")])
        local.commit(); remote.commit()

        cols = ["id", "imei", "status"]
        sql = _build_upsert_sql("phones", cols, _table_pk_columns(local, "phones"))
        rows = local.execute("SELECT * FROM phones").fetchall()
        remote.executemany(sql, [tuple(r[c] for c in cols) for r in rows])
        remote.commit()

        after = {r["id"]: (r["imei"], r["status"])
                 for r in remote.execute("SELECT * FROM phones")}
        self.assertEqual(after[2], ("B", "in_stock"))          # inserted
        self.assertEqual(after[3], ("C", "sold"))              # updated in place
        self.assertEqual(after[99], ("CLOUD", "in_stock"))     # cloud-only KEPT
        self.assertEqual(len(after), 4)                        # nothing deleted


class TestFkSafeDelete(unittest.TestCase):
    """delete_inventory_where_safe must never crash on a referenced row.

    Guards the "FOREIGN KEY constraint failed" crash when saving colours /
    pruning the matrix in cloud mode (Turso enforces FKs; SQLite doesn't by
    default). Referenced rows are kept; unreferenced ones are deleted.
    """

    def _db(self):
        c = sqlite3.connect(":memory:")
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("CREATE TABLE inventory_items(id INTEGER PRIMARY KEY, stock INT DEFAULT 0)")
        c.execute("CREATE TABLE sale_items(id INTEGER PRIMARY KEY, "
                  "item_id INT REFERENCES inventory_items(id))")
        c.executemany("INSERT INTO inventory_items(id,stock) VALUES(?,0)", [(1,), (2,), (3,)])
        c.execute("INSERT INTO sale_items(item_id) VALUES(2)")  # item 2 referenced
        c.commit()
        return c

    def test_bulk_delete_skips_referenced(self):
        c = self._db()
        delete_inventory_where_safe(c, "stock=0", ())
        remaining = [r["id"] for r in c.execute("SELECT id FROM inventory_items ORDER BY id")]
        self.assertEqual(remaining, [2])  # referenced kept, others deleted

    def test_no_reference_deletes_all(self):
        c = self._db()
        c.execute("DELETE FROM sale_items")  # drop the only reference
        c.commit()
        delete_inventory_where_safe(c, "stock=0", ())
        remaining = [r["id"] for r in c.execute("SELECT id FROM inventory_items")]
        self.assertEqual(remaining, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
