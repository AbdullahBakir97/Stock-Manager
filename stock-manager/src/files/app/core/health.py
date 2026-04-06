"""
app/core/health.py — Database integrity checks and startup health validation.

Provides pre-flight checks to ensure the database is intact before
the application proceeds with normal operations.
"""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from typing import Optional

from app.core.database import get_connection, DB_PATH
from app.core.logger import get_logger

_log = get_logger(__name__)


# ── Health check result ──────────────────────────────────────────────────────

@dataclass
class HealthReport:
    """Result of a database health check."""
    ok: bool
    db_exists: bool
    db_size_bytes: int
    schema_version: int
    integrity_ok: bool
    foreign_key_ok: bool
    table_count: int
    missing_tables: list[str]
    warnings: list[str]
    errors: list[str]

    @property
    def summary(self) -> str:
        if self.ok:
            return f"Healthy — v{self.schema_version}, {self.table_count} tables, {self.db_size_bytes:,} bytes"
        return f"UNHEALTHY — {len(self.errors)} error(s): {'; '.join(self.errors)}"


# ── Required tables ──────────────────────────────────────────────────────────

_REQUIRED_TABLES = [
    "app_config",
    "categories",
    "part_types",
    "phone_models",
    "inventory_items",
    "inventory_transactions",
]


# ── Main check ───────────────────────────────────────────────────────────────

def check_database_health() -> HealthReport:
    """
    Run a comprehensive health check on the application database.

    Checks:
      1. Database file exists and is non-zero size
      2. SQLite integrity_check passes
      3. No foreign key violations
      4. All required tables exist
      5. Schema version is present and valid
    """
    warnings: list[str] = []
    errors: list[str] = []

    # ── File check ───────────────────────────────────────────────────────────
    db_exists = os.path.isfile(DB_PATH)
    db_size = os.path.getsize(DB_PATH) if db_exists else 0

    if not db_exists:
        _log.warning("Health check: database file does not exist")
        return HealthReport(
            ok=False, db_exists=False, db_size_bytes=0,
            schema_version=0, integrity_ok=False, foreign_key_ok=False,
            table_count=0, missing_tables=list(_REQUIRED_TABLES),
            warnings=warnings, errors=["Database file not found"],
        )

    if db_size == 0:
        errors.append("Database file is empty (0 bytes)")

    # ── SQLite checks ────────────────────────────────────────────────────────
    integrity_ok = True
    foreign_key_ok = True
    schema_version = 0
    table_count = 0
    missing_tables: list[str] = []

    try:
        conn = get_connection()

        # Integrity check
        try:
            result = conn.execute("PRAGMA integrity_check").fetchone()[0]
            if result != "ok":
                integrity_ok = False
                errors.append(f"SQLite integrity check failed: {result}")
                _log.error(f"Health check: integrity_check returned '{result}'")
        except Exception as e:
            integrity_ok = False
            errors.append(f"Integrity check error: {e}")

        # Foreign key check
        try:
            violations = conn.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                foreign_key_ok = False
                warnings.append(f"{len(violations)} foreign key violation(s)")
                _log.warning(f"Health check: {len(violations)} FK violations")
        except Exception as e:
            foreign_key_ok = False
            warnings.append(f"FK check error: {e}")

        # Table check
        try:
            tables_rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            existing_tables = {r["name"] for r in tables_rows}
            table_count = len(existing_tables)
            missing_tables = [t for t in _REQUIRED_TABLES if t not in existing_tables]
            if missing_tables:
                errors.append(f"Missing tables: {', '.join(missing_tables)}")
                _log.error(f"Health check: missing tables — {missing_tables}")
        except Exception as e:
            errors.append(f"Table check error: {e}")

        # Schema version
        try:
            row = conn.execute(
                "SELECT value FROM app_config WHERE key='schema_version'"
            ).fetchone()
            if row:
                schema_version = int(row["value"])
            else:
                warnings.append("Schema version not found in app_config")
        except Exception as e:
            warnings.append(f"Schema version check error: {e}")

        conn.close()

    except Exception as e:
        errors.append(f"Cannot connect to database: {e}")
        _log.error(f"Health check: connection failed — {e}")
        return HealthReport(
            ok=False, db_exists=db_exists, db_size_bytes=db_size,
            schema_version=0, integrity_ok=False, foreign_key_ok=False,
            table_count=0, missing_tables=list(_REQUIRED_TABLES),
            warnings=warnings, errors=errors,
        )

    ok = len(errors) == 0
    report = HealthReport(
        ok=ok, db_exists=db_exists, db_size_bytes=db_size,
        schema_version=schema_version, integrity_ok=integrity_ok,
        foreign_key_ok=foreign_key_ok, table_count=table_count,
        missing_tables=missing_tables, warnings=warnings, errors=errors,
    )

    if ok:
        _log.info(f"Health check passed: {report.summary}")
    else:
        _log.error(f"Health check FAILED: {report.summary}")

    return report


def run_startup_checks() -> HealthReport:
    """
    Run all startup checks. Called once at application init.

    Returns the health report for the UI to display if needed.
    """
    _log.info("Running startup health checks...")
    report = check_database_health()

    if report.warnings:
        for w in report.warnings:
            _log.warning(f"  Warning: {w}")
    if report.errors:
        for e in report.errors:
            _log.error(f"  Error: {e}")

    return report
