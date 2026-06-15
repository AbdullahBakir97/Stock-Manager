"""tests/test_embedded_replica.py — real round-trip test for the libSQL
embedded-replica connection wrapper.

This is the gate that verifies the cloud-sync data layer actually works before
a release, since it can't be tested on the dev machine (no Python-3.14 wheel).
It runs in CI (Python 3.11) against a THROWAWAY Turso database supplied via the
secrets TURSO_TEST_URL / TURSO_TEST_TOKEN; it skips cleanly when those are
absent (forks, local runs) so it never produces a false failure.

It exercises exactly the integration risks:
  * connect to an embedded replica (local file + sync_url + token),
  * write through to the primary + commit + sync() the change down,
  * read it back from the local replica,
  * dict-style row access (row["col"]) that every repository relies on,
  * executemany.
"""
from __future__ import annotations

import os
import sys
import uuid
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging; logging.disable(logging.CRITICAL)

_URL = os.environ.get("TURSO_TEST_URL")
_TOKEN = os.environ.get("TURSO_TEST_TOKEN")


@unittest.skipUnless(
    _URL and _TOKEN,
    "TURSO_TEST_URL / TURSO_TEST_TOKEN not set — skipping cloud round-trip",
)
class TestEmbeddedReplicaRoundTrip(unittest.TestCase):

    def test_write_sync_read(self):
        import app.core.database as db
        if not db.libsql_available():
            self.skipTest("libsql not installed in this environment")

        tmp = tempfile.mkdtemp()
        replica = os.path.join(tmp, "replica.db")
        table = "ci_test_" + uuid.uuid4().hex[:10]
        conn = db._LibsqlReplicaConnection(replica, _URL, _TOKEN)
        try:
            with conn:
                conn.execute(
                    f"CREATE TABLE IF NOT EXISTS {table} "
                    f"(id INTEGER PRIMARY KEY, name TEXT, qty INTEGER)"
                )
            with conn:
                conn.execute(
                    f"INSERT INTO {table} (name, qty) VALUES (?, ?)", ("widget", 7)
                )
            conn.sync()

            # Read back from the local replica — dict-style access must work.
            row = conn.execute(
                f"SELECT name, qty FROM {table} WHERE name = ?", ("widget",)
            ).fetchone()
            self.assertIsNotNone(row, "row missing after insert + sync")
            self.assertEqual(row["name"], "widget")
            self.assertEqual(row["qty"], 7)

            # executemany + aggregate read.
            with conn:
                conn.executemany(
                    f"INSERT INTO {table} (name, qty) VALUES (?, ?)",
                    [("a", 1), ("b", 2), ("c", 3)],
                )
            conn.sync()
            n = conn.execute(
                f"SELECT COUNT(*) AS n FROM {table}"
            ).fetchone()["n"]
            self.assertGreaterEqual(n, 4)
        finally:
            try:
                with conn:
                    conn.execute(f"DROP TABLE IF EXISTS {table}")
            except Exception:
                pass
            conn.close()
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
