"""
app/services/report_service.py — Professional PDF report generation (fpdf2).

Design:
    - One _ReportPDF subclass overrides header()/footer() so every page
      gets the shop banner + title subtitle + page numbers automatically.
    - Page numbers rendered via fpdf2's {nb} alias after alias_nb_pages().
    - Logo (ShopConfig.logo_path) rendered top-left of the header when
      available.
    - All tables have per-page pagination and redraw their column
      headers on new pages.
    - All currency rendered via ShopConfig.format_currency().
    - All unicode passes through _latin1() before hitting fpdf2 (which
      is natively Latin-1).

12 report types (7 existing, 5 new):
    Existing: inventory, low_stock, transactions, summary, audit,
              discrepancy, barcode_labels
    New:      valuation, sales, scan_invoices, expiring,
              category_performance

Each public method returns the absolute PDF path so the UI can offer
"Open" and "Open folder" actions.
"""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fpdf import FPDF

from app.repositories.item_repo import ItemRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.audit_repo import AuditRepository
from app.repositories.category_repo import CategoryRepository
from app.core.config import ShopConfig
from app.core.i18n import t


# ── Latin-1 safe FPDF subclass ──────────────────────────────────────────────
_UMAP = {
    "\u20ac": "EUR", "\u2013": "-", "\u2014": "--",
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2022": "*", "\u2026": "...", "\u00b7": ".",
}


def _latin1(text: str) -> str:
    """Sanitise any string for fpdf2 (which uses latin-1 fonts)."""
    if text is None:
        return ""
    s = str(text)
    for k, v in _UMAP.items():
        s = s.replace(k, v)
    return s.encode("latin-1", errors="replace").decode("latin-1")


# ── Brand colours ───────────────────────────────────────────────────────────
_PRIMARY    = (16, 185, 129)   # Emerald (#10B981)
_PRIMARY_DK = (5, 150, 105)
_DARK       = (15, 23, 42)
_GRAY_800   = (30, 41, 59)
_GRAY_700   = (51, 65, 85)
_GRAY_600   = (71, 85, 105)
_GRAY_400   = (148, 163, 184)
_GRAY_200   = (226, 232, 240)
_GRAY_100   = (241, 245, 249)
_GRAY_50    = (248, 250, 252)
_WHITE      = (255, 255, 255)
_RED        = (239, 68, 68)
_RED_TXT    = (220, 38, 38)
_AMBER      = (245, 158, 11)
_GREEN_TXT  = (5, 150, 105)

_PAGE_W = 210               # A4 portrait
_MARGIN_L = 12
_MARGIN_R = 12
_MARGIN_T = 28              # extra room for header banner
_MARGIN_B = 16              # extra room for footer with page numbers
_PW = _PAGE_W - _MARGIN_L - _MARGIN_R   # 186 mm usable width
_CONTENT_BOTTOM = 297 - _MARGIN_B        # A4 height (297) minus bottom margin


class _ReportPDF(FPDF):
    """fpdf2 subclass that draws a shop-branded header + numbered footer
    on EVERY page. Set `title_text`, `subtitle_text`, and `shop_cfg` before
    calling add_page() to drive the header contents."""

    title_text: str = ""
    subtitle_text: str = ""
    shop_cfg: Optional[ShopConfig] = None

    # ── Latin-1 safety ─────────────────────────────────────────────────────
    def cell(self, w=0, h=0, txt="", *a, **kw):
        return super().cell(w, h, _latin1(txt), *a, **kw)

    def multi_cell(self, w, h=0, txt="", *a, **kw):
        return super().multi_cell(w, h, _latin1(txt), *a, **kw)

    def rounded_rect(self, x, y, w, h, r=0, style="", *a, **kw):
        if hasattr(super(), "rounded_rect"):
            return super().rounded_rect(x, y, w, h, r, style, *a, **kw)
        self.rect(x, y, w, h, style)

    # ── Page branding (auto on every add_page) ─────────────────────────────
    def header(self) -> None:  # noqa: D401 — fpdf2 override
        cfg = self.shop_cfg
        shop_name = (cfg.name if cfg else "") or "Stock Manager Pro"
        contact = (cfg.contact_info if cfg else "") or ""
        logo_path = (cfg.logo_path if cfg else "") or ""

        # Accent strip
        self.set_fill_color(*_PRIMARY)
        self.rect(0, 0, _PAGE_W, 4, "F")

        # Optional logo (top-left)
        logo_drawn = False
        if logo_path and os.path.exists(logo_path):
            try:
                self.image(logo_path, x=_MARGIN_L, y=7, w=14, h=14)
                logo_drawn = True
            except Exception:
                logo_drawn = False

        text_x = _MARGIN_L + (18 if logo_drawn else 0)

        # Shop name + date
        self.set_xy(text_x, 8)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*_DARK)
        self.cell(_PW - (18 if logo_drawn else 0) - 40, 5, shop_name, ln=False)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*_GRAY_600)
        self.cell(40, 5, datetime.now().strftime("%B %d, %Y"),
                  ln=True, align="R")

        # Contact line
        if contact:
            self.set_x(text_x)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(*_GRAY_400)
            self.cell(_PW - (18 if logo_drawn else 0), 3.5, contact, ln=True)

        # Separator
        self.ln(1)
        self.set_draw_color(*_GRAY_200)
        self.line(_MARGIN_L, self.get_y(), _PAGE_W - _MARGIN_R, self.get_y())
        self.ln(2.5)

        # Report title + subtitle (only on page 1)
        if self.page_no() == 1:
            self.set_font("Helvetica", "B", 20)
            self.set_text_color(*_DARK)
            self.cell(0, 9, self.title_text, ln=True)
            if self.subtitle_text:
                self.set_font("Helvetica", "", 9)
                self.set_text_color(*_GRAY_600)
                self.cell(0, 4.5, self.subtitle_text, ln=True)
            self.ln(3)
        else:
            # Compact title on continuation pages
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(*_GRAY_700)
            self.cell(0, 6, self.title_text + " (continued)", ln=True)
            self.ln(2)

    def footer(self) -> None:  # noqa: D401 — fpdf2 override
        self.set_y(-_MARGIN_B + 2)
        self.set_draw_color(*_GRAY_200)
        self.line(_MARGIN_L, self.get_y(), _PAGE_W - _MARGIN_R, self.get_y())
        self.ln(1.5)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*_GRAY_400)
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        # Left: generated stamp · Right: page n / nb
        self.cell(_PW / 2, 4,
                  f"Generated by Stock Manager Pro  |  {now}",
                  ln=False, align="L")
        self.cell(_PW / 2, 4, f"Page {self.page_no()} of {{nb}}",
                  ln=True, align="R")


# ── Output directory ────────────────────────────────────────────────────────

def _output_dir() -> Path:
    """Where reports are written. Same tree as invoices + backups."""
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        base = str(Path.home() / "AppData" / "Local")
    root = Path(base) / "StockPro" / "StockManagerPro" / "reports"
    root.mkdir(parents=True, exist_ok=True)
    return root


# ── Main service ────────────────────────────────────────────────────────────

