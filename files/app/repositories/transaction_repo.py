"""app/repositories/transaction_repo.py — Unified audit log queries and inserts."""
from __future__ import annotations
from typing import Optional
import sqlite3

from app.repositories.base import BaseRepository
from app.models.transaction import InventoryTransaction, ProductTransaction


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

    # ── Compatibility — product side (used by products tab until Phase C) ─────

    def log_product_op(self, conn: sqlite3.Connection, product_id: int,
                       operation: str, quantity: int,
                       stock_before: int, stock_after: int, note: str = "") -> None:
        """Delegates to log_op — item_id == product_id in inventory_items."""
        self.log_op(conn, product_id, operation, quantity,
                    stock_before, stock_after, note)

    def get_product_transactions(self, product_id: Optional[int] = None,
                                 limit: int = 500) -> list[ProductTransaction]:
        """Returns ProductTransaction objects for the products tab (Phase C removes this)."""
        txns = self.get_transactions(item_id=product_id, limit=limit)
        result = []
        for t in txns:
            result.append(ProductTransaction(
                id=t.id, product_id=t.item_id,
                operation=t.operation, quantity=t.quantity,
                stock_before=t.stock_before, stock_after=t.stock_after,
                note=t.note, timestamp=t.timestamp,
                brand=t.brand, type=t.name, color=t.color,
            ))
        return result

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
