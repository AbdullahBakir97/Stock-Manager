"""app/services/receipt_service.py — Professional receipt/invoice generation."""
from __future__ import annotations

import tempfile
from pathlib import Path
from datetime import datetime
from fpdf import FPDF

from app.repositories.sale_repo import SaleRepository
from app.services.customer_service import CustomerService
from app.core.config import ShopConfig
from app.core.i18n import t

# ── Latin-1 safe text ────────────────────────────────────────────────────────
_UMAP = {
    "\u20ac": "EUR", "\u2013": "-", "\u2014": "--",
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2022": "*", "\u2026": "...", "\u00b7": ".",
}


def _lat(text: str) -> str:
    for k, v in _UMAP.items():
        text = text.replace(k, v)
    return text.encode("latin-1", errors="replace").decode("latin-1")


class _ReceiptPDF(FPDF):
    def cell(self, w=0, h=0, txt="", border=0, ln=0, align="", fill=False):
        return super().cell(w, h, _lat(str(txt)), border, ln, align, fill)

    def multi_cell(self, w, h=0, txt="", border=0, align="", fill=False):
        return super().multi_cell(w, h, _lat(str(txt)), border, align, fill)


# ── Colors ───────────────────────────────────────────────────────────────────
_PRIMARY = (16, 185, 129)
_DARK = (15, 23, 42)
_GRAY = (100, 116, 139)
_LIGHT = (241, 245, 249)
_WHITE = (255, 255, 255)


class ReceiptService:
    """Generates professional PDF receipts for completed sales."""

    def __init__(self) -> None:
        self._sales = SaleRepository()
        self._custs = CustomerService()

    def generate_receipt(self, sale_id: int, output_path: str = "") -> str:
        """Generate a receipt PDF for a given sale. Returns the file path."""
        sale = self._sales.get_by_id(sale_id)
        if not sale:
            raise ValueError(f"Sale #{sale_id} not found")

        cfg = ShopConfig.get()
        pdf = _ReceiptPDF(orientation="P", unit="mm", format=(80, 200))
        pdf.set_auto_page_break(auto=True, margin=5)
        pdf.add_page()
        pw = 80 - 6  # usable width (3mm margin each side)
        pdf.set_margins(3, 3, 3)

        # ── Shop Header ──
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*_DARK)
        pdf.cell(pw, 6, cfg.name or "Stock Manager Pro", 0, 1, "C")

        if cfg.contact_info:
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*_GRAY)
            pdf.cell(pw, 4, cfg.contact_info, 0, 1, "C")

        # Separator
        pdf.ln(2)
        pdf.set_draw_color(*_GRAY)
        pdf.set_line_width(0.2)
        pdf.line(3, pdf.get_y(), 77, pdf.get_y())
        pdf.ln(2)

        # ── Receipt Info ──
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*_DARK)
        pdf.cell(pw / 2, 4, f"Receipt #{sale.id}")
        pdf.cell(pw / 2, 4, sale.timestamp[:16] if sale.timestamp else "", 0, 1, "R")

        if sale.customer_name:
            pdf.cell(pw, 4, f"Customer: {sale.customer_name}", 0, 1)

        pdf.ln(2)

        # ── Items Table ──
        # Header
        pdf.set_fill_color(*_LIGHT)
        pdf.set_font("Helvetica", "B", 7)
        pdf.cell(32, 5, "Item", 0, 0, "", True)
        pdf.cell(10, 5, "Qty", 0, 0, "C", True)
        pdf.cell(16, 5, "Price", 0, 0, "R", True)
        pdf.cell(pw - 58, 5, "Total", 0, 1, "R", True)

        # Items
        pdf.set_font("Helvetica", "", 7)
        for item in sale.items:
            name = item.item_name or f"Item #{item.item_id}"
            if len(name) > 18:
                name = name[:16] + ".."
            pdf.cell(32, 4.5, name)
            pdf.cell(10, 4.5, str(item.quantity), 0, 0, "C")
            pdf.cell(16, 4.5, f"{item.unit_price:,.2f}", 0, 0, "R")
            pdf.cell(pw - 58, 4.5, f"{item.line_total:,.2f}", 0, 1, "R")

        # Separator
        pdf.ln(1)
        pdf.line(3, pdf.get_y(), 77, pdf.get_y())
        pdf.ln(2)

        # ── Totals ──
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(pw - 25, 4.5, "Subtotal:", 0, 0, "R")
        pdf.cell(25, 4.5, f"{sale.total_amount:,.2f} {cfg.currency}", 0, 1, "R")

        if sale.discount > 0:
            pdf.set_text_color(220, 38, 38)
            pdf.cell(pw - 25, 4.5, "Discount:", 0, 0, "R")
            pdf.cell(25, 4.5, f"-{sale.discount:,.2f} {cfg.currency}", 0, 1, "R")
            pdf.set_text_color(*_DARK)

        # Net total (bold)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(pw - 25, 6, "TOTAL:", 0, 0, "R")
        pdf.cell(25, 6, f"{sale.net_total:,.2f} {cfg.currency}", 0, 1, "R")

        # ── Footer ──
        pdf.ln(3)
        pdf.set_draw_color(*_GRAY)
        pdf.line(3, pdf.get_y(), 77, pdf.get_y())
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 6)
        pdf.set_text_color(*_GRAY)
        pdf.cell(pw, 3, "Thank you for your purchase!", 0, 1, "C")
        pdf.cell(pw, 3, cfg.name or "", 0, 1, "C")

        if sale.note:
            pdf.ln(1)
            pdf.set_font("Helvetica", "I", 6)
            pdf.cell(pw, 3, f"Note: {sale.note}", 0, 1, "C")

        # Output
        if not output_path:
            tmp = tempfile.mktemp(suffix=".pdf", prefix=f"receipt_{sale_id}_")
            output_path = tmp

        pdf.output(output_path)
        return output_path
