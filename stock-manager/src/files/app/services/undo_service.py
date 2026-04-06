"""
app/services/undo_service.py — Transaction undo capability.

Provides time-limited undo for stock operations by creating reverse
transactions. Original transactions are never deleted — the audit
trail is always preserved.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from app.core.database import get_connection
from app.repositories.item_repo import ItemRepository
from app.repositories.transaction_repo import TransactionRepository
from app.core.i18n import t
from app.core.logger import get_logger

_log = get_logger(__name__)

# Default undo window in hours
_UNDO_WINDOW_HOURS = 24


class UndoService:

    def __init__(self) -> None:
        self._items = ItemRepository()
        self._txn = TransactionRepository()

    def can_undo(self, txn_id: int) -> tuple[bool, str]:
        """Check whether a transaction can be undone.

        Returns (can_undo, reason) tuple. Only IN/OUT/ADJUST operations
        within the undo window are eligible.
        """
        txn = self._get_transaction(txn_id)
        if txn is None:
            return False, t("undo_not_found")

        # Only stock operations can be undone
        if txn["operation"] not in ("IN", "OUT", "ADJUST"):
            return False, t("undo_not_stock_op")

        # Check if it's an undo transaction itself
        note = txn["note"] or ""
        if note.startswith("[UNDO]"):
            return False, t("undo_already_undone")

        # Check undo window
        ts = datetime.fromisoformat(txn["timestamp"])
        if datetime.now() - ts > timedelta(hours=_UNDO_WINDOW_HOURS):
            return False, t("undo_expired")

        # Check item still exists
        item = self._items.get_by_id(txn["item_id"])
        if item is None:
            return False, t("undo_item_deleted")

        return True, ""

    def undo_transaction(self, txn_id: int) -> dict:
        """Undo a stock transaction by creating a reverse operation.

        Returns dict with before/after stock levels of the reversal.
        Raises ValueError if undo is not possible.
        """
        can, reason = self.can_undo(txn_id)
        if not can:
            raise ValueError(reason)

        txn = self._get_transaction(txn_id)
        item_id = txn["item_id"]
        op = txn["operation"]
        qty = txn["quantity"]
        original_before = txn["stock_before"]
        original_after = txn["stock_after"]

        with get_connection() as conn:
            item = self._items.get_by_id(item_id)
            if item is None:
                raise ValueError(t("undo_item_deleted"))

            current_stock = item.stock

            if op == "IN":
                # Reverse of IN = reduce stock by qty
                new_stock = current_stock - qty
                if new_stock < 0:
                    raise ValueError(t("undo_would_go_negative"))
                reverse_op = "OUT"
            elif op == "OUT":
                # Reverse of OUT = add stock back
                new_stock = current_stock + qty
                reverse_op = "IN"
            else:
                # ADJUST — restore to stock_before
                new_stock = original_before
                reverse_op = "ADJUST"

            # Apply the reversal
            self._items.set_exact(conn, item_id, new_stock)

            # Log the reverse transaction
            note = f"[UNDO] Reversed txn #{txn_id}: {op} {qty}"
            reverse_qty = qty if op != "ADJUST" else abs(new_stock - current_stock)
            self._txn.log_op(conn, item_id, reverse_op, reverse_qty,
                             current_stock, new_stock, note)

            _log.info(
                f"Undo: txn_id={txn_id}, original_op={op}, reverse_op={reverse_op}, "
                f"qty={qty}, stock {current_stock} -> {new_stock}"
            )

        return {
            "before": current_stock,
            "after": new_stock,
            "reversed_txn_id": txn_id,
            "reverse_op": reverse_op,
            "item_id": item_id,
        }

    def get_recent_undoable(self, limit: int = 10) -> list[dict]:
        """Return recent transactions that can still be undone."""
        cutoff = (datetime.now() - timedelta(hours=_UNDO_WINDOW_HOURS)).isoformat()
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT t.id, t.item_id, t.operation, t.quantity,
                          t.stock_before, t.stock_after, t.note, t.timestamp,
                          ii.brand, ii.name, ii.color
                   FROM inventory_transactions t
                   JOIN inventory_items ii ON ii.id = t.item_id
                   WHERE t.operation IN ('IN', 'OUT', 'ADJUST')
                     AND t.timestamp >= ?
                     AND (t.note IS NULL OR t.note NOT LIKE '[UNDO]%')
                   ORDER BY t.timestamp DESC
                   LIMIT ?""",
                (cutoff, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Internal ─────────────────────────────────────────────────────────────

    def _get_transaction(self, txn_id: int) -> Optional[dict]:
        """Fetch a single transaction by ID."""
        with get_connection() as conn:
            row = conn.execute(
                """SELECT id, item_id, operation, quantity,
                          stock_before, stock_after, note, timestamp
                   FROM inventory_transactions WHERE id=?""",
                (txn_id,),
            ).fetchone()
        return dict(row) if row else None
