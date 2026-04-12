"""app/repositories/purchase_order_repo.py — CRUD for purchase orders + line items."""
from __future__ import annotations
from typing import Optional
from datetime import datetime

from app.repositories.base import BaseRepository
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine


class PurchaseOrderRepository(BaseRepository):
    """Repository for purchase_orders and purchase_order_lines tables."""

    # ── PO queries ───────────────────────────────────────────────────────────

    def get_all(self, *, status: str = "", search: str = "",
                limit: int = 200) -> list[PurchaseOrder]:
        """List POs with optional status/search filter."""
        sql = """
            SELECT po.*,
                   s.name AS supplier_name,
                   COUNT(pol.id) AS line_count,
                   COALESCE(SUM(pol.quantity * pol.cost_price), 0) AS total_value
            FROM purchase_orders po
            LEFT JOIN suppliers s ON s.id = po.supplier_id
            LEFT JOIN purchase_order_lines pol ON pol.po_id = po.id
            WHERE 1=1
        """
        params: list = []
        if status:
            sql += " AND po.status = ?"
            params.append(status)
        if search:
            sql += " AND (po.po_number LIKE ? OR s.name LIKE ? OR po.notes LIKE ?)"
            s = f"%{search}%"
            params.extend([s, s, s])
        sql += " GROUP BY po.id ORDER BY po.created_at DESC LIMIT ?"
        params.append(limit)
        with self._conn() as conn:
            return [self._build_po(r) for r in conn.execute(sql, params).fetchall()]

    def get_by_id(self, po_id: int) -> Optional[PurchaseOrder]:
        sql = """
            SELECT po.*,
                   s.name AS supplier_name,
                   COUNT(pol.id) AS line_count,
                   COALESCE(SUM(pol.quantity * pol.cost_price), 0) AS total_value
            FROM purchase_orders po
            LEFT JOIN suppliers s ON s.id = po.supplier_id
            LEFT JOIN purchase_order_lines pol ON pol.po_id = po.id
            WHERE po.id = ?
            GROUP BY po.id
        """
        with self._conn() as conn:
            row = conn.execute(sql, (po_id,)).fetchone()
            if not row:
                return None
            po = self._build_po(row)
            po.lines = self.get_lines(po_id)
            return po

    def get_summary(self) -> dict:
        """Aggregate stats for PO dashboard."""
        with self._conn() as conn:
            row = conn.execute("""
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status = 'DRAFT' THEN 1 ELSE 0 END) AS draft_count,
                    SUM(CASE WHEN status = 'SENT' THEN 1 ELSE 0 END) AS sent_count,
                    SUM(CASE WHEN status IN ('PARTIAL', 'RECEIVED') THEN 1 ELSE 0 END) AS received_count
                FROM purchase_orders
            """).fetchone()
            return dict(row) if row else {}

    def next_po_number(self) -> str:
        """Generate next PO number like PO-2026-0001."""
        year = datetime.now().year
        prefix = f"PO-{year}-"
        with self._conn() as conn:
            row = conn.execute(
                "SELECT po_number FROM purchase_orders WHERE po_number LIKE ? ORDER BY id DESC LIMIT 1",
                (f"{prefix}%",),
            ).fetchone()
            if row:
                last_num = int(row["po_number"].split("-")[-1])
                return f"{prefix}{last_num + 1:04d}"
            return f"{prefix}0001"

    # ── PO writes ────────────────────────────────────────────────────────────

    def create(self, supplier_id: Optional[int] = None, notes: str = "") -> int:
        po_number = self.next_po_number()
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO purchase_orders (po_number, supplier_id, notes)
                   VALUES (?, ?, ?)""",
                (po_number, supplier_id, notes),
            )
            return cur.lastrowid

    def update(self, po_id: int, *, supplier_id: Optional[int] = None,
               notes: str = "", status: Optional[str] = None) -> None:
        with self._conn() as conn:
            if status:
                conn.execute(
                    """UPDATE purchase_orders
                       SET supplier_id=?, notes=?, status=?, updated_at=datetime('now')
                       WHERE id=?""",
                    (supplier_id, notes, status, po_id),
                )
            else:
                conn.execute(
                    """UPDATE purchase_orders
                       SET supplier_id=?, notes=?, updated_at=datetime('now')
                       WHERE id=?""",
                    (supplier_id, notes, po_id),
                )

    def set_status(self, po_id: int, status: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE purchase_orders SET status=?, updated_at=datetime('now') WHERE id=?",
                (status, po_id),
            )

    def delete(self, po_id: int) -> bool:
        """Delete a PO (only if DRAFT or CANCELLED). Returns True on success."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT status FROM purchase_orders WHERE id=?", (po_id,)
            ).fetchone()
            if not row or row["status"] not in ("DRAFT", "CANCELLED"):
                return False
            conn.execute("DELETE FROM purchase_order_lines WHERE po_id=?", (po_id,))
            conn.execute("DELETE FROM purchase_orders WHERE id=?", (po_id,))
            return True

    # ── Line item queries ────────────────────────────────────────────────────

    def get_lines(self, po_id: int) -> list[PurchaseOrderLine]:
        sql = """
            SELECT pol.*,
                   COALESCE(ii.name, '') || ' ' || COALESCE(ii.brand, '') AS item_name,
                   COALESCE(ii.barcode, '') AS item_barcode
            FROM purchase_order_lines pol
            JOIN inventory_items ii ON ii.id = pol.item_id
            WHERE pol.po_id = ?
            ORDER BY pol.id
        """
        with self._conn() as conn:
            return [self._build_line(r) for r in conn.execute(sql, (po_id,)).fetchall()]

    # ── Line item writes ─────────────────────────────────────────────────────

    def add_line(self, po_id: int, item_id: int, quantity: int = 1,
                 cost_price: float = 0) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO purchase_order_lines (po_id, item_id, quantity, cost_price)
                   VALUES (?, ?, ?, ?)""",
                (po_id, item_id, quantity, cost_price),
            )
            conn.execute(
                "UPDATE purchase_orders SET updated_at=datetime('now') WHERE id=?",
                (po_id,),
            )
            return cur.lastrowid

    def update_line(self, line_id: int, quantity: int, cost_price: float) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE purchase_order_lines SET quantity=?, cost_price=? WHERE id=?",
                (quantity, cost_price, line_id),
            )

    def remove_line(self, line_id: int) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM purchase_order_lines WHERE id=?", (line_id,))

    def receive_line(self, line_id: int, received_qty: int) -> None:
        """Mark a line item as received (partial or full)."""
        with self._conn() as conn:
            conn.execute(
                "UPDATE purchase_order_lines SET received_qty=? WHERE id=?",
                (received_qty, line_id),
            )

    # ── Builders ─────────────────────────────────────────────────────────────

    def _build_po(self, row) -> PurchaseOrder:
        return PurchaseOrder(
            id=row["id"],
            po_number=row["po_number"],
            supplier_id=row["supplier_id"],
            status=row["status"],
            notes=row["notes"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            supplier_name=row["supplier_name"] or "",
            line_count=row["line_count"],
            total_value=row["total_value"],
        )

    def _build_line(self, row) -> PurchaseOrderLine:
        return PurchaseOrderLine(
            id=row["id"],
            po_id=row["po_id"],
            item_id=row["item_id"],
            quantity=row["quantity"],
            cost_price=row["cost_price"],
            received_qty=row["received_qty"],
            item_name=(row["item_name"] or "").strip(),
            item_barcode=row["item_barcode"] or "",
        )
