"""app/repositories/return_repo.py — CRUD for returns."""
from __future__ import annotations
from typing import Optional

from app.repositories.base import BaseRepository
from app.models.return_item import ReturnItem


class ReturnRepository(BaseRepository):
    """Repository for the returns table."""

    def get_all(self, *, limit: int = 200) -> list[ReturnItem]:
        sql = """
            SELECT r.*,
                   COALESCE(ii.name, '') || ' ' || COALESCE(ii.brand, '') AS item_name,
                   COALESCE(ii.barcode, '') AS item_barcode
            FROM returns r
            JOIN inventory_items ii ON ii.id = r.item_id
            ORDER BY r.created_at DESC LIMIT ?
        """
        with self._conn() as conn:
            return [self._build(r) for r in conn.execute(sql, (limit,)).fetchall()]

    def get_summary(self) -> dict:
        with self._conn() as conn:
            row = conn.execute("""
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN action = 'RESTOCK' THEN quantity ELSE 0 END) AS restocked,
                    SUM(CASE WHEN action = 'WRITEOFF' THEN quantity ELSE 0 END) AS writeoff,
                    COALESCE(SUM(refund_amount), 0) AS total_refunded
                FROM returns
            """).fetchone()
            return dict(row) if row else {}

    def create(self, *, item_id: int, quantity: int, reason: str = "",
               action: str = "RESTOCK", refund_amount: float = 0,
               sale_id: Optional[int] = None) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO returns (sale_id, item_id, quantity, reason, action, refund_amount)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (sale_id, item_id, quantity, reason, action, refund_amount),
            )
            return cur.lastrowid

    def _build(self, row) -> ReturnItem:
        return ReturnItem(
            id=row["id"],
            sale_id=row["sale_id"],
            item_id=row["item_id"],
            quantity=row["quantity"],
            reason=row["reason"] or "",
            action=row["action"],
            refund_amount=row["refund_amount"] or 0,
            created_at=row["created_at"],
            item_name=(row["item_name"] or "").strip(),
            item_barcode=row["item_barcode"] or "",
        )