class ReportService:
    """Generates professional PDF reports. All methods return the saved
    absolute file path. When no `output_path` is provided, writes to
    %LOCALAPPDATA%\\StockPro\\StockManagerPro\\reports\\<name>_<timestamp>.pdf.
    """

    def __init__(self) -> None:
        self._item_repo = ItemRepository()
        self._txn_repo = TransactionRepository()
        self._audit_repo = AuditRepository()
        self._cat_repo = CategoryRepository()
        self._cfg = ShopConfig.get()

    # ════════════════════════════════════════════════════════════════════════
    # PUBLIC — existing reports
    # ════════════════════════════════════════════════════════════════════════

    def generate_inventory_report(self, output_path: str | None = None,
                                  category_id: int | None = None,
                                  include_empty: bool = False) -> str:
        pdf = self._new_pdf(t("report_inventory_title"),
                            "Stock items grouped by category → part type. "
                            "(Empty placeholder rows hidden.)")
        pdf.add_page()

        items = self._item_repo.get_all_items()
        if category_id:
            items = [i for i in items
                     if getattr(i, "category_id", None) == category_id]
        # By default hide zero-stock placeholder rows — the matrix engine
        # seeds a row for every (model × part_type × color) combination,
        # so without this filter the PDF balloons to thousands of "0 stock"
        # entries that the shop doesn't actually own.
        if not include_empty:
            items = [i for i in items
                     if (i.stock or 0) > 0
                     or (i.min_stock or 0) > 0
                     or (i.inventur or 0) > 0]

        summary = self._item_repo.get_summary()
        self._kpi_cards(pdf, [
            ("Total Products", str(summary.get("total_products", 0))),
            ("Total Units",    str(summary.get("total_units", 0))),
            ("Low Stock",      str(summary.get("low_stock_count", 0))),
            ("Out of Stock",   str(summary.get("out_of_stock_count", 0))),
        ])
        if items:
            self._section_title(pdf, f"All Items ({len(items)})")
            self._inventory_table(pdf, items)
        else:
            self._empty_msg(pdf, "No inventory items found.")
        return self._save(pdf, output_path, "inventory_report")

    def generate_low_stock_report(self, output_path: str | None = None) -> str:
        pdf = self._new_pdf(t("report_low_stock_title"),
                            "Items requiring restocking, sorted by urgency")
        pdf.add_page()

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
        return self._save(pdf, output_path, "low_stock_report")

    def generate_transaction_report(self,
                                    date_from: str | None = None,
                                    date_to: str | None = None,
                                    op_filter: str = "",
                                    output_path: str | None = None) -> str:
        """Date range + operation filter. Uses get_filtered() from repo."""
        # Normalise date range
        if not date_to:
            date_to = datetime.now().strftime("%Y-%m-%d")
        if not date_from:
            date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        subtitle = f"Stock movements · {date_from}  to  {date_to}"
        if op_filter:
            subtitle += f"  ·  {op_filter}"
        pdf = self._new_pdf(t("report_txn_title"), subtitle)
        pdf.add_page()

        txns = self._txn_repo.get_filtered(
            date_from=date_from, date_to=date_to,
            operation=op_filter or "", limit=2000,
        )
        total_in = sum(tx.quantity for tx in txns if tx.operation == "IN")
        total_out = sum(tx.quantity for tx in txns if tx.operation == "OUT")
        self._kpi_cards(pdf, [
            ("Transactions", str(len(txns))),
            ("Total In",     f"+{total_in}"),
            ("Total Out",    f"-{total_out}"),
            ("Net Change",   f"{total_in - total_out:+d}"),
        ])
        if txns:
            self._section_title(pdf, f"Transactions ({len(txns)})")
            self._transactions_table(pdf, txns)
        else:
            self._empty_msg(pdf, "No transactions for the selected range.")
        return self._save(pdf, output_path, "transaction_report")

    def generate_summary_report(self, output_path: str | None = None) -> str:
        pdf = self._new_pdf(t("report_summary_title"),
                            "Executive overview of inventory health and key metrics")
        pdf.add_page()

        summary = self._item_repo.get_summary()
        low = self._item_repo.get_low_stock()
        out = [i for i in low if i.is_out]
        val = summary.get("inventory_value")
        val_str = self._cfg.format_currency(f"{val:,.2f}") if val else "-"

        self._kpi_cards(pdf, [
            ("Total Products", str(summary.get("total_products", 0))),
            ("Total Units",    str(summary.get("total_units", 0))),
            ("Inventory Value", val_str),
        ])
        pdf.ln(3)
        self._kpi_cards(pdf, [
            ("Low Stock",    str(len(low))),
            ("Out of Stock", str(len(out))),
            ("Healthy Items", str(summary.get("total_products", 0) - len(low))),
        ])
        if low:
            self._section_title(pdf, "Top Priority — Restock Needed")
            self._low_stock_table(pdf, low[:10])
        return self._save(pdf, output_path, "summary_report")

    def generate_audit_sheet(self, output_path: str | None = None) -> str:
        pdf = self._new_pdf(t("report_audit_title"),
                            "Physical stock count sheet — compare actual vs. system")
        pdf.add_page()

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
        pdf.ln(6)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*_GRAY_600)
        pdf.cell(0, 6,
                 "Counted by: ________________________    "
                 "Date: _______________    "
                 "Signature: ________________________",
                 ln=True)
        return self._save(pdf, output_path, "audit_sheet")

    def generate_discrepancy_report(self, audit_id: int | None = None,
                                    output_path: str | None = None) -> str:
        pdf = self._new_pdf(t("report_discrepancy_title"),
                            "Expected vs. actual stock — variance analysis")
        pdf.add_page()

        if audit_id:
            audit = self._audit_repo.get_by_id(audit_id)
        else:
            audits = self._audit_repo.get_all()
            completed = [a for a in audits if a.status == "COMPLETED"]
            audit = completed[0] if completed else None

        if audit is None:
            self._empty_msg(pdf, "No completed audits found. Run a stock audit first.")
            return self._save(pdf, output_path, "discrepancy_report")

        lines = self._audit_repo.get_lines(audit.id)
        discrepancies = [ln for ln in lines if ln.counted_qty != ln.system_qty]
        total_lines = len(lines)
        total_disc = len(discrepancies)
        accuracy = ((total_lines - total_disc) / total_lines * 100) if total_lines else 100
        total_shrinkage = sum((ln.system_qty - ln.counted_qty) for ln in discrepancies
                              if ln.counted_qty < ln.system_qty)
        total_surplus = sum((ln.counted_qty - ln.system_qty) for ln in discrepancies
                            if ln.counted_qty > ln.system_qty)

        self._kpi_cards(pdf, [
            ("Audit", f"#{audit.id}"),
            ("Items Counted", str(total_lines)),
            ("Discrepancies", str(total_disc)),
            ("Accuracy", f"{accuracy:.1f}%"),
        ])

        self._section_title(pdf, "Variance Summary")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*_GRAY_700)
        pdf.cell(0, 5, f"Shrinkage (system > counted): {total_shrinkage} units", ln=True)
        pdf.cell(0, 5, f"Surplus (counted > system): {total_surplus} units", ln=True)
        pdf.cell(0, 5, f"Net variance: {total_surplus - total_shrinkage:+d} units", ln=True)
        pdf.ln(4)

        if discrepancies:
            self._section_title(pdf, f"Discrepancy Details ({total_disc} items)")
            self._discrepancy_table(pdf, discrepancies)
        else:
            self._empty_msg(pdf, "No discrepancies found — all counts match system records.")
        return self._save(pdf, output_path, "discrepancy_report")

    def generate_barcode_labels(self, output_path: str | None = None) -> str:
        """Delegates to BarcodeGenService for sheet layout."""
        from app.services.barcode_gen_service import (
            BarcodeGenService, BarcodeEntry, _to_code39
        )
        bc_svc = BarcodeGenService()
        items = self._item_repo.get_all_items()
        items_with_bc = [i for i in items if i.barcode]
        if not items_with_bc:
            pdf = self._new_pdf(t("report_barcode_title"),
                                "Printable barcode label sheets")
            pdf.add_page()
            self._empty_msg(pdf,
                            "No items have barcodes assigned. "
                            "Use the Barcode Generator page to assign barcodes first.")
            return self._save(pdf, output_path, "barcode_labels")

        entries = []
        for item in items_with_bc:
            code39 = _to_code39(item.barcode)
            entries.append(BarcodeEntry(
                item_id=item.id,
                barcode_text=code39,
                db_text=item.barcode,
                display_label=item.display_name,
            ))
        # Build a temp path if caller didn't specify
        if output_path is None:
            output_path = str(_output_dir() /
                              f"barcode_labels_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        bc_svc.create_pdf(entries, output_path)
        return output_path

    # ════════════════════════════════════════════════════════════════════════
    # PUBLIC — NEW reports
    # ════════════════════════════════════════════════════════════════════════

    def generate_valuation_report(self, output_path: str | None = None) -> str:
        """Stock total price split by part type & grouped under categories
        + grand total. Also includes a per-brand summary so the user can
        see total value per brand at a glance.

        Structure:
            KPIs
            Per-brand summary table (brand → SKUs, units, stock value)
            For each category:
                Per-part-type table (part type → SKUs, units, avg price,
                                     stock value), with brand subtotals
                                     inside when multiple brands hold items.
            Grand-total emerald bar.
        """
        pdf = self._new_pdf("Stock Valuation",
                            "Stock value per brand / category / part type")
        pdf.add_page()

        cats = self._cat_repo.get_all_active()
        items = self._item_repo.get_all_items()

        # Resolve price (per-item > part-type default > 0)
        pt_default: dict[int, float | None] = {}
        for c in cats:
            for pt in c.part_types:
                pt_default[pt.id] = (float(pt.default_price)
                                     if pt.default_price is not None else None)

        def _price(it) -> float:
            if it.sell_price is not None:
                return float(it.sell_price)
            d = pt_default.get(getattr(it, "part_type_id", None) or 0)
            return d if d is not None else 0.0

        # Aggregate by (category_id, part_type_id)
        agg: dict[tuple[int, int], dict] = {}
        # Aggregate by brand for the top summary
        brand_agg: dict[str, dict] = {}
        # Aggregate by (brand, part_type_id) — enables per-brand subtotals
        # inside each part-type row group (nice-to-have)
        bp_agg: dict[tuple[str, int], dict] = {}

        for it in items:
            ptid = getattr(it, "part_type_id", None)
            if ptid is None:
                continue
            cid = None
            for c in cats:
                for pt in c.part_types:
                    if pt.id == ptid:
                        cid = c.id
                        break
                if cid is not None:
                    break
            if cid is None:
                continue
            brand = self._resolve_brand(it)
            units = it.stock or 0
            val = units * _price(it)
            # Only count SKUs that actually hold stock — avoids the
            # misleading "thousands of SKUs" count from zero-stock
            # placeholder rows the matrix engine creates.
            has_stock = units > 0

            k = (cid, ptid)
            e = agg.setdefault(k, {"units": 0, "value": 0.0, "skus": 0})
            if has_stock:
                e["skus"] += 1
            e["units"] += units
            e["value"] += val

            b = brand_agg.setdefault(brand, {"skus": 0, "units": 0, "value": 0.0})
            if has_stock:
                b["skus"] += 1
            b["units"] += units
            b["value"] += val

            bp = bp_agg.setdefault((brand, ptid),
                                   {"skus": 0, "units": 0, "value": 0.0})
            if has_stock:
                bp["skus"] += 1
            bp["units"] += units
            bp["value"] += val

        grand_units = sum(e["units"] for e in agg.values())
        grand_value = sum(e["value"] for e in agg.values())
        grand_skus = sum(e["skus"] for e in agg.values())

        self._kpi_cards(pdf, [
            ("Categories",  str(len(cats))),
            ("Part Types",  str(len(agg))),
            ("Total Units", str(grand_units)),
            ("Total Value",
             self._cfg.format_currency(f"{grand_value:,.2f}")),
        ])

        # ── Per-brand summary ─────────────────────────────────────────────
        if brand_agg:
            self._section_title(pdf, "By Brand")
            brand_rows = sorted(
                brand_agg.items(),
                key=lambda kv: kv[1]["value"], reverse=True,
            )
            self._brand_summary_table(pdf, brand_rows, grand_value)

        # ── Per-category → per-part-type → per-brand breakdown ───────────
        for cat in cats:
            cat_rows = [(pt, agg.get((cat.id, pt.id),
                                     {"units": 0, "value": 0.0, "skus": 0}))
                        for pt in cat.part_types]
            cat_rows = [r for r in cat_rows if r[1]["skus"] > 0]
            if not cat_rows:
                continue
            cat_units = sum(r[1]["units"] for r in cat_rows)
            cat_value = sum(r[1]["value"] for r in cat_rows)

            self._group_header(
                pdf,
                f"{cat.name('EN')}",
                meta=(f"{cat_units} units  ·  "
                      f"{self._cfg.format_currency(f'{cat_value:,.2f}')}"),
                level=1,
            )
            self._valuation_table(pdf, cat_rows, bp_agg)

        self._grand_total_bar(pdf, [
            ("SKUs",  str(grand_skus)),
            ("Units", str(grand_units)),
            ("Stock Value",
             self._cfg.format_currency(f"{grand_value:,.2f}")),
        ])
        return self._save(pdf, output_path, "valuation_report")

    def generate_sales_report(self,
                              date_from: str | None = None,
                              date_to: str | None = None,
                              output_path: str | None = None) -> str:
        from app.repositories.sale_repo import SaleRepository
        sale_repo = SaleRepository()

        if not date_to:
            date_to = datetime.now().strftime("%Y-%m-%d")
        if not date_from:
            date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        pdf = self._new_pdf("Sales Report",
                            f"POS sales  ·  {date_from}  to  {date_to}")
        pdf.add_page()

        sales = sale_repo.get_all(limit=5000, date_from=date_from, date_to=date_to)
        total_revenue = sum((s.net_total or s.total_amount or 0) for s in sales)
        total_units = 0
        for s in sales:
            total_units += sum(si.quantity for si in (s.items or []))
        avg_basket = (total_revenue / len(sales)) if sales else 0

        self._kpi_cards(pdf, [
            ("Sales",   str(len(sales))),
            ("Units",   str(total_units)),
            ("Revenue", self._cfg.format_currency(f"{total_revenue:,.2f}")),
            ("Avg Basket", self._cfg.format_currency(f"{avg_basket:,.2f}")),
        ])

        if sales:
            self._section_title(pdf, f"Sales ({len(sales)})")
            self._sales_table(pdf, sales)
        else:
            self._empty_msg(pdf, "No sales in the selected range.")

        # Best sellers
        try:
            best = sale_repo.top_items(limit=10,
                                       date_from=date_from, date_to=date_to)
        except Exception:
            best = []
        if best:
            self._section_title(pdf, "Top Sellers (Top 10)")
            self._best_sellers_table(pdf, best)
        return self._save(pdf, output_path, "sales_report")

    def generate_scan_invoices_report(self,
                                      date_from: str | None = None,
                                      date_to: str | None = None,
                                      op_filter: str = "ALL",
                                      output_path: str | None = None) -> str:
        from app.repositories.invoice_repo import InvoiceRepository
        inv_repo = InvoiceRepository()

        if not date_to:
            date_to = datetime.now().strftime("%Y-%m-%d")
        if not date_from:
            date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        subtitle = f"Quick Scan invoices  ·  {date_from}  to  {date_to}"
        if op_filter and op_filter != "ALL":
            subtitle += f"  ·  {op_filter}"
        pdf = self._new_pdf("Scan Invoices", subtitle)
        pdf.add_page()

        all_invoices = inv_repo.list_recent(limit=2000)
        # Filter by date + operation
        def _in_range(iv):
            created = (iv.get("created_at") or "")[:10]
            if date_from and created < date_from:
                return False
            if date_to and created > date_to:
                return False
            if op_filter and op_filter != "ALL":
                if (iv.get("operation") or "").upper() != op_filter.upper():
                    return False
            return True
        invoices = [iv for iv in all_invoices if _in_range(iv)]

        in_total = sum(float(iv.get("total") or 0)
                       for iv in invoices if iv.get("operation") == "IN")
        out_total = sum(float(iv.get("total") or 0)
                        for iv in invoices if iv.get("operation") == "OUT")
        self._kpi_cards(pdf, [
            ("Invoices", str(len(invoices))),
            ("IN Total", self._cfg.format_currency(f"{in_total:,.2f}")),
            ("OUT Total", self._cfg.format_currency(f"{out_total:,.2f}")),
            ("Net", self._cfg.format_currency(f"{(out_total - in_total):,.2f}")),
        ])

        if invoices:
            self._section_title(pdf, f"Invoices ({len(invoices)})")
            self._scan_invoices_table(pdf, invoices)
        else:
            self._empty_msg(pdf, "No invoices for the selected range.")
        return self._save(pdf, output_path, "scan_invoices_report")

    def generate_expiring_report(self, days_ahead: int = 30,
                                 output_path: str | None = None) -> str:
        pdf = self._new_pdf("Expiring Stock",
                            f"Items expiring within {days_ahead} days")
        pdf.add_page()

        try:
            items = self._item_repo.get_expiring(days=days_ahead)
        except Exception:
            items = []

        expired = sum(1 for i in items
                      if self._days_to_expiry(getattr(i, "expiry_date", "")) <= 0)
        soon = sum(1 for i in items
                   if 0 < self._days_to_expiry(getattr(i, "expiry_date", "")) <= 7)
        self._kpi_cards(pdf, [
            ("Flagged Items", str(len(items))),
            ("Already Expired", str(expired)),
            ("Within 7 Days", str(soon)),
            ("Window", f"{days_ahead} days"),
        ])
        if items:
            self._section_title(pdf, f"Expiring / Expired ({len(items)})")
            self._expiring_table(pdf, items)
        else:
            self._empty_msg(pdf, "No items expiring in the selected window.")
        return self._save(pdf, output_path, "expiring_report")

    def generate_category_performance_report(self,
                                             date_from: str | None = None,
                                             date_to: str | None = None,
                                             output_path: str | None = None) -> str:
        if not date_to:
            date_to = datetime.now().strftime("%Y-%m-%d")
        if not date_from:
            date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        pdf = self._new_pdf("Category Performance",
                            f"Stock + movement per category  ·  {date_from}  to  {date_to}")
        pdf.add_page()

        cats = self._cat_repo.get_all_active()
        items = self._item_repo.get_all_items()
        txns = self._txn_repo.get_filtered(date_from=date_from, date_to=date_to, limit=20000)

        # Map pt_id → cat_id and pt_id → pt for reverse lookup
        pt_to_cat: dict[int, int] = {}
        for c in cats:
            for pt in c.part_types:
                pt_to_cat[pt.id] = c.id

        # Per-category aggregates
        per_cat: dict[int, dict] = {
            c.id: {
                "name": c.name("EN"),
                "stock_units": 0, "stock_value": 0.0, "skus": 0,
                "sold_units": 0, "in_units": 0,
            } for c in cats
        }

        for it in items:
            cid = pt_to_cat.get(getattr(it, "part_type_id", None) or 0)
            if cid is None or cid not in per_cat:
                continue
            entry = per_cat[cid]
            entry["skus"] += 1
            entry["stock_units"] += (it.stock or 0)
            price = it.sell_price
            if price is None:
                # fallback part type default
                ptid = it.part_type_id
                for c in cats:
                    for pt in c.part_types:
                        if pt.id == ptid and pt.default_price is not None:
                            price = float(pt.default_price)
                            break
                    if price is not None:
                        break
            if price is not None:
                entry["stock_value"] += (it.stock or 0) * float(price)

        # Transactions — aggregate by category via item lookup
        items_by_id = {it.id: it for it in items}
        for tx in txns:
            it = items_by_id.get(tx.item_id)
            if it is None:
                continue
            cid = pt_to_cat.get(getattr(it, "part_type_id", None) or 0)
            if cid is None or cid not in per_cat:
                continue
            if tx.operation == "OUT":
                per_cat[cid]["sold_units"] += tx.quantity
            elif tx.operation == "IN":
                per_cat[cid]["in_units"] += tx.quantity

        rows = [v for v in per_cat.values() if v["skus"] > 0]
        total_value = sum(r["stock_value"] for r in rows)
        total_sold = sum(r["sold_units"] for r in rows)
        self._kpi_cards(pdf, [
            ("Categories",  str(len(rows))),
            ("Stock Value", self._cfg.format_currency(f"{total_value:,.2f}")),
            ("Sold Units",  str(total_sold)),
            ("Period (days)", str((datetime.strptime(date_to, '%Y-%m-%d')
                                    - datetime.strptime(date_from, '%Y-%m-%d')).days + 1)),
        ])

        if rows:
            self._section_title(pdf, "Categories")
            self._category_performance_table(pdf, rows)
        else:
            self._empty_msg(pdf, "No category data for the selected range.")
        return self._save(pdf, output_path, "category_performance_report")

    # ════════════════════════════════════════════════════════════════════════
    # DESIGN COMPONENTS
    # ════════════════════════════════════════════════════════════════════════

    def _safe(self, s) -> str:
        """Latin-1 sanitise — available to subclasses / inline render code."""
        return _latin1(s)

    def _new_pdf(self, title: str, subtitle: str = "") -> _ReportPDF:
        pdf = _ReportPDF(orientation="P", unit="mm", format="A4")
        pdf.title_text = title
        pdf.subtitle_text = subtitle
        pdf.shop_cfg = self._cfg
        pdf.set_auto_page_break(auto=True, margin=_MARGIN_B + 4)
        pdf.set_left_margin(_MARGIN_L)
        pdf.set_right_margin(_MARGIN_R)
        pdf.set_top_margin(_MARGIN_T)
        pdf.alias_nb_pages()       # enables {nb} → total pages
        return pdf

    def _kpi_cards(self, pdf: _ReportPDF, cards: list[tuple[str, str]]) -> None:
        n = max(1, len(cards))
        gap = 3
        card_w = (_PW - gap * (n - 1)) / n
        card_h = 18
        y0 = pdf.get_y()
        for i, (label, value) in enumerate(cards):
            x = _MARGIN_L + i * (card_w + gap)
            pdf.set_fill_color(*_GRAY_50)
            pdf.set_draw_color(*_GRAY_200)
            pdf.rounded_rect(x, y0, card_w, card_h, 2, "DF")
            pdf.set_xy(x + 4, y0 + 2)
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_text_color(*_DARK)
            pdf.cell(card_w - 8, 7, value)
            pdf.set_xy(x + 4, y0 + 9)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*_GRAY_600)
            pdf.cell(card_w - 8, 5, label)
        pdf.set_y(y0 + card_h + 5)

    def _section_title(self, pdf: _ReportPDF, text: str) -> None:
        pdf.ln(1)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*_DARK)
        pdf.cell(0, 7, text, ln=True)
        y = pdf.get_y()
        pdf.set_draw_color(*_PRIMARY)
        pdf.set_line_width(0.6)
        pdf.line(_MARGIN_L, y, _MARGIN_L + 48, y)
        pdf.set_line_width(0.2)
        pdf.ln(2)

    def _empty_msg(self, pdf: _ReportPDF, text: str) -> None:
        pdf.ln(8)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(*_GRAY_400)
        pdf.cell(0, 8, text, ln=True, align="C")

    def _group_header(self, pdf: _ReportPDF, title: str, meta: str = "",
                      level: int = 1) -> None:
        """Draw a horizontal group-header bar for brand / part-type sections.

        level=1 → brand (darker)
        level=2 → part type (mid-slate, thinner)
        """
        pdf.ln(0.5)
        self._page_break_check_raw(pdf)
        y = pdf.get_y()
        bar_h = 7 if level == 1 else 6
        bg = _GRAY_800 if level == 1 else _GRAY_600
        pdf.set_fill_color(*bg)
        pdf.rect(_MARGIN_L, y, _PW, bar_h, "F")
        # Title on the left
        pdf.set_xy(_MARGIN_L + 4, y + (1 if level == 1 else 0.8))
        pdf.set_font("Helvetica", "B", 9 if level == 1 else 8)
        pdf.set_text_color(*_WHITE)
        left_w = _PW * 0.7
        pdf.cell(left_w, bar_h - 1, title, ln=False, align="L")
        # Meta (counts / totals) right
        if meta:
            pdf.set_xy(_MARGIN_L + left_w, y + (1 if level == 1 else 0.8))
            pdf.set_font("Helvetica", "", 8)
            pdf.cell(_PW - left_w - 4, bar_h - 1, meta, ln=False, align="R")
        pdf.set_y(y + bar_h + 0.5)

    def _subtotal_row(self, pdf: _ReportPDF, label: str, meta: str) -> None:
        """Thin line showing a subtotal right below a grouped table."""
        y = pdf.get_y()
        pdf.set_draw_color(*_GRAY_400)
        pdf.line(_MARGIN_L, y, _MARGIN_L + _PW, y)
        pdf.set_xy(_MARGIN_L + 4, y + 0.8)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*_GRAY_700)
        left_w = _PW * 0.6
        pdf.cell(left_w, 5, label, ln=False)
        pdf.set_xy(_MARGIN_L + left_w, y + 0.8)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*_DARK)
        pdf.cell(_PW - left_w - 4, 5, meta, ln=False, align="R")
        pdf.ln(6.5)

    def _page_break_check_raw(self, pdf: _ReportPDF) -> None:
        """Page-break when near the bottom, without redrawing a table header
        (used before group headers which are self-contained)."""
        if pdf.get_y() > _CONTENT_BOTTOM - 12:
            pdf.add_page()

    def _grand_total_bar(self, pdf: _ReportPDF, kvs: list[tuple[str, str]]) -> None:
        """Bold emerald bar at the bottom of the valuation report."""
        pdf.ln(2)
        y = pdf.get_y()
        pdf.set_fill_color(*_PRIMARY)
        pdf.rect(_MARGIN_L, y, _PW, 11, "F")
        pdf.set_xy(_MARGIN_L + 4, y + 2)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*_WHITE)
        pdf.cell(40, 7, "GRAND TOTAL")
        # kvs chunks spread across the bar
        remaining = _PW - 44
        slot = remaining / max(1, len(kvs))
        for i, (label, value) in enumerate(kvs):
            x = _MARGIN_L + 44 + i * slot
            pdf.set_xy(x, y + 1.5)
            pdf.set_font("Helvetica", "", 7)
            pdf.cell(slot, 3.5, label.upper(), ln=False)
            pdf.set_xy(x, y + 5)
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(slot, 5, value, ln=False)
        pdf.ln(13)

    # ════════════════════════════════════════════════════════════════════════
    # TABLE RENDERERS (with pagination)
    # ════════════════════════════════════════════════════════════════════════

    def _draw_table_header(self, pdf: _ReportPDF,
                           cols: list[tuple[str, float, str]]) -> None:
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_fill_color(*_DARK)
        pdf.set_text_color(*_WHITE)
        pdf.set_draw_color(*_DARK)
        for label, w, align in cols:
            pdf.cell(w, 7, f"  {label}",
                     border=0, fill=True,
                     align="L" if align == "L" else align)
        pdf.ln(7)

    def _row(self, pdf: _ReportPDF,
             cells: list[tuple[str, float, str]], idx: int,
             row_h: float = 6.5) -> None:
        bg = _WHITE if idx % 2 == 0 else _GRAY_50
        pdf.set_fill_color(*bg)
        pdf.set_draw_color(*_GRAY_200)
        pdf.set_text_color(*_GRAY_800)
        pdf.set_font("Helvetica", "", 7.5)
        for val, w, align in cells:
            pdf.cell(w, row_h, f"  {val}" if align == "L" else val,
                     border="B", fill=True,
                     align="L" if align == "L" else align)
        pdf.ln(row_h)

    def _page_break_check(self, pdf: _ReportPDF,
                          cols: list[tuple[str, float, str]]) -> None:
        if pdf.get_y() > _CONTENT_BOTTOM - 8:
            pdf.add_page()
            self._draw_table_header(pdf, cols)

    # ── Inventory ──────────────────────────────────────────────────────────
    def _inventory_table(self, pdf: _ReportPDF, items: list) -> None:
        """Part-type-centric inventory listing.

        Structure (each part type appears ONCE):
            CATEGORY header bar (dark)        skus · units · value
              (JK) incell FHD subheader       skus · units · value
              Table with Brand column, items from ALL brands
              Subtotal strip
              (D.D) Soft-OLED subheader       …
              …
            BATTERIES header bar (dark)        …
            …
            GRAND TOTAL emerald bar
        """
        cols = [
            ("#",      8,  "C"),
            ("Brand",  20, "L"),
            ("Item",   54, "L"),
            ("Color",  16, "C"),
            ("Price",  24, "R"),
            ("Stock",  16, "C"),
            ("Min",    14, "C"),
            ("Diff",   16, "C"),
            ("Status", 18, "C"),
        ]
        # Sum = 186 exact ✓

        # Map: part_type_id -> (category, part_type)
        cats = self._cat_repo.get_all_active()
        pt_info: dict[int, tuple[object, object]] = {}
        cat_order: list = []
        for cat in cats:
            cat_order.append(cat)
            for pt in cat.part_types:
                pt_info[pt.id] = (cat, pt)

        # Group items: category_id -> part_type_id -> list[item]
        grouped: dict[int, dict[int, list]] = {}
        uncategorised: list = []
        for it in items:
            ptid = getattr(it, "part_type_id", None)
            if ptid is None or ptid not in pt_info:
                uncategorised.append(it)
                continue
            cat, pt = pt_info[ptid]
            grouped.setdefault(cat.id, {}).setdefault(pt.id, []).append(it)

        running_idx = 0
        gt_skus = gt_units = 0
        gt_value = 0.0

        for cat in cat_order:
            if cat.id not in grouped:
                continue
            pt_groups = grouped[cat.id]
            cat_skus = sum(len(v) for v in pt_groups.values())
            cat_units = sum((it.stock or 0)
                            for v in pt_groups.values() for it in v)
            cat_value = sum(
                (it.stock or 0) * float(it.sell_price or 0)
                for v in pt_groups.values() for it in v
            )
            self._group_header(
                pdf, cat.name("EN").upper(),
                meta=(f"{cat_skus} SKUs  ·  {cat_units} units  ·  "
                      f"{self._cfg.format_currency(f'{cat_value:,.2f}')}"),
                level=1,
            )

            # Iterate part types in their defined order (sort_order)
            for pt in cat.part_types:
                rows = pt_groups.get(pt.id)
                if not rows:
                    continue
                # Sort items inside by brand then name
                rows = sorted(rows,
                              key=lambda it: (self._resolve_brand(it).lower(),
                                              it.display_name.lower()))
                pt_units = sum((it.stock or 0) for it in rows)
                pt_value = sum((it.stock or 0) * float(it.sell_price or 0)
                               for it in rows)
                self._group_header(
                    pdf, f"  {pt.name}",
                    meta=(f"{len(rows)} SKUs  ·  {pt_units} units  ·  "
                          f"{self._cfg.format_currency(f'{pt_value:,.2f}')}"),
                    level=2,
                )
                self._draw_table_header(pdf, cols)
                for item in rows:
                    running_idx += 1
                    diff = (item.stock or 0) - (item.min_stock or 0)
                    diff_s = f"{diff:+d}" if item.min_stock > 0 else "-"
                    if item.is_out:
                        status = "OUT"
                    elif item.is_low:
                        status = "LOW"
                    else:
                        status = "OK"
                    price = (self._cfg.format_currency(f"{item.sell_price:,.2f}")
                             if item.sell_price else "-")
                    cells = [
                        (str(running_idx), 8,  "C"),
                        (self._resolve_brand(item)[:12], 20, "L"),
                        (item.display_name[:34], 54, "L"),
                        ((item.color or "-")[:9], 16, "C"),
                        (price, 24, "R"),
                        (str(item.stock), 16, "C"),
                        (str(item.min_stock), 14, "C"),
                        (diff_s, 16, "C"),
                    ]
                    y_before = pdf.get_y()
                    self._row(pdf, cells, running_idx - 1)
                    # Status badge coloured
                    pdf.set_xy(_MARGIN_L + sum(c[1] for c in cols[:-1]),
                               y_before)
                    if status == "OUT":
                        pdf.set_text_color(*_RED_TXT); pdf.set_font("Helvetica", "B", 7.5)
                    elif status == "LOW":
                        pdf.set_text_color(180, 120, 0); pdf.set_font("Helvetica", "B", 7.5)
                    else:
                        pdf.set_text_color(*_GREEN_TXT); pdf.set_font("Helvetica", "", 7.5)
                    bg = _WHITE if (running_idx - 1) % 2 == 0 else _GRAY_50
                    pdf.set_fill_color(*bg)
                    pdf.cell(18, 6.5, status, border="B", fill=True, align="C")
                    pdf.ln(0)
                    self._page_break_check(pdf, cols)

                self._subtotal_row(
                    pdf,
                    f"Subtotal — {pt.name}",
                    (f"{len(rows)} SKUs   {pt_units} units   "
                     f"{self._cfg.format_currency(f'{pt_value:,.2f}')}"),
                )

            gt_skus += cat_skus
            gt_units += cat_units
            gt_value += cat_value

        # Uncategorised items (no part_type or deleted part type)
        if uncategorised:
            self._group_header(
                pdf, "UNCATEGORISED",
                meta=f"{len(uncategorised)} items",
                level=1,
            )
            self._draw_table_header(pdf, cols)
            for item in uncategorised:
                running_idx += 1
                diff = (item.stock or 0) - (item.min_stock or 0)
                diff_s = f"{diff:+d}" if item.min_stock > 0 else "-"
                status = "OUT" if item.is_out else ("LOW" if item.is_low else "OK")
                price = (self._cfg.format_currency(f"{item.sell_price:,.2f}")
                         if item.sell_price else "-")
                cells = [
                    (str(running_idx), 8, "C"),
                    (self._resolve_brand(item)[:12], 20, "L"),
                    (item.display_name[:34], 54, "L"),
                    ((item.color or "-")[:9], 16, "C"),
                    (price, 24, "R"),
                    (str(item.stock), 16, "C"),
                    (str(item.min_stock), 14, "C"),
                    (diff_s, 16, "C"),
                    (status, 18, "C"),
                ]
                self._row(pdf, cells, running_idx - 1)
                self._page_break_check(pdf, cols)
            gt_skus += len(uncategorised)
            gt_units += sum((it.stock or 0) for it in uncategorised)
            gt_value += sum((it.stock or 0) * float(it.sell_price or 0)
                            for it in uncategorised)

        self._grand_total_bar(pdf, [
            ("SKUs", str(gt_skus)),
            ("Units", str(gt_units)),
            ("Stock Value",
             self._cfg.format_currency(f"{gt_value:,.2f}")),
        ])

    # ── Low stock ──────────────────────────────────────────────────────────
    def _low_stock_table(self, pdf: _ReportPDF, items: list) -> None:
        cols = [
            ("#",       10, "C"),
            ("Item",    62, "L"),
            ("Stock",   18, "C"),
            ("Min",     18, "C"),
            ("Deficit", 20, "C"),
            ("% of Min",20, "C"),
            ("Urgency", 38, "C"),  # widened from 24 — sum becomes 186
        ]
        self._draw_table_header(pdf, cols)

        for idx, item in enumerate(items):
            diff = (item.stock or 0) - (item.min_stock or 0)
            pct = int(item.stock / item.min_stock * 100) if item.min_stock > 0 else 0
            if item.is_out or pct < 25:
                urgency = "CRITICAL"
            elif pct < 50:
                urgency = "HIGH"
            else:
                urgency = "MEDIUM"

            cells = [
                (str(idx + 1), 10, "C"),
                (item.display_name[:40], 62, "L"),
                (str(item.stock), 18, "C"),
                (str(item.min_stock), 18, "C"),
                (str(diff), 20, "C"),
                (f"{pct}%", 20, "C"),
            ]
            y_before = pdf.get_y()
            self._row(pdf, cells, idx)

            pdf.set_xy(_MARGIN_L + sum(c[1] for c in cols[:-1]), y_before)
            if urgency == "CRITICAL":
                pdf.set_text_color(*_RED_TXT); pdf.set_font("Helvetica", "B", 7)
            elif urgency == "HIGH":
                pdf.set_text_color(180, 120, 0); pdf.set_font("Helvetica", "B", 7)
            else:
                pdf.set_text_color(*_GRAY_600); pdf.set_font("Helvetica", "", 7)
            bg = _WHITE if idx % 2 == 0 else _GRAY_50
            pdf.set_fill_color(*bg)
            pdf.cell(38, 6.5, urgency, border="B", fill=True, align="C")
            pdf.ln(0)
            self._page_break_check(pdf, cols)

    # ── Transactions ───────────────────────────────────────────────────────
    def _transactions_table(self, pdf: _ReportPDF, txns: list) -> None:
        cols = [
            ("Date",   24, "L"),
            ("Item",   56, "L"),
            ("Type",   16, "C"),
            ("Qty",    16, "C"),
            ("Before", 18, "C"),
            ("After",  18, "C"),
            ("Change", 18, "C"),
            ("Note",   20, "L"),
        ]
        # Sum = 186 ✓
        self._draw_table_header(pdf, cols)

        for idx, tx in enumerate(txns):
            d = (tx.stock_after or 0) - (tx.stock_before or 0)
            ds = f"{d:+d}"
            date_s = tx.timestamp[:10] if tx.timestamp else "-"
            note = (tx.note or "-")[:14]

            bg = _WHITE if idx % 2 == 0 else _GRAY_50
            pdf.set_fill_color(*bg); pdf.set_draw_color(*_GRAY_200)
            pdf.set_text_color(*_GRAY_800); pdf.set_font("Helvetica", "", 7.5)
            pdf.cell(24, 6.5, f"  {date_s}", border="B", fill=True, align="L")
            pdf.cell(56, 6.5, f"  {tx.display_name[:32]}", border="B", fill=True, align="L")

            # OP coloured
            op = tx.operation
            if op == "IN":
                pdf.set_text_color(*_GREEN_TXT)
            elif op == "OUT":
                pdf.set_text_color(*_RED_TXT)
            else:
                pdf.set_text_color(*_GRAY_600)
            pdf.set_font("Helvetica", "B", 7)
            pdf.cell(16, 6.5, op, border="B", fill=True, align="C")

            pdf.set_text_color(*_GRAY_800); pdf.set_font("Helvetica", "", 7.5)
            pdf.cell(16, 6.5, str(tx.quantity), border="B", fill=True, align="C")
            pdf.cell(18, 6.5, str(tx.stock_before), border="B", fill=True, align="C")
            pdf.cell(18, 6.5, str(tx.stock_after),  border="B", fill=True, align="C")

            if d >= 0:
                pdf.set_text_color(*_GREEN_TXT)
            else:
                pdf.set_text_color(*_RED_TXT)
            pdf.set_font("Helvetica", "B", 7.5)
            pdf.cell(18, 6.5, ds, border="B", fill=True, align="C")
            pdf.set_text_color(*_GRAY_400); pdf.set_font("Helvetica", "", 6.5)
            pdf.cell(20, 6.5, f"  {note}", border="B", fill=True, align="L")
            pdf.ln(6.5)
            self._page_break_check(pdf, cols)

    # ── Audit ─────────────────────────────────────────────────────────────
    def _audit_table(self, pdf: _ReportPDF, items: list) -> None:
        cols = [
            ("#",        10, "C"),
            ("Item",     60, "L"),
            ("Barcode",  32, "L"),
            ("System",   18, "C"),
            ("Actual",   22, "C"),
            ("Diff",     18, "C"),
            ("Notes",    26, "L"),
        ]
        self._draw_table_header(pdf, cols)
        for idx, item in enumerate(items):
            bc = (item.barcode or "-")[:18]
            cells = [
                (str(idx + 1), 10, "C"),
                (item.display_name[:36], 60, "L"),
                (bc, 32, "L"),
                (str(item.stock), 18, "C"),
                ("", 22, "C"),
                ("", 18, "C"),
                ("", 26, "L"),
            ]
            self._row(pdf, cells, idx, row_h=7)
            self._page_break_check(pdf, cols)

    # ── Discrepancy ────────────────────────────────────────────────────────
    def _discrepancy_table(self, pdf: _ReportPDF, lines: list) -> None:
        cols = [
            ("Item",        60, "L"),
            ("System",      26, "C"),
            ("Counted",     26, "C"),
            ("Variance",    26, "C"),
            ("Var %",       24, "C"),
            ("Status",      24, "C"),
        ]
        self._draw_table_header(pdf, cols)

        for idx, ln in enumerate(lines):
            variance = ln.counted_qty - ln.system_qty
            var_pct = (variance / ln.system_qty * 100) if ln.system_qty else 0
            status = "Shrinkage" if variance < 0 else "Surplus"
            item_name = ln.item_name or f"Item #{ln.item_id}"

            bg = _WHITE if idx % 2 == 0 else _GRAY_50
            pdf.set_fill_color(*bg); pdf.set_draw_color(*_GRAY_200)
            pdf.set_text_color(*_GRAY_800); pdf.set_font("Helvetica", "", 7.5)
            pdf.cell(60, 6.5, f"  {item_name[:38]}", border="B", fill=True, align="L")
            pdf.cell(26, 6.5, str(ln.system_qty), border="B", fill=True, align="C")
            pdf.cell(26, 6.5, str(ln.counted_qty), border="B", fill=True, align="C")
            if variance < 0:
                pdf.set_text_color(*_RED_TXT)
            else:
                pdf.set_text_color(*_GREEN_TXT)
            pdf.set_font("Helvetica", "B", 7.5)
            pdf.cell(26, 6.5, f"{variance:+d}", border="B", fill=True, align="C")
            pdf.cell(24, 6.5, f"{var_pct:+.1f}%", border="B", fill=True, align="C")
            pdf.set_text_color(*_GRAY_700); pdf.set_font("Helvetica", "", 7.5)
            pdf.cell(24, 6.5, status, border="B", fill=True, align="C")
            pdf.ln(6.5)
            self._page_break_check(pdf, cols)

    # ── Valuation ──────────────────────────────────────────────────────────
    def _valuation_table(self, pdf: _ReportPDF, rows: list,
                         bp_agg: dict[tuple[str, int], dict] | None = None) -> None:
        """Part-type rows with optional per-brand subtotals directly below
        each row when multiple brands share that part type."""
        cols = [
            ("Part Type",   86, "L"),
            ("SKUs",        20, "C"),
            ("Units",       22, "C"),
            ("Avg Price",   28, "R"),
            ("Stock Value", 30, "R"),
        ]
        # Sum = 186 ✓
        self._draw_table_header(pdf, cols)
        idx = 0
        for pt, data in rows:
            units = data["units"]; value = data["value"]
            avg = value / units if units else 0
            avg_s = self._cfg.format_currency(f"{avg:,.2f}") if units else "-"
            val_s = self._cfg.format_currency(f"{value:,.2f}")
            cells = [
                (pt.name[:54], 86, "L"),
                (str(data["skus"]), 20, "C"),
                (str(units), 22, "C"),
                (avg_s, 28, "R"),
                (val_s, 30, "R"),
            ]
            self._row(pdf, cells, idx)
            idx += 1

            # Per-brand sub-rows — thin, indented, only when > 1 brand
            if bp_agg is not None:
                brands_here = sorted(
                    [(b, d) for (b, p), d in bp_agg.items() if p == pt.id],
                    key=lambda kv: kv[1]["value"], reverse=True,
                )
                if len(brands_here) > 1:
                    for brand, bd in brands_here:
                        pdf.set_fill_color(*_GRAY_100)
                        pdf.set_draw_color(*_GRAY_200)
                        pdf.set_text_color(*_GRAY_700)
                        pdf.set_font("Helvetica", "I", 7)
                        pdf.cell(86, 5.5, f"      · {brand}",
                                 border="B", fill=True, align="L")
                        pdf.cell(20, 5.5, str(bd["skus"]),
                                 border="B", fill=True, align="C")
                        pdf.cell(22, 5.5, str(bd["units"]),
                                 border="B", fill=True, align="C")
                        b_avg = bd["value"] / bd["units"] if bd["units"] else 0
                        pdf.cell(28, 5.5,
                                 self._cfg.format_currency(f"{b_avg:,.2f}")
                                 if bd["units"] else "-",
                                 border="B", fill=True, align="R")
                        pdf.cell(30, 5.5,
                                 self._cfg.format_currency(f"{bd['value']:,.2f}"),
                                 border="B", fill=True, align="R")
                        pdf.ln(5.5)
            self._page_break_check(pdf, cols)

    def _brand_summary_table(self, pdf: _ReportPDF,
                             brand_rows: list[tuple[str, dict]],
                             grand_total: float) -> None:
        """Small table: Brand | SKUs | Units | Stock Value | % of total."""
        cols = [
            ("Brand",        70, "L"),
            ("SKUs",         24, "C"),
            ("Units",        30, "C"),
            ("Stock Value",  38, "R"),
            ("% of Total",   24, "R"),
        ]
        # Sum = 186 ✓
        self._draw_table_header(pdf, cols)
        for idx, (brand, data) in enumerate(brand_rows):
            pct = (data["value"] / grand_total * 100) if grand_total else 0
            cells = [
                (brand[:44], 70, "L"),
                (str(data["skus"]), 24, "C"),
                (str(data["units"]), 30, "C"),
                (self._cfg.format_currency(f"{data['value']:,.2f}"), 38, "R"),
                (f"{pct:.1f}%", 24, "R"),
            ]
            self._row(pdf, cells, idx)
            self._page_break_check(pdf, cols)

    # ── Sales ──────────────────────────────────────────────────────────────
    def _sales_table(self, pdf: _ReportPDF, sales: list) -> None:
        cols = [
            ("Date",     26, "L"),
            ("Receipt",  20, "L"),
            ("Customer", 56, "L"),
            ("Items",    18, "C"),
            ("Subtotal", 26, "R"),
            ("Total",    26, "R"),
            ("Status",   14, "C"),
        ]
        self._draw_table_header(pdf, cols)
        for idx, s in enumerate(sales):
            items_count = sum(si.quantity for si in (s.items or []))
            date = (s.timestamp or "")[:16]
            cust = (getattr(s, "customer_name", "") or "-")[:32]
            status = getattr(s, "status", "") or "-"
            sub = float(s.total_amount or 0)
            total = float(s.net_total or sub)
            cells = [
                (date, 26, "L"),
                (f"#{s.id}", 20, "L"),
                (cust, 56, "L"),
                (str(items_count), 18, "C"),
                (self._cfg.format_currency(f"{sub:,.2f}"), 26, "R"),
                (self._cfg.format_currency(f"{total:,.2f}"), 26, "R"),
                (status[:6], 14, "C"),
            ]
            self._row(pdf, cells, idx)
            self._page_break_check(pdf, cols)

    def _best_sellers_table(self, pdf: _ReportPDF, rows: list[dict]) -> None:
        cols = [
            ("#",      10, "C"),
            ("Item",   96, "L"),
            ("Units",  30, "C"),
            ("Revenue", 50, "R"),
        ]
        self._draw_table_header(pdf, cols)
        for idx, r in enumerate(rows):
            cells = [
                (str(idx + 1), 10, "C"),
                ((r.get("item_name") or f"Item #{r.get('item_id')}")[:60], 96, "L"),
                (str(int(r.get("total_qty") or 0)), 30, "C"),
                (self._cfg.format_currency(f"{float(r.get('total_revenue') or 0):,.2f}"), 50, "R"),
            ]
            self._row(pdf, cells, idx)
            self._page_break_check(pdf, cols)

    # ── Scan invoices ──────────────────────────────────────────────────────
    def _scan_invoices_table(self, pdf: _ReportPDF, invoices: list[dict]) -> None:
        cols = [
            ("Invoice #",  34, "L"),
            ("Date",       28, "L"),
            ("Op",         14, "C"),
            ("Customer",   56, "L"),
            ("Layout",     16, "C"),
            ("Total",      38, "R"),
        ]
        self._draw_table_header(pdf, cols)
        for idx, iv in enumerate(invoices):
            op = (iv.get("operation") or "").upper()
            bg = _WHITE if idx % 2 == 0 else _GRAY_50
            pdf.set_fill_color(*bg); pdf.set_draw_color(*_GRAY_200)
            pdf.set_text_color(*_GRAY_800); pdf.set_font("Helvetica", "", 7.5)
            pdf.cell(34, 6.5, f"  {iv.get('invoice_number', '')}", border="B", fill=True, align="L")
            pdf.cell(28, 6.5, f"  {(iv.get('created_at') or '')[:16]}", border="B", fill=True, align="L")

            if op == "IN":
                pdf.set_text_color(*_GREEN_TXT)
            elif op == "OUT":
                pdf.set_text_color(*_RED_TXT)
            else:
                pdf.set_text_color(*_GRAY_600)
            pdf.set_font("Helvetica", "B", 7)
            pdf.cell(14, 6.5, op, border="B", fill=True, align="C")

            pdf.set_text_color(*_GRAY_800); pdf.set_font("Helvetica", "", 7.5)
            cust = (iv.get("customer_name") or "-")[:32]
            pdf.cell(56, 6.5, f"  {cust}", border="B", fill=True, align="L")
            pdf.cell(16, 6.5, (iv.get("layout") or "").upper(), border="B", fill=True, align="C")
            pdf.set_font("Helvetica", "B", 7.5)
            total_v = float(iv.get("total") or 0)
            cur = iv.get("currency") or self._cfg.currency
            pdf.cell(38, 6.5, f"{total_v:,.2f} {cur}",
                     border="B", fill=True, align="R")
            pdf.ln(6.5)
            self._page_break_check(pdf, cols)

    # ── Expiring ───────────────────────────────────────────────────────────
    def _expiring_table(self, pdf: _ReportPDF, items: list) -> None:
        cols = [
            ("#",        10, "C"),
            ("Item",     76, "L"),
            ("Barcode",  30, "L"),
            ("Stock",    16, "C"),
            ("Expiry",   24, "C"),
            ("Days",     14, "C"),
            ("Status",   16, "C"),
        ]
        self._draw_table_header(pdf, cols)
        for idx, item in enumerate(items):
            exp = getattr(item, "expiry_date", "") or ""
            days = self._days_to_expiry(exp)
            if days <= 0:
                status = "EXPIRED"
            elif days <= 7:
                status = "URGENT"
            else:
                status = "SOON"

            cells = [
                (str(idx + 1), 10, "C"),
                (item.display_name[:48], 76, "L"),
                ((item.barcode or "-")[:16], 30, "L"),
                (str(item.stock), 16, "C"),
                ((exp or "-")[:10], 24, "C"),
                (str(days), 14, "C"),
            ]
            y_before = pdf.get_y()
            self._row(pdf, cells, idx)

            pdf.set_xy(_MARGIN_L + sum(c[1] for c in cols[:-1]), y_before)
            if status == "EXPIRED":
                pdf.set_text_color(*_RED_TXT); pdf.set_font("Helvetica", "B", 7)
            elif status == "URGENT":
                pdf.set_text_color(180, 120, 0); pdf.set_font("Helvetica", "B", 7)
            else:
                pdf.set_text_color(*_GRAY_600); pdf.set_font("Helvetica", "", 7)
            bg = _WHITE if idx % 2 == 0 else _GRAY_50
            pdf.set_fill_color(*bg)
            pdf.cell(16, 6.5, status, border="B", fill=True, align="C")
            pdf.ln(0)
            self._page_break_check(pdf, cols)

    # ── Category performance ───────────────────────────────────────────────
    def _category_performance_table(self, pdf: _ReportPDF, rows: list[dict]) -> None:
        cols = [
            ("Category",    64, "L"),
            ("SKUs",        18, "C"),
            ("Stock Units", 24, "C"),
            ("Stock Value", 34, "R"),
            ("Sold Units",  22, "C"),
            ("In Units",    24, "C"),
        ]
        self._draw_table_header(pdf, cols)
        for idx, r in enumerate(rows):
            cells = [
                (str(r.get("name", ""))[:40], 64, "L"),
                (str(r.get("skus", 0)), 18, "C"),
                (str(r.get("stock_units", 0)), 24, "C"),
                (self._cfg.format_currency(f"{r.get('stock_value', 0):,.2f}"), 34, "R"),
                (str(r.get("sold_units", 0)), 22, "C"),
                (str(r.get("in_units", 0)), 24, "C"),
            ]
            self._row(pdf, cells, idx)
            self._page_break_check(pdf, cols)

    # ── Utilities ──────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_brand(it) -> str:
        """Best-effort brand: model_brand (matrix items) > brand > placeholder."""
        b = (getattr(it, "model_brand", "") or "").strip()
        if b:
            return b
        b = (getattr(it, "brand", "") or "").strip()
        return b or "(no brand)"

    @staticmethod
    def _days_to_expiry(expiry_str: str) -> int:
        if not expiry_str:
            return 99999
        try:
            exp = datetime.strptime(expiry_str[:10], "%Y-%m-%d").date()
            return (exp - datetime.now().date()).days
        except Exception:
            return 99999

    def _save(self, pdf: _ReportPDF, output_path: str | None,
              filename_base: str) -> str:
        if output_path is None:
            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(_output_dir() / f"{filename_base}_{now}.pdf")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        pdf.output(output_path)
        return output_path
