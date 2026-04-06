"""app/services/report_service.py — Professional PDF report generation using fpdf2."""
from __future__ import annotations
from datetime import datetime, timedelta
import tempfile
from pathlib import Path
from fpdf import FPDF

from app.repositories.item_repo import ItemRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.audit_repo import AuditRepository
from app.core.config import ShopConfig
from app.core.i18n import t


# ── Latin-1 safe FPDF subclass ──────────────────────────────────────────────
_UMAP = {
    "\u20ac": "EUR", "\u2013": "-", "\u2014": "--",
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2022": "*", "\u2026": "...", "\u00b7": ".",
}


def _latin1(text: str) -> str:
    for k, v in _UMAP.items():
        text = text.replace(k, v)
    return text.encode("latin-1", errors="replace").decode("latin-1")


class SafePDF(FPDF):
    """FPDF subclass that auto-sanitises text to latin-1."""
    def cell(self, w=0, h=0, txt="", *a, **kw):
        return super().cell(w, h, _latin1(str(txt)), *a, **kw)
    def multi_cell(self, w, h=0, txt="", *a, **kw):
        return super().multi_cell(w, h, _latin1(str(txt)), *a, **kw)
    def rounded_rect(self, x, y, w, h, r=0, style="", *a, **kw):
        # Fallback for older fpdf2 versions without rounded_rect
        if hasattr(super(), "rounded_rect"):
            return super().rounded_rect(x, y, w, h, r, style, *a, **kw)
        self.rect(x, y, w, h, style)


# ── Brand colors ─────────────────────────────────────────────────────────────
_PRIMARY    = (16, 185, 129)   # Emerald green (#10B981)
_PRIMARY_DK = (5, 150, 105)    # Darker emerald
_DARK       = (15, 23, 42)     # Slate-900
_GRAY_800   = (30, 41, 59)
_GRAY_600   = (71, 85, 105)
_GRAY_400   = (148, 163, 184)
_GRAY_200   = (226, 232, 240)
_GRAY_50    = (248, 250, 252)
_WHITE      = (255, 255, 255)
_RED        = (239, 68, 68)
_AMBER      = (245, 158, 11)
_GREEN_TXT  = (5, 150, 105)
_RED_TXT    = (220, 38, 38)

_PW = 186  # usable page width (A4 210mm - 2*12mm margins)


