"""
app/services/scan_invoice_service.py — PDF invoices for Quick Scan sessions.

Two layouts:
    - A4 (portrait): professional full-page invoice for customer sales
    - Thermal (80 mm): compact receipt-style strip for quick stock records

Input: an invoice id saved by InvoiceRepository.
Output: path to the written PDF (also saved back to scan_invoices.pdf_path).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from datetime import datetime
from fpdf import FPDF

from app.repositories.invoice_repo import InvoiceRepository
from app.core.config import ShopConfig

# ── Latin-1 safe text (same approach as ReceiptService) ─────────────────────
_UMAP = {
    "\u20ac": "EUR", "\u2013": "-", "\u2014": "--",
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2022": "*", "\u2026": "...", "\u00b7": ".",
}


def _lat(text: str) -> str:
    for k, v in _UMAP.items():
        text = text.replace(k, v)
    return text.encode("latin-1", errors="replace").decode("latin-1")


class _InvoicePDF(FPDF):
    def cell(self, w=0, h=0, txt="", border=0, ln=0, align="", fill=False):
        return super().cell(w, h, _lat(str(txt)), border, ln, align, fill)

    def multi_cell(self, w, h=0, txt="", border=0, align="", fill=False):
        return super().multi_cell(w, h, _lat(str(txt)), border, align, fill)


# ── Colors ──────────────────────────────────────────────────────────────────
_PRIMARY = (16, 185, 129)    # emerald
_DARK = (15, 23, 42)         # slate-900
_MUTED = (100, 116, 139)     # slate-500
_LINE = (203, 213, 225)      # slate-300
_LIGHT = (241, 245, 249)     # slate-100
_ACCENT = (74, 158, 255)     # blue
_RED = (239, 68, 68)         # rose
_WHITE = (255, 255, 255)


def _output_dir() -> Path:
    """Where PDFs are written. Same tree used by installer cache & backups."""
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        base = str(Path.home() / "AppData" / "Local")
    root = Path(base) / "StockPro" / "StockManagerPro" / "invoices"
    root.mkdir(parents=True, exist_ok=True)
    return root


class ScanInvoiceService:
    """Render a scan-session invoice to PDF in A4 or thermal layout."""

    def __init__(self) -> None:
        self._repo = InvoiceRepository()

    # ── Public API ───────────────────────────────────────────────────────────

    def generate(self, invoice_id: int) -> str:
        """Render the invoice whose id is provided. Returns the file path."""
        result = self._repo.get_invoice(invoice_id)
        if not result:
            raise ValueError(f"Invoice #{invoice_id} not found")
        header, lines = result

        layout = (header.get("layout") or "a4").lower()
        if layout == "thermal":
            path = self._generate_thermal(header, lines)
        else:
            path = self._generate_a4(header, lines)

        try:
            self._repo.set_pdf_path(invoice_id, path)
        except Exception:
            pass
        return path

    # ── A4 invoice ───────────────────────────────────────────────────────────

    def _generate_a4(self, header: dict, lines: list[dict]) -> str:
        cfg = ShopConfig.get()
        currency = header.get("currency") or cfg.currency or "EUR"
        op = (header.get("operation") or "OUT").upper()
        title = "INVOICE" if op == "OUT" else "STOCK RECEIPT"

        pdf = _InvoicePDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_margins(15, 15, 15)
        pdf.add_page()
        pw = 210 - 30  # usable width

        # ── Top bar (brand strip) ──
        pdf.set_fill_color(*_PRIMARY)
        pdf.rect(0, 0, 210, 10, "F")

        # ── Shop header ──
        pdf.set_y(16)
        pdf.set_font("Helvetica", "B", 20)
        pdf.set_text_color(*_DARK)
        pdf.cell(pw * 0.6, 9, cfg.name or "Stock Manager Pro", 0, 0, "L")
        # Title on the right
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(*_PRIMARY)
        pdf.cell(pw * 0.4, 9, title, 0, 1, "R")

        if cfg.contact_info:
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*_MUTED)
            pdf.cell(pw * 0.6, 5, cfg.contact_info, 0, 0, "L")
            pdf.cell(0, 5, "", 0, 1)

        # Separator
        pdf.ln(4)
        pdf.set_draw_color(*_LINE)
        pdf.set_line_width(0.3)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(6)

        # ── Invoice metadata ──
        label_w = 30
        value_w = (pw / 2) - label_w
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*_DARK)
        pdf.cell(label_w, 6, "Number:", 0, 0, "L")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(value_w, 6, header.get("invoice_number", ""), 0, 0, "L")

        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(label_w, 6, "Date:", 0, 0, "L")
        pdf.set_font("Helvetica", "", 10)
        created = header.get("created_at") or ""
        if created:
            created = created[:16]
        pdf.cell(value_w, 6, created, 0, 1, "L")

        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(label_w, 6, "Operation:", 0, 0, "L")
        pdf.set_font("Helvetica", "", 10)
        op_label = "Sale (takeout)" if op == "OUT" else "Stock in (insert)"
        pdf.cell(value_w, 6, op_label, 0, 0, "L")

        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(label_w, 6, "Currency:", 0, 0, "L")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(value_w, 6, currency, 0, 1, "L")
        pdf.ln(4)

        # ── Customer block ──
        customer = (header.get("customer_name") or "").strip()
        pdf.set_draw_color(*_LINE)
        pdf.set_fill_color(*_LIGHT)
        pdf.rect(15, pdf.get_y(), pw, 16, "FD")
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_MUTED)
        pdf.set_xy(18, pdf.get_y() + 2)
        pdf.cell(pw - 6, 5, "BILL TO", 0, 1, "L")
        pdf.set_x(18)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*_DARK)
        pdf.cell(pw - 6, 6, customer if customer else "Walk-in / Stock record", 0, 1, "L")
        pdf.ln(8)

        # ── Items table ──
        col_widths = {
            "item": pw * 0.46,
            "barcode": pw * 0.20,
            "qty": pw * 0.08,
            "unit": pw * 0.12,
            "total": pw * 0.14,
        }
        # Header row
        pdf.set_fill_color(*_DARK)
        pdf.set_text_color(*_WHITE)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(col_widths["item"], 8, "ITEM", 0, 0, "L", True)
        pdf.cell(col_widths["barcode"], 8, "BARCODE", 0, 0, "L", True)
        pdf.cell(col_widths["qty"], 8, "QTY", 0, 0, "C", True)
        pdf.cell(col_widths["unit"], 8, "UNIT", 0, 0, "R", True)
        pdf.cell(col_widths["total"], 8, "TOTAL", 0, 1, "R", True)

        # Rows
        pdf.set_text_color(*_DARK)
        pdf.set_font("Helvetica", "", 9)
        alt = False
        for line in lines:
            if alt:
                pdf.set_fill_color(*_LIGHT)
                fill = True
            else:
                fill = False
            alt = not alt
            name = str(line.get("item_snapshot", ""))
            if len(name) > 48:
                name = name[:46] + "..."
            bc = str(line.get("barcode", ""))
            if len(bc) > 18:
                bc = bc[:16] + ".."
            pdf.cell(col_widths["item"], 7, name, 0, 0, "L", fill)
            pdf.cell(col_widths["barcode"], 7, bc, 0, 0, "L", fill)
            pdf.cell(col_widths["qty"], 7, str(line.get("quantity", 0)), 0, 0, "C", fill)
            pdf.cell(col_widths["unit"], 7, f"{float(line.get('unit_price', 0)):,.2f}", 0, 0, "R", fill)
            pdf.cell(col_widths["total"], 7, f"{float(line.get('line_total', 0)):,.2f}", 0, 1, "R", fill)

        pdf.ln(4)
        pdf.set_draw_color(*_LINE)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(4)

        # ── Totals box ──
        totals_w = pw * 0.4
        start_x = 15 + pw - totals_w

        subtotal = float(header.get("subtotal", 0))
        total = float(header.get("total", subtotal))

        pdf.set_x(start_x)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*_MUTED)
        pdf.cell(totals_w * 0.55, 6, "Subtotal", 0, 0, "L")
        pdf.set_text_color(*_DARK)
        pdf.cell(totals_w * 0.45, 6, f"{subtotal:,.2f} {currency}", 0, 1, "R")

        # Grand total — emphasised
        pdf.ln(1)
        pdf.set_draw_color(*_PRIMARY)
        pdf.set_line_width(0.6)
        pdf.line(start_x, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(2)
        pdf.set_x(start_x)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*_DARK)
        pdf.cell(totals_w * 0.55, 9, "TOTAL", 0, 0, "L")
        pdf.set_text_color(*_PRIMARY)
        pdf.cell(totals_w * 0.45, 9, f"{total:,.2f} {currency}", 0, 1, "R")

        # ── Footer ──
        pdf.set_y(-30)
        pdf.set_draw_color(*_LINE)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(3)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(*_MUTED)
        footer_line = "Thank you for your business." if op == "OUT" else "Stock received successfully."
        pdf.cell(pw, 4, footer_line, 0, 1, "C")
        pdf.cell(pw, 4, (cfg.name or "") + ("  —  " + cfg.contact_info if cfg.contact_info else ""),
                 0, 1, "C")
        note = (header.get("note") or "").strip()
        if note:
            pdf.cell(pw, 4, f"Note: {note}", 0, 1, "C")

        # Write
        path = _output_dir() / f"{header['invoice_number']}.pdf"
        pdf.output(str(path))
        return str(path)

    # ── Thermal 80 mm receipt ────────────────────────────────────────────────

    def _generate_thermal(self, header: dict, lines: list[dict]) -> str:
        cfg = ShopConfig.get()
        currency = header.get("currency") or cfg.currency or "EUR"
        op = (header.get("operation") or "OUT").upper()
        title = "INVOICE" if op == "OUT" else "STOCK RECEIPT"

        pdf = _InvoicePDF(orientation="P", unit="mm", format=(80, 240))
        pdf.set_auto_page_break(auto=True, margin=5)
        pdf.set_margins(3, 3, 3)
        pdf.add_page()
        pw = 80 - 6

        # ── Shop Header ──
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*_DARK)
        pdf.cell(pw, 6, cfg.name or "Stock Manager Pro", 0, 1, "C")
        if cfg.contact_info:
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*_MUTED)
            pdf.cell(pw, 4, cfg.contact_info, 0, 1, "C")

        pdf.ln(1)
        pdf.set_draw_color(*_LINE)
        pdf.set_line_width(0.2)
        pdf.line(3, pdf.get_y(), 77, pdf.get_y())
        pdf.ln(1)

        # Title badge
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*_PRIMARY)
        pdf.cell(pw, 5, title, 0, 1, "C")
        pdf.ln(1)

        # Metadata
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*_DARK)
        pdf.cell(pw / 2, 4, header.get("invoice_number", ""), 0, 0, "L")
        created = (header.get("created_at") or "")[:16]
        pdf.cell(pw / 2, 4, created, 0, 1, "R")

        customer = (header.get("customer_name") or "").strip()
        if customer:
            pdf.cell(pw, 4, f"Customer: {customer}", 0, 1)

        pdf.ln(1)
        pdf.line(3, pdf.get_y(), 77, pdf.get_y())
        pdf.ln(1)

        # Items
        pdf.set_fill_color(*_LIGHT)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*_DARK)
        pdf.cell(36, 5, "Item", 0, 0, "L", True)
        pdf.cell(8, 5, "Qty", 0, 0, "C", True)
        pdf.cell(14, 5, "Unit", 0, 0, "R", True)
        pdf.cell(pw - 58, 5, "Total", 0, 1, "R", True)

        pdf.set_font("Helvetica", "", 7)
        for line in lines:
            name = str(line.get("item_snapshot", ""))
            if len(name) > 22:
                name = name[:20] + ".."
            pdf.cell(36, 4.5, name)
            pdf.cell(8, 4.5, str(line.get("quantity", 0)), 0, 0, "C")
            pdf.cell(14, 4.5, f"{float(line.get('unit_price', 0)):,.2f}", 0, 0, "R")
            pdf.cell(pw - 58, 4.5, f"{float(line.get('line_total', 0)):,.2f}", 0, 1, "R")

        pdf.ln(1)
        pdf.line(3, pdf.get_y(), 77, pdf.get_y())
        pdf.ln(2)

        # Totals
        subtotal = float(header.get("subtotal", 0))
        total = float(header.get("total", subtotal))

        pdf.set_font("Helvetica", "", 8)
        pdf.cell(pw - 25, 4.5, "Subtotal:", 0, 0, "R")
        pdf.cell(25, 4.5, f"{subtotal:,.2f} {currency}", 0, 1, "R")

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*_PRIMARY)
        pdf.cell(pw - 25, 6, "TOTAL:", 0, 0, "R")
        pdf.cell(25, 6, f"{total:,.2f} {currency}", 0, 1, "R")

        # Footer
        pdf.ln(3)
        pdf.set_draw_color(*_LINE)
        pdf.line(3, pdf.get_y(), 77, pdf.get_y())
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 6)
        pdf.set_text_color(*_MUTED)
        footer = "Thank you for your purchase!" if op == "OUT" else "Stock received."
        pdf.cell(pw, 3, footer, 0, 1, "C")
        pdf.cell(pw, 3, cfg.name or "", 0, 1, "C")

        path = _output_dir() / f"{header['invoice_number']}.pdf"
        pdf.output(str(path))
        return str(path)
