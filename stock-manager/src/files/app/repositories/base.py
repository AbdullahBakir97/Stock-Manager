"""app/repositories/base.py — Shared connection provider."""
from __future__ import annotations
import sqlite3
from app.core.database import get_connection


class BaseRepository:
    """All repos inherit this for a single get_connection() source."""

    def _conn(self) -> sqlite3.Connection:
        return get_connection()