class ReportService:
    """Generates professional PDF reports for inventory, low stock, transactions, and summary."""

    def __init__(self) -> None:
        self._item_repo = ItemRepository()
        self._txn_repo = TransactionRepository()
        self._audit_repo = AuditRepository()
        self._config = ShopConfig.get()

    # ════════════════════════════════════════════════════════════════════════
    # PUBLIC — Report generators
    # ════════════════════════════════════════════════════════════════════════

    def generate_inventory_report(self, output_path: str | None = None) -> str:
        pdf = self._create_pdf()
        pdf.add_page()
        self._header(pdf, t("report_inventory_title"),
                     "Complete inventory with stock levels, pricing, and status")

        summary = self._item_repo.get_summary()
        self._kpi_cards(pdf, [
            ("Total Products", str(summary.get("total_products", 0))),
            ("Total Units",    str(summary.get("total_units", 0))),
            ("Low Stock",      str(summary.get("low_stock_count", 0))),
            ("Out of Stock",   str(summary.get("out_of_stock_count", 0))),
        ])

        items = self._item_repo.get_all_items()
        if items:
            self._section_title(pdf, f"All Items ({len(items)})")
            self._inventory_table(pdf, items)
        else:
            self._empty_msg(pdf, "No inventory items found.")

        self._footer_line(pdf)
        return self._save_pdf(pdf, output_path, "inventory_report")

    def generate_low_stock_report(self, output_path: str | None = None) -> str:
        pdf = self._create_pdf()
        pdf.add_page()
        self._header(pdf, t("report_low_stock_title"),
                     "Items requiring restocking, sorted by urgency")

        items = self._item_repo.get_low_stock()
        out_count = sum(1 for i in items if i.is_out)

        self._kpi_cards(pdf, [
            ("Low Stock Items", str(len(items))),
            ("Out of Stock",    str(out_count)),
            ("Needs Reorder",   str(len(items) - out_count)),
        ])

        if items:
            self._section_title(pdf, "Items Below Minimum")
            self._low_stock_table(pdf, items)
        else:
            self._empty_msg(pdf, "All items are above minimum stock levels.")

        self._footer_line(pdf)
        return self._save_pdf(pdf, output_path, "low_stock_report")

    def generate_transaction_report(self, days: int = 30,
                                    output_path: str | None = None) -> str:
        pdf = self._create_pdf()
        pdf.add_page()
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        date_to = datetime.now().strftime("%Y-%m-%d")
        self._header(pdf, t("report_txn_title"),
                     f"Stock movements from {date_from} to {date_to}")

        txns = self._txn_repo.get_transactions(limit=500)
        total_in = sum(tx.quantity for tx in txns if tx.operation == "IN")
        total_out = sum(tx.quantity for tx in txns if tx.operation == "OUT")

        self._kpi_cards(pdf, [
            ("Transactions", str(len(txns))),
            ("Total In",     f"+{total_in}"),
            ("Total Out",    f"-{total_out}"),
            ("Net Change",   f"{total_in - total_out:+d}"),
        ])

        if txns:
            self._section_title(pdf, f"Recent Transactions ({min(len(txns), 200)})")
            self._transactions_table(pdf, txns[:200])
        else:
            self._empty_msg(pdf, "No transactions found for this period.")

        self._footer_line(pdf)
        return self._save_pdf(pdf, output_path, "transaction_report")

    def generate_summary_report(self, output_path: str | None = None) -> str:
        pdf = self._create_pdf()
        pdf.add_page()
        self._header(pdf, t("report_summary_title"),
                     "Executive overview of inventory health and key metrics")

        summary = self._item_repo.get_summary()
        low = self._item_repo.get_low_stock()
        out = [i for i in low if i.is_out]

        val = summary.get("inventory_value")
        val_str = self._config.format_currency(val) if val else "-"

        self._kpi_cards(pdf, [
            ("Total Products", str(summary.get("total_products", 0))),
            ("Total Units",    str(summary.get("total_units", 0))),
            ("Inventory Value", val_str),
        ])

        pdf.ln(4)
        self._kpi_cards(pdf, [
            ("Low Stock",    str(len(low))),
            ("Out of Stock", str(len(out))),
            ("Healthy Items", str(summary.get("total_products", 0)
                                  - len(low))),
        ])

        # Top urgent items
        if low:
            self._section_title(pdf, "Top Priority - Restock Needed")
            self._low_stock_table(pdf, low[:10])

        self._footer_line(pdf)
        return self._save_pdf(pdf, output_path, "summary_report")

    def generate_audit_sheet(self, output_path: str | None = None) -> str:
        """Print-ready inventory audit sheet for physical stock counts."""
        pdf = self._create_pdf()
        pdf.add_page()
        self._header(pdf, t("report_audit_title"),
                     "Physical stock count sheet — compare actual vs. system")

        items = self._item_repo.get_all_items()
        summary = self._item_repo.get_summary()

        self._kpi_cards(pdf, [
            ("Total SKUs",  str(len(items))),
            ("System Units", str(summary.get("total_units", 0))),
            ("Date",         datetime.now().strftime("%Y-%m-%d")),
        ])

        if items:
            self._section_title(pdf, f"Stock Count Sheet ({len(items)} items)")
            self._audit_table(pdf, items)
        else:
            self._empty_msg(pdf, "No inventory items found.")

        # Sign-off area
        pdf.ln(10)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*_GRAY_600)
        pdf.cell(0, 6, "Counted by: ________________________    "
                        "Date: _______________    "
                        "Signature: ________________________", ln=True)

        self._footer_line(pdf)
        return self._save_pdf(pdf, output_path, "audit_sheet")

    def generate_discrepancy_report(self, audit_id: int | None = None,
                                    output_path: str | None = None) -> str:
        """Discrepancy report comparing expected vs. actual stock levels.

        If audit_id is given, reports on that audit's findings.
        Otherwise, generates a current variance report from the latest
        completed audit.
        """
        pdf = self._create_pdf()
        pdf.add_page()
        self._header(pdf, t("report_discrepancy_title"),
                     "Expected vs. actual stock — variance analysis")

        # Find audit to report on
        if audit_id:
            audit = self._audit_repo.get_by_id(audit_id)
        else:
            # Get latest completed audit
            audits = self._audit_repo.get_all()
            completed = [a for a in audits if a.status == "COMPLETED"]
            audit = completed[0] if completed else None

        if audit is None:
            self._empty_msg(pdf, "No completed audits found. Run a stock audit first.")
            self._footer_line(pdf)
            return self._save_pdf(pdf, output_path, "discrepancy_report")

        lines = self._audit_repo.get_lines(audit.id)
        discrepancies = [ln for ln in lines if ln.counted_qty != ln.system_qty]
        total_lines = len(lines)
        total_disc = len(discrepancies)
        accuracy = ((total_lines - total_disc) / total_lines * 100) if total_lines else 100
        total_shrinkage = sum(
            (ln.system_qty - ln.counted_qty) for ln in discrepancies
            if ln.counted_qty < ln.system_qty
        )
        total_surplus = sum(
            (ln.counted_qty - ln.system_qty) for ln in discrepancies
            if ln.counted_qty > ln.system_qty
        )

        # KPI cards
        self._kpi_cards(pdf, [
            ("Audit", f"#{audit.id}"),
            ("Items Counted", str(total_lines)),
            ("Discrepancies", str(total_disc)),
            ("Accuracy", f"{accuracy:.1f}%"),
        ])

        # Summary stats
        self._section_title(pdf, "Variance Summary")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*_GRAY_700)
        pdf.cell(0, 5, f"Shrinkage (system > counted): {total_shrinkage} units", ln=True)
        pdf.cell(0, 5, f"Surplus (counted > system): {total_surplus} units", ln=True)
        pdf.cell(0, 5, f"Net variance: {total_surplus - total_shrinkage:+d} units", ln=True)
        pdf.ln(6)

        # Discrepancy table
        if discrepancies:
            self._section_title(pdf, f"Discrepancy Details ({total_disc} items)")
            cols = [("Item", 60), ("System Qty", 26), ("Counted Qty", 26),
                    ("Variance", 26), ("Variance %", 24), ("Status", 24)]
            # Header row
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_fill_color(*_GRAY_100)
            for label, w in cols:
                pdf.cell(w, 7, label, border=0, fill=True)
            pdf.ln()
            # Data rows
            pdf.set_font("Helvetica", "", 8)
            for i, ln in enumerate(discrepancies):
                variance = ln.counted_qty - ln.system_qty
                var_pct = (variance / ln.system_qty * 100) if ln.system_qty else 0
                status = "Shrinkage" if variance < 0 else "Surplus"
                if i % 2 == 0:
                    pdf.set_fill_color(250, 250, 252)
                else:
                    pdf.set_fill_color(255, 255, 255)
                # Color code the variance
                if variance < 0:
                    pdf.set_text_color(220, 38, 38)  # red
                else:
                    pdf.set_text_color(22, 163, 74)   # green
                item_name = ln.item_name or f"Item #{ln.item_id}"
                pdf.cell(60, 6, self._safe(item_name[:35]), fill=True)
                pdf.set_text_color(*_GRAY_700)
                pdf.cell(26, 6, str(ln.system_qty), fill=True)
                pdf.cell(26, 6, str(ln.counted_qty), fill=True)
                if variance < 0:
                    pdf.set_text_color(220, 38, 38)
                else:
                    pdf.set_text_color(22, 163, 74)
                pdf.cell(26, 6, f"{variance:+d}", fill=True)
                pdf.cell(24, 6, f"{var_pct:+.1f}%", fill=True)
                pdf.set_text_color(*_GRAY_700)
                pdf.cell(24, 6, status, fill=True)
                pdf.ln()
        else:
            self._empty_msg(pdf, "No discrepancies found — all counts match system records.")

        self._footer_line(pdf)
        return self._save_pdf(pdf, output_path, "discrepancy_report")

    def generate_barcode_labels(self, output_path: str | None = None) -> str:
        """Generate printable barcode label sheets for all items with barcodes."""
        from app.services.barcode_gen_service import BarcodeGenService
        bc_svc = BarcodeGenService()

        items = self._item_repo.get_all_items()
        items_with_bc = [i for i in items if i.barcode]

        if not items_with_bc:
            # Create a simple "no barcodes" PDF
            pdf = self._create_pdf()
            pdf.add_page()
            self._header(pdf, t("report_barcode_title"), "Printable barcode label sheets")
            self._empty_msg(pdf, "No items have barcodes assigned. "
                                 "Use the Barcode Generator page to assign barcodes first.")
            self._footer_line(pdf)
            return self._save_pdf(pdf, output_path, "barcode_labels")

        # Build BarcodeEntry list from existing barcodes
        from app.services.barcode_gen_service import BarcodeEntry, _to_code39
        entries = []
        for item in items_with_bc:
            code39 = _to_code39(item.barcode)
            entries.append(BarcodeEntry(
                item_id=item.id,
                barcode_text=code39,
                db_text=item.barcode,
                display_label=item.display_name,
                brand=item.brand or "",
                part_type=item.part_type_name or "",
            ))

        pdf_bytes = bc_svc.create_pdf(entries, include_commands=False)
        if output_path is None:
            import tempfile
            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(Path(tempfile.gettempdir()) / f"barcode_labels_{now}.pdf")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
        return output_path

    # ════════════════════════════════════════════════════════════════════════
    # DESIGN COMPONENTS
    # ════════════════════════════════════════════════════════════════════════

    def _create_pdf(self) -> SafePDF:
        pdf = SafePDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_left_margin(12)
        pdf.set_right_margin(12)
        pdf.set_top_margin(12)
        return pdf

    # ── Header banner ────────────────────────────────────────────────────────

    def _header(self, pdf: SafePDF, title: str, subtitle: str = "") -> None:
        """Modern header with colored accent bar and shop branding."""
        x0 = pdf.get_x()
        y0 = pdf.get_y()

        # Accent bar (full width emerald strip)
        pdf.set_fill_color(*_PRIMARY)
        pdf.rect(0, 0, 210, 4, "F")

        # Shop name + date (right-aligned date)
        pdf.set_y(10)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*_GRAY_600)
        pdf.cell(0, 5, self._config.name, ln=False)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(0, 5, datetime.now().strftime("%B %d, %Y"), ln=True, align="R")

        if self._config.contact_info:
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*_GRAY_400)
            pdf.cell(0, 3, self._config.contact_info, ln=True)

        # Separator line
        pdf.ln(3)
        pdf.set_draw_color(*_GRAY_200)
        pdf.line(12, pdf.get_y(), 198, pdf.get_y())
        pdf.ln(5)

        # Report title
        pdf.set_font("Helvetica", "B", 20)
        pdf.set_text_color(*_DARK)
        pdf.cell(0, 10, title, ln=True)

        # Subtitle
        if subtitle:
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*_GRAY_600)
            pdf.cell(0, 5, subtitle, ln=True)

        pdf.ln(6)

    # ── KPI cards row ────────────────────────────────────────────────────────

    def _kpi_cards(self, pdf: SafePDF, cards: list[tuple[str, str]]) -> None:
        """Row of metric cards with background fill."""
        n = len(cards)
        gap = 3
        card_w = (_PW - gap * (n - 1)) / n
        card_h = 18
        y0 = pdf.get_y()

        for i, (label, value) in enumerate(cards):
            x = 12 + i * (card_w + gap)

            # Card background
            pdf.set_fill_color(*_GRAY_50)
            pdf.set_draw_color(*_GRAY_200)
            pdf.rounded_rect(x, y0, card_w, card_h, 2, "DF")

            # Value (large, bold)
            pdf.set_xy(x + 4, y0 + 2)
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_text_color(*_DARK)
            pdf.cell(card_w - 8, 7, value)

            # Label (small, muted)
            pdf.set_xy(x + 4, y0 + 9)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*_GRAY_600)
            pdf.cell(card_w - 8, 5, label)

        pdf.set_y(y0 + card_h + 6)

    # ── Section title ────────────────────────────────────────────────────────

    def _section_title(self, pdf: SafePDF, text: str) -> None:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*_DARK)
        pdf.cell(0, 7, text, ln=True)

        # Thin emerald underline
        y = pdf.get_y()
        pdf.set_draw_color(*_PRIMARY)
        pdf.set_line_width(0.6)
        pdf.line(12, y, 60, y)
        pdf.set_line_width(0.2)
        pdf.ln(3)

    # ── Empty message ────────────────────────────────────────────────────────

    def _empty_msg(self, pdf: SafePDF, text: str) -> None:
        pdf.ln(10)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(*_GRAY_400)
        pdf.cell(0, 8, text, ln=True, align="C")

    # ── Footer ───────────────────────────────────────────────────────────────

    def _footer_line(self, pdf: SafePDF) -> None:
        pdf.ln(8)
        y = pdf.get_y()
        pdf.set_draw_color(*_GRAY_200)
        pdf.line(12, y, 198, y)
        pdf.ln(3)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*_GRAY_400)
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        pdf.cell(0, 4, f"Generated by Stock Manager Pro  |  {now}", ln=True, align="C")

    # ════════════════════════════════════════════════════════════════════════
    # TABLE RENDERERS
    # ════════════════════════════════════════════════════════════════════════

    def _table_header(self, pdf: SafePDF, cols: list[tuple[str, float, str]]) -> None:
        """Draw a styled table header row. cols = [(label, width, align), ...]"""
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_fill_color(*_DARK)
        pdf.set_text_color(*_WHITE)
        pdf.set_draw_color(*_DARK)
        rh = 7
        for label, w, align in cols:
            pdf.cell(w, rh, f"  {label}", border=0, fill=True, align="L" if align == "L" else align)
        pdf.ln(rh)

    def _table_row(self, pdf: SafePDF, cells: list[tuple[str, float, str]],
                   idx: int, row_h: float = 6.5) -> None:
        """Draw a single alternating table row."""
        bg = _WHITE if idx % 2 == 0 else _GRAY_50
        pdf.set_fill_color(*bg)
        pdf.set_draw_color(*_GRAY_200)
        pdf.set_text_color(*_GRAY_800)
        pdf.set_font("Helvetica", "", 7.5)
        for val, w, align in cells:
            pdf.cell(w, row_h, f"  {val}" if align == "L" else val,
                     border="B", fill=True, align="L" if align == "L" else align)
        pdf.ln(row_h)

    # ── Inventory table ──────────────────────────────────────────────────────

    def _inventory_table(self, pdf: SafePDF, items: list) -> None:
        cols = [
            ("#",      12, "C"),
            ("Item",   72, "L"),
            ("Color",  22, "C"),
            ("Price",  24, "R"),
            ("Stock",  18, "C"),
            ("Min",    16, "C"),
            ("Diff",   18, "C"),
            ("Status", 18, "C"),
        ]
        self._table_header(pdf, cols)

        for idx, item in enumerate(items):
            diff = item.stock - item.min_stock
            diff_s = f"{diff:+d}" if item.min_stock > 0 else "-"
            if item.is_out:
                status = "OUT"
            elif item.is_low:
                status = "LOW"
            else:
                status = "OK"
            price = self._config.format_currency(item.sell_price) if item.sell_price else "-"

            cells = [
                (str(idx + 1), 12, "C"),
                (item.display_name[:45], 72, "L"),
                (item.color or "-", 22, "C"),
                (price, 24, "R"),
                (str(item.stock), 18, "C"),
                (str(item.min_stock), 16, "C"),
                (diff_s, 18, "C"),
                (status, 18, "C"),
            ]
            # Color the status text
            y_before = pdf.get_y()
            self._table_row(pdf, cells[:-1], idx)

            # Overwrite status with colored badge
            pdf.set_xy(12 + sum(c[1] for c in cols[:-1]), y_before)
            if status == "OUT":
                pdf.set_text_color(*_RED_TXT)
                pdf.set_font("Helvetica", "B", 7.5)
            elif status == "LOW":
                pdf.set_text_color(180, 120, 0)
                pdf.set_font("Helvetica", "B", 7.5)
            else:
                pdf.set_text_color(*_GREEN_TXT)
                pdf.set_font("Helvetica", "", 7.5)
            bg = _WHITE if idx % 2 == 0 else _GRAY_50
            pdf.set_fill_color(*bg)
            pdf.cell(18, 6.5, status, border="B", fill=True, align="C")

    # ── Low stock table ──────────────────────────────────────────────────────

    def _low_stock_table(self, pdf: SafePDF, items: list) -> None:
        cols = [
            ("#",       10, "C"),
            ("Item",    62, "L"),
            ("Stock",   18, "C"),
            ("Min",     18, "C"),
            ("Deficit", 20, "C"),
            ("% of Min",20, "C"),
            ("Urgency", 24, "C"),
        ]
        self._table_header(pdf, cols)

        for idx, item in enumerate(items):
            diff = item.stock - item.min_stock
            pct = int(item.stock / item.min_stock * 100) if item.min_stock > 0 else 0
            if item.is_out:
                urgency = "CRITICAL"
            elif pct < 25:
                urgency = "CRITICAL"
            elif pct < 50:
                urgency = "HIGH"
            else:
                urgency = "MEDIUM"

            cells = [
                (str(idx + 1), 10, "C"),
                (item.display_name[:38], 62, "L"),
                (str(item.stock), 18, "C"),
                (str(item.min_stock), 18, "C"),
                (str(diff), 20, "C"),
                (f"{pct}%", 20, "C"),
            ]

            y_before = pdf.get_y()
            self._table_row(pdf, cells, idx)

            # Urgency badge with color
            pdf.set_xy(12 + sum(c[1] for c in cols[:-1]), y_before)
            if urgency == "CRITICAL":
                pdf.set_text_color(*_RED_TXT)
                pdf.set_font("Helvetica", "B", 7)
            elif urgency == "HIGH":
                pdf.set_text_color(180, 120, 0)
                pdf.set_font("Helvetica", "B", 7)
            else:
                pdf.set_text_color(*_GRAY_600)
                pdf.set_font("Helvetica", "", 7)
            bg = _WHITE if idx % 2 == 0 else _GRAY_50
            pdf.set_fill_color(*bg)
            pdf.cell(24, 6.5, urgency, border="B", fill=True, align="C")

    # ── Transactions table ───────────────────────────────────────────────────

    def _transactions_table(self, pdf: SafePDF, txns: list) -> None:
        cols = [
            ("Date",   24, "L"),
            ("Item",   58, "L"),
            ("Type",   18, "C"),
            ("Qty",    16, "C"),
            ("Before", 18, "C"),
            ("After",  18, "C"),
            ("Change", 18, "C"),
            ("Note",   30, "L"),
        ]
        self._table_header(pdf, cols)

        for idx, tx in enumerate(txns):
            d = tx.stock_after - tx.stock_before
            ds = f"{d:+d}"
            date_s = tx.timestamp[:10] if tx.timestamp else "-"
            note = (tx.note or "-")[:20]

            cells_before = [
                (date_s, 24, "L"),
                (tx.display_name[:35], 58, "L"),
            ]

            y_before = pdf.get_y()

            # Draw regular cells first
            bg = _WHITE if idx % 2 == 0 else _GRAY_50
            pdf.set_fill_color(*bg)
            pdf.set_draw_color(*_GRAY_200)
            pdf.set_text_color(*_GRAY_800)
            pdf.set_font("Helvetica", "", 7.5)
            for val, w, align in cells_before:
                pdf.cell(w, 6.5, f"  {val}" if align == "L" else val,
                         border="B", fill=True, align="L" if align == "L" else align)

            # Operation type with color
            op = tx.operation
            if op == "IN":
                pdf.set_text_color(*_GREEN_TXT)
            elif op == "OUT":
                pdf.set_text_color(*_RED_TXT)
            else:
                pdf.set_text_color(*_GRAY_600)
            pdf.set_font("Helvetica", "B", 7)
            pdf.cell(18, 6.5, op, border="B", fill=True, align="C")

            # Remaining cells
            pdf.set_text_color(*_GRAY_800)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.cell(16, 6.5, str(tx.quantity), border="B", fill=True, align="C")
            pdf.cell(18, 6.5, str(tx.stock_before), border="B", fill=True, align="C")
            pdf.cell(18, 6.5, str(tx.stock_after), border="B", fill=True, align="C")

            # Change with color
            if d >= 0:
                pdf.set_text_color(*_GREEN_TXT)
            else:
                pdf.set_text_color(*_RED_TXT)
            pdf.set_font("Helvetica", "B", 7.5)
            pdf.cell(18, 6.5, ds, border="B", fill=True, align="C")

            # Note
            pdf.set_text_color(*_GRAY_400)
            pdf.set_font("Helvetica", "", 6.5)
            pdf.cell(30, 6.5, f"  {note}", border="B", fill=True, align="L")

            pdf.ln(6.5)

    # ── Audit table ────────────────────────────────────────────────────────

    def _audit_table(self, pdf: SafePDF, items: list) -> None:
        """Render audit-style table with blank columns for physical count."""
        cols = [
            ("#",        10, "C"),
            ("Item",     60, "L"),
            ("Barcode",  32, "L"),
            ("System",   18, "C"),
            ("Actual",   22, "C"),
            ("Diff",     18, "C"),
            ("Notes",    26, "L"),
        ]
        self._table_header(pdf, cols)

        for idx, item in enumerate(items):
            bc_display = (item.barcode or "-")[:18]
            cells = [
                (str(idx + 1), 10, "C"),
                (item.display_name[:36], 60, "L"),
                (bc_display, 32, "L"),
                (str(item.stock), 18, "C"),
                ("", 22, "C"),        # blank for actual count
                ("", 18, "C"),        # blank for diff
                ("", 26, "L"),        # blank for notes
            ]
            self._table_row(pdf, cells, idx, row_h=7)

            # Page break check (leave room for footer)
            if pdf.get_y() > 265:
                self._footer_line(pdf)
                pdf.add_page()
                self._table_header(pdf, cols)

    # ════════════════════════════════════════════════════════════════════════
    # SAVE
    # ════════════════════════════════════════════════════════════════════════

    def _save_pdf(self, pdf: SafePDF, output_path: str | None,
                  filename_base: str) -> str:
        if output_path is None:
            temp_dir = tempfile.gettempdir()
            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(Path(temp_dir) / f"{filename_base}_{now}.pdf")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        pdf.output(output_path)
        return output_path
