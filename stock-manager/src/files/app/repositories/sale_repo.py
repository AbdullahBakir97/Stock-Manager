"""app/repositories/sale_repo.py — Sales and sale-item queries."""
from __future__ import annotations

from typing import Optional

from app.repositories.base import BaseRepository
from app.models.sale import Sale, SaleItem


class SaleRepository(BaseRepository):

    # ── Sale CRUD ────────────────────────────────────────────────────────────

    def create(self, customer_name: str = "", discount: float = 0,
               note: str = "", items: list[dict] | None = None,
               customer_id: int | None = None) -> int:
        """Create a sale with line items. Each item dict needs:
        item_id, quantity, unit_price, cost_price.
        Returns the new sale id."""
        with self._conn() as conn:
            total = sum(
                d["quantity"] * d["unit_price"] for d in (items or [])
            )
            cur = conn.execute(
                """INSERT INTO sales (customer_name, total_amount, discount, note, customer_id)
                   VALUES (?,?,?,?,?)""",
                (customer_name.strip(), total, discount, note.strip(),
                 customer_id),
            )
            sale_id = cur.lastrowid
            for d in (items or []):
                line_total = d["quantity"] * d["unit_price"]
                conn.execute(
                    """INSERT INTO sale_items
                       (sale_id, item_id, quantity, unit_price, cost_price, line_total)
                       VALUES (?,?,?,?,?,?)""",
                    (sale_id, d["item_id"], d["quantity"],
                     d["unit_price"], d.get("cost_price", 0), line_total),
                )
            return sale_id

    def get_by_id(self, sale_id: int) -> Optional[Sale]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM sales WHERE id=?", (sale_id,)
            ).fetchone()
            if not row:
                return None
            sale = self._build(row)
            sale.items = self._get_items(conn, sale_id)
            return sale

    def get_all(self, limit: int = 200, offset: int = 0,
                date_from: str = "", date_to: str = "") -> list[Sale]:
        with self._conn() as conn:
            sql = "SELECT * FROM sales"
            params: list = []
            clauses: list[str] = []
            if date_from:
                clauses.append("timestamp >= ?")
                params.append(date_from)
            if date_to:
                clauses.append("timestamp <= ?")
                params.append(date_to + " 23:59:59")
            if clauses:
                sql += " WHERE " + " AND ".join(clauses)
            sql += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            rows = conn.execute(sql, params).fetchall()
            return [self._build(r) for r in rows]

    def get_by_customer(self, customer_id: int, limit: int = 50) -> list[Sale]:
        """Return recent sales linked to a specific customer."""
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT * FROM sales
                   WHERE customer_id = ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (customer_id, limit),
            ).fetchall()
            return [self._build(r) for r in rows]

    def delete(self, sale_id: int) -> bool:
        with self._conn() as conn:
            conn.execute("DELETE FROM sales WHERE id=?", (sale_id,))
            return True

    # ── Reporting helpers ────────────────────────────────────────────────────

    def daily_totals(self, date: str) -> dict:
        """Return {count, revenue, profit} for a given date (YYYY-MM-DD)."""
        with self._conn() as conn:
            row = conn.execute(
                """SELECT COUNT(*) AS cnt,
                          COALESCE(SUM(total_amount - discount), 0) AS revenue
                   FROM sales
                   WHERE DATE(timestamp) = ?""",
                (date,),
            ).fetchone()
            profit_row = conn.execute(
                """SELECT COALESCE(SUM(si.line_total - si.cost_price * si.quantity), 0) AS profit
                   FROM sale_items si
                   JOIN sales s ON s.id = si.sale_id
                   WHERE DATE(s.timestamp) = ?""",
                (date,),
            ).fetchone()
            return {
                "count": row["cnt"],
                "revenue": row["revenue"],
                "profit": profit_row["profit"],
            }

    def top_items(self, limit: int = 10, date_from: str = "",
                  date_to: str = "") -> list[dict]:
        """Return top-selling items by quantity."""
        with self._conn() as conn:
            sql = """SELECT si.item_id,
                            COALESCE(ii.name, pm.name, '') AS item_name,
                            SUM(si.quantity) AS total_qty,
                            SUM(si.line_total) AS total_revenue
                     FROM sale_items si
                     JOIN inventory_items ii ON ii.id = si.item_id
                     LEFT JOIN phone_models pm ON pm.id = ii.model_id
                     JOIN sales s ON s.id = si.sale_id"""
            params: list = []
            clauses: list[str] = []
            if date_from:
                clauses.append("DATE(s.timestamp) >= ?")
                params.append(date_from)
            if date_to:
                clauses.append("DATE(s.timestamp) <= ?")
                params.append(date_to)
            if clauses:
                sql += " WHERE " + " AND ".join(clauses)
            sql += " GROUP BY si.item_id ORDER BY total_qty DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    # ── Internal ─────────────────────────────────────────────────────────────

    def _get_items(self, conn, sale_id: int) -> list[SaleItem]:
        rows = conn.execute(
            """SELECT si.*,
                      COALESCE(ii.name, pm.name, '') AS item_name,
                      COALESCE(ii.barcode, '') AS item_barcode
               FROM sale_items si
               JOIN inventory_items ii ON ii.id = si.item_id
               LEFT JOIN phone_models pm ON pm.id = ii.model_id
               WHERE si.sale_id=?""",
            (sale_id,),
        ).fetchall()
        return [self._build_si(r) for r in rows]

    def _build(self, row) -> Sale:
        return Sale(
            id=row["id"], customer_name=row["customer_name"],
            total_amount=row["total_amount"], discount=row["discount"],
            note=row["note"], timestamp=row["timestamp"],
            customer_id=row["customer_id"] if "customer_id" in row.keys() else None,
        )

    def _build_si(self, row) -> SaleItem:
        return SaleItem(
            id=row["id"], sale_id=row["sale_id"],
            item_id=row["item_id"], quantity=row["quantity"],
            unit_price=row["unit_price"], cost_price=row["cost_price"],
            line_total=row["line_total"],
            item_name=row["item_name"] if "item_name" in row.keys() else "",
            item_barcode=row["item_barcode"] if "item_barcode" in row.keys() else "",
        )
