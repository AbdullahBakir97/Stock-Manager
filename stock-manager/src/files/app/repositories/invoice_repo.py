"""
app/repositories/invoice_repo.py — Scan-session invoices (quick scan).

Each confirmed Quick Scan session produces a `scan_invoices` row + one
`scan_invoice_items` row per pending item. Prices are SNAPSHOT at commit
time so historical invoices stay stable even if the price changes later.

Invoice number format: `INV-YYYYMMDD-NNNN`
    - YYYYMMDD = date stamp (today at commit time)
    - NNNN     = zero-padded sequence within that day, starting at 0001
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.repositories.base import BaseRepository


class InvoiceRepository(BaseRepository):

    # ── Numbering ─────────────────────────────────────────────────────────────

    def next_invoice_number(self) -> str:
        """Generate the next invoice number for today: INV-YYYYMMDD-NNNN."""
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"INV-{today}-"
        with self._conn() as conn:
            row = conn.execute(
                "SELECT invoice_number FROM scan_invoices "
                "WHERE invoice_number LIKE ? "
                "ORDER BY invoice_number DESC LIMIT 1",
                (prefix + "%",),
            ).fetchone()
        if row:
            try:
                seq = int(row["invoice_number"].rsplit("-", 1)[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f"{prefix}{seq:04d}"

    # ── Create ────────────────────────────────────────────────────────────────

    def create_invoice(self, *, operation: str, layout: str,
                       customer_name: str, currency: str,
                       items: list[dict], note: str = "") -> int:
        """Insert an invoice header + its line items in one transaction.

        `items` is a list of dicts with keys:
            item_id (int), item_snapshot (str), barcode (str),
            quantity (int), unit_price (float), line_total (float)

        Returns the new invoice id.
        """
        subtotal = sum(float(i.get("line_total", 0)) for i in items)
        total = subtotal  # no tax/discount for scan invoices (for now)
        invoice_number = self.next_invoice_number()

        conn = self._conn()
        try:
            cur = conn.execute(
                """INSERT INTO scan_invoices
                   (invoice_number, operation, layout, customer_name,
                    subtotal, total, currency, note, pdf_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, '')""",
                (invoice_number, operation, layout, customer_name,
                 subtotal, total, currency, note),
            )
            invoice_id = cur.lastrowid
            for it in items:
                conn.execute(
                    """INSERT INTO scan_invoice_items
                       (invoice_id, item_id, item_snapshot, barcode,
                        quantity, unit_price, line_total)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        invoice_id,
                        int(it["item_id"]),
                        str(it.get("item_snapshot", "")),
                        str(it.get("barcode", "")),
                        int(it["quantity"]),
                        float(it["unit_price"]),
                        float(it["line_total"]),
                    ),
                )
            conn.commit()
            return int(invoice_id)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_invoice(self, invoice_id: int) -> Optional[tuple[dict, list[dict]]]:
        """Return (header_dict, list[line_dict]) or None if not found."""
        with self._conn() as conn:
            header = conn.execute(
                "SELECT * FROM scan_invoices WHERE id=?", (invoice_id,)
            ).fetchone()
            if not header:
                return None
            lines = conn.execute(
                "SELECT * FROM scan_invoice_items WHERE invoice_id=? ORDER BY id",
                (invoice_id,),
            ).fetchall()
        return dict(header), [dict(r) for r in lines]

    def list_recent(self, limit: int = 50) -> list[dict]:
        """List recent invoices (header rows only)."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM scan_invoices ORDER BY created_at DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Update ────────────────────────────────────────────────────────────────

    def set_pdf_path(self, invoice_id: int, pdf_path: str) -> None:
        """Record the absolute path of the rendered PDF on disk."""
        with self._conn() as conn:
            conn.execute(
                "UPDATE scan_invoices SET pdf_path=? WHERE id=?",
                (pdf_path, invoice_id),
            )
            conn.commit()

    # ── Analytics helpers ────────────────────────────────────────────────────

    def get_totals(self, date_from: str = "", date_to: str = "",
                   operation: str = "") -> dict:
        """Aggregate totals across a date range.
        Returns {'count', 'count_in', 'count_out', 'total_in', 'total_out', 'total'}.
        """
        sql = """SELECT COUNT(*) AS count,
                        COALESCE(SUM(CASE WHEN operation='IN'  THEN 1 ELSE 0 END), 0) AS count_in,
                        COALESCE(SUM(CASE WHEN operation='OUT' THEN 1 ELSE 0 END), 0) AS count_out,
                        COALESCE(SUM(CASE WHEN operation='IN'  THEN total ELSE 0 END), 0) AS total_in,
                        COALESCE(SUM(CASE WHEN operation='OUT' THEN total ELSE 0 END), 0) AS total_out,
                        COALESCE(SUM(total), 0) AS total
                   FROM scan_invoices WHERE 1=1"""
        params: list = []
        if date_from:
            sql += " AND DATE(created_at) >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND DATE(created_at) <= ?"
            params.append(date_to)
        if operation:
            sql += " AND operation = ?"
            params.append(operation)
        with self._conn() as conn:
            r = conn.execute(sql, params).fetchone()
        return dict(r) if r else {"count": 0, "count_in": 0, "count_out": 0,
                                   "total_in": 0, "total_out": 0, "total": 0}

    def get_daily(self, date_from: str, date_to: str) -> list[dict]:
        """Per-day invoice aggregates in range. Returns
        [{'date', 'count', 'in_total', 'out_total'}, ...] ordered by date."""
        sql = """SELECT DATE(created_at) AS date,
                        COUNT(*) AS count,
                        COALESCE(SUM(CASE WHEN operation='IN'  THEN total ELSE 0 END), 0) AS in_total,
                        COALESCE(SUM(CASE WHEN operation='OUT' THEN total ELSE 0 END), 0) AS out_total
                   FROM scan_invoices
                  WHERE DATE(created_at) >= ? AND DATE(created_at) <= ?
               GROUP BY DATE(created_at)
               ORDER BY DATE(created_at) ASC"""
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(sql, (date_from, date_to)).fetchall()]

    def get_top_customers(self, date_from: str = "", date_to: str = "",
                          limit: int = 10) -> list[dict]:
        """Top customers by total invoice value (OUT only). Walk-in
        invoices (empty customer) are excluded."""
        sql = """SELECT customer_name,
                        COUNT(*) AS invoice_count,
                        COALESCE(SUM(total), 0) AS revenue
                   FROM scan_invoices
                  WHERE customer_name IS NOT NULL
                    AND TRIM(customer_name) != ''
                    AND operation = 'OUT'"""
        params: list = []
        if date_from:
            sql += " AND DATE(created_at) >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND DATE(created_at) <= ?"
            params.append(date_to)
        sql += (" GROUP BY customer_name"
                " ORDER BY revenue DESC"
                " LIMIT ?")
        params.append(int(limit))
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
