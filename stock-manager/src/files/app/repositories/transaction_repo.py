"""app/repositories/transaction_repo.py — Unified audit log queries and inserts."""
from __future__ import annotations
from typing import Optional
import sqlite3

from app.repositories.base import BaseRepository
from app.models.transaction import InventoryTransaction


class TransactionRepository(BaseRepository):

    # ── Unified (inventory_transactions) ─────────────────────────────────────

    def log_op(self, conn: sqlite3.Connection, item_id: int, operation: str,
               quantity: int, stock_before: int, stock_after: int,
               note: str = "") -> None:
        conn.execute(
            """INSERT INTO inventory_transactions
               (item_id, operation, quantity, stock_before, stock_after, note)
               VALUES (?,?,?,?,?,?)""",
            (item_id, operation, quantity, stock_before, stock_after, note or None),
        )

    def get_transactions(self, item_id: Optional[int] = None,
                         limit: int = 500) -> list[InventoryTransaction]:
        sql = """
            SELECT t.*,
                   ii.brand, ii.name, ii.color,
                   pm.name  AS model_name,
                   pt.name  AS pt_name
            FROM inventory_transactions t
            JOIN inventory_items ii ON ii.id = t.item_id
            LEFT JOIN phone_models pm ON pm.id = ii.model_id
            LEFT JOIN part_types   pt ON pt.id = ii.part_type_id
        """
        params: list = []
        if item_id is not None:
            sql += " WHERE t.item_id=?"
            params.append(item_id)
        sql += " ORDER BY t.timestamp DESC LIMIT ?"
        params.append(limit)
        with self._conn() as conn:
            return [self._build_txn(r) for r in conn.execute(sql, params).fetchall()]

    def get_filtered(self, *, search: str = "", operation: str = "",
                     date_from: str = "", date_to: str = "",
                     limit: int = 500, offset: int = 0) -> list[InventoryTransaction]:
        """Advanced query with filters, pagination, and search."""
        sql = """
            SELECT t.*,
                   ii.brand, ii.name, ii.color,
                   pm.name  AS model_name,
                   pt.name  AS pt_name
            FROM inventory_transactions t
            JOIN inventory_items ii ON ii.id = t.item_id
            LEFT JOIN phone_models pm ON pm.id = ii.model_id
            LEFT JOIN part_types   pt ON pt.id = ii.part_type_id
            WHERE 1=1
        """
        params: list = []
        if search:
            sql += " AND (ii.brand LIKE ? OR ii.name LIKE ? OR ii.color LIKE ? OR t.note LIKE ?)"
            w = f"%{search}%"
            params.extend([w, w, w, w])
        if operation:
            sql += " AND t.operation=?"
            params.append(operation)
        if date_from:
            sql += " AND t.timestamp >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND t.timestamp <= ?"
            params.append(date_to + " 23:59:59")
        sql += " ORDER BY t.timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._conn() as conn:
            return [self._build_txn(r) for r in conn.execute(sql, params).fetchall()]

    def count_filtered(self, *, search: str = "", operation: str = "",
                       date_from: str = "", date_to: str = "") -> int:
        """Count matching transactions for pagination."""
        sql = """
            SELECT COUNT(*) FROM inventory_transactions t
            JOIN inventory_items ii ON ii.id = t.item_id
            WHERE 1=1
        """
        params: list = []
        if search:
            sql += " AND (ii.brand LIKE ? OR ii.name LIKE ? OR ii.color LIKE ? OR t.note LIKE ?)"
            w = f"%{search}%"
            params.extend([w, w, w, w])
        if operation:
            sql += " AND t.operation=?"
            params.append(operation)
        if date_from:
            sql += " AND t.timestamp >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND t.timestamp <= ?"
            params.append(date_to + " 23:59:59")
        with self._conn() as conn:
            return conn.execute(sql, params).fetchone()[0]

    def get_summary_stats(self, *, search: str = "", operation: str = "",
                          date_from: str = "", date_to: str = "") -> dict:
        """Return aggregate stats for matching transactions."""
        sql = """
            SELECT
                COUNT(*) as total,
                COALESCE(SUM(CASE WHEN t.operation='IN' THEN t.quantity ELSE 0 END), 0) as total_in,
                COALESCE(SUM(CASE WHEN t.operation='OUT' THEN t.quantity ELSE 0 END), 0) as total_out
            FROM inventory_transactions t
            JOIN inventory_items ii ON ii.id = t.item_id
            WHERE 1=1
        """
        params: list = []
        if search:
            sql += " AND (ii.brand LIKE ? OR ii.name LIKE ? OR ii.color LIKE ? OR t.note LIKE ?)"
            w = f"%{search}%"
            params.extend([w, w, w, w])
        if operation:
            sql += " AND t.operation=?"
            params.append(operation)
        if date_from:
            sql += " AND t.timestamp >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND t.timestamp <= ?"
            params.append(date_to + " 23:59:59")
        with self._conn() as conn:
            r = conn.execute(sql, params).fetchone()
            return {"total": r[0], "total_in": r[1], "total_out": r[2]}

    # ── Builder ───────────────────────────────────────────────────────────────

    def _build_txn(self, row) -> InventoryTransaction:
        return InventoryTransaction(
            id=row["id"], item_id=row["item_id"],
            operation=row["operation"], quantity=row["quantity"],
            stock_before=row["stock_before"], stock_after=row["stock_after"],
            note=row["note"], timestamp=row["timestamp"],
            brand=row["brand"] or "",
            name=row["name"] or "",
            color=row["color"] or "",
            model_name=row["model_name"] or "",
            part_type_name=row["pt_name"] or "",
        )
