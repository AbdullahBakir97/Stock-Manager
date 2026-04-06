"""app/services/report_service.py — PDF report generation using fpdf2."""
from __future__ import annotations
from datetime import datetime, timedelta
import tempfile
from pathlib import Path
from fpdf import FPDF

from app.repositories.item_repo import ItemRepository
from app.repositories.transaction_repo import TransactionRepository
from app.core.config import ShopConfig
from app.core.i18n import t


class ReportService:
    """Generates professional PDF reports for inventory, low stock, transactions, and summary."""

    def __init__(self) -> None:
        self._item_repo = ItemRepository()
        self._txn_repo = TransactionRepository()
        self._config = ShopConfig.get()

    def generate_inventory_report(self, output_path: str | None = None) -> str:
        """Full inventory report with summary + item table."""
        pdf = self._create_pdf()
        pdf.add_page()

        # Header
        self._add_header(pdf, t("report_inventory_title"))

        # Summary section
        summary = self._item_repo.get_summary()
        self._add_summary_section(pdf, summary)

        # Items table
        items = self._item_repo.get_all_items()
        self._add_items_table(pdf, items)

        return self._save_pdf(pdf, output_path, "inventory_report")

    def generate_low_stock_report(self, output_path: str | None = None) -> str:
        """Low stock items report with urgency levels."""
        pdf = self._create_pdf()
        pdf.add_page()

        # Header
        self._add_header(pdf, t("report_low_stock_title"))

        # Low stock items
        items = self._item_repo.get_low_stock()

        if not items:
            pdf.set_font("Helvetica", "", 11)
            pdf.cell(0, 10, t("msg_no_low_stock_items"), ln=True)
        else:
            # Table with urgency indicators
            self._add_low_stock_table(pdf, items)

        return self._save_pdf(pdf, output_path, "low_stock_report")

    def generate_transaction_report(self, days: int = 30,
                                    output_path: str | None = None) -> str:
        """Transaction history for the last N days."""
        pdf = self._create_pdf()
        pdf.add_page()

        # Header with date range
        title = t("report_txn_title")
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, title, ln=True)

        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        date_to = datetime.now().strftime("%Y-%m-%d")
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 5, f"{date_from} to {date_to}", ln=True)
        pdf.ln(3)

        # Transactions
        txns = self._txn_repo.get_transactions(limit=500)

        if not txns:
            pdf.set_font("Helvetica", "", 11)
            pdf.cell(0, 10, "No transactions found.", ln=True)
        else:
            self._add_transactions_table(pdf, txns)

        return self._save_pdf(pdf, output_path, "transaction_report")

    def generate_summary_report(self, output_path: str | None = None) -> str:
        """Executive summary — single page overview."""
        pdf = self._create_pdf()
        pdf.add_page()

        # Header
        self._add_header(pdf, t("report_summary_title"))

        # Summary stats
        summary = self._item_repo.get_summary()
        self._add_summary_section(pdf, summary)

        # Key insights
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Key Insights", ln=True)
        pdf.set_font("Helvetica", "", 10)

        low_stock_items = self._item_repo.get_low_stock()
        out_of_stock = [i for i in low_stock_items if i.is_out]

        pdf.multi_cell(0, 5, f"• Low stock items: {len(low_stock_items)}")
        pdf.multi_cell(0, 5, f"• Out of stock: {len(out_of_stock)}")

        if summary.get("inventory_value"):
            value_str = self._config.format_currency(summary["inventory_value"])
            pdf.multi_cell(0, 5, f"• Total inventory value: {value_str}")

        return self._save_pdf(pdf, output_path, "summary_report")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _create_pdf(self) -> FPDF:
        """Create a base PDF with standard settings."""
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=12)
        pdf.set_margin(12)
        return pdf

    def _add_header(self, pdf: FPDF, title: str) -> None:
        """Add shop info and report title to top of page."""
        # Shop name
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 8, self._config.name, ln=True)

        # Contact info if available
        if self._config.contact_info:
            pdf.set_font("Helvetica", "", 8)
            pdf.cell(0, 4, self._config.contact_info, ln=True)

        pdf.ln(2)

        # Report title
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, title, ln=True)

        # Generated date
        pdf.set_font("Helvetica", "", 9)
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        pdf.cell(0, 5, t("report_generated_at", date=now), ln=True)

        pdf.ln(3)

    def _add_summary_section(self, pdf: FPDF, summary: dict) -> None:
        """Add summary statistics in a grid layout."""
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, "Summary Statistics", ln=True)

        pdf.set_font("Helvetica", "", 10)
        col_width = 45

        # Row 1
        pdf.cell(col_width, 6, f"Total Products: {summary.get('total_products', 0)}")
        pdf.cell(col_width, 6, f"Total Units: {summary.get('total_units', 0)}")
        pdf.ln(6)

        # Row 2
        pdf.cell(col_width, 6, f"Low Stock: {summary.get('low_stock_count', 0)}")
        pdf.cell(col_width, 6, f"Out of Stock: {summary.get('out_of_stock_count', 0)}")
        pdf.ln(6)

        # Row 3 — Inventory value
        if summary.get("inventory_value"):
            value_str = self._config.format_currency(summary["inventory_value"])
            pdf.cell(0, 6, f"Inventory Value: {value_str}")
            pdf.ln(6)

        pdf.ln(3)

    def _add_items_table(self, pdf: FPDF, items: list) -> None:
        """Add inventory items in a table format."""
        if not items:
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 10, "No items found.", ln=True)
            return

        # Table header
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(41, 128, 185)  # Blue
        pdf.set_text_color(255, 255, 255)

        pdf.cell(60, 7, "Item", border=1, fill=True)
        pdf.cell(20, 7, "Stock", border=1, align="C", fill=True)
        pdf.cell(15, 7, "Min", border=1, align="C", fill=True)
        pdf.cell(25, 7, "Price", border=1, align="R", fill=True)
        pdf.cell(15, 7, "Status", border=1, align="C", fill=True)
        pdf.ln(7)

        # Table rows with alternating background
        pdf.set_text_color(0, 0, 0)
        for idx, item in enumerate(items):
            # Alternating row color
            if idx % 2 == 0:
                pdf.set_fill_color(240, 240, 240)
            else:
                pdf.set_fill_color(255, 255, 255)

            pdf.set_font("Helvetica", "", 8)

            # Item name (truncate if needed)
            name = item.display_name[:40]
            pdf.cell(60, 6, name, border=1, fill=True)

            # Stock
            pdf.cell(20, 6, str(item.stock), border=1, align="C", fill=True)

            # Min stock
            pdf.cell(15, 6, str(item.min_stock), border=1, align="C", fill=True)

            # Price
            if item.sell_price:
                price_str = self._config.format_currency(item.sell_price)
            else:
                price_str = "—"
            pdf.cell(25, 6, price_str, border=1, align="R", fill=True)

            # Status
            if item.is_out:
                status = "OUT"
            elif item.is_low:
                status = "LOW"
            else:
                status = "OK"
            pdf.cell(15, 6, status, border=1, align="C", fill=True)

            pdf.ln(6)

    def _add_low_stock_table(self, pdf: FPDF, items: list) -> None:
        """Add low stock items with urgency indicators."""
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 8, f"Low Stock Items ({len(items)})", ln=True)

        # Table header
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(41, 128, 185)
        pdf.set_text_color(255, 255, 255)

        pdf.cell(50, 7, "Item", border=1, fill=True)
        pdf.cell(18, 7, "Stock", border=1, align="C", fill=True)
        pdf.cell(18, 7, "Min", border=1, align="C", fill=True)
        pdf.cell(20, 7, "Diff", border=1, align="C", fill=True)
        pdf.cell(30, 7, "Urgency", border=1, align="C", fill=True)
        pdf.ln(7)

        # Table rows
        pdf.set_text_color(0, 0, 0)
        for idx, item in enumerate(items):
            if idx % 2 == 0:
                pdf.set_fill_color(240, 240, 240)
            else:
                pdf.set_fill_color(255, 255, 255)

            pdf.set_font("Helvetica", "", 8)

            # Item name
            name = item.display_name[:32]
            pdf.cell(50, 6, name, border=1, fill=True)

            # Current stock
            pdf.cell(18, 6, str(item.stock), border=1, align="C", fill=True)

            # Min stock
            pdf.cell(18, 6, str(item.min_stock), border=1, align="C", fill=True)

            # Difference (negative = shortage)
            diff = item.stock - item.min_stock
            pdf.cell(20, 6, str(diff), border=1, align="C", fill=True)

            # Urgency level
            if item.is_out:
                urgency = "CRITICAL"
            else:
                # Calculate % of minimum
                pct = (item.stock / item.min_stock * 100) if item.min_stock > 0 else 0
                if pct < 25:
                    urgency = "CRITICAL"
                elif pct < 50:
                    urgency = "HIGH"
                else:
                    urgency = "MEDIUM"

            pdf.cell(30, 6, urgency, border=1, align="C", fill=True)
            pdf.ln(6)

    def _add_transactions_table(self, pdf: FPDF, txns: list) -> None:
        """Add transactions in a table format."""
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 8, f"Transactions ({len(txns)})", ln=True)

        # Table header
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(41, 128, 185)
        pdf.set_text_color(255, 255, 255)

        pdf.cell(20, 6, "Date", border=1, fill=True)
        pdf.cell(45, 6, "Item", border=1, fill=True)
        pdf.cell(16, 6, "Op", border=1, align="C", fill=True)
        pdf.cell(14, 6, "Qty", border=1, align="C", fill=True)
        pdf.cell(18, 6, "Before", border=1, align="C", fill=True)
        pdf.cell(18, 6, "After", border=1, align="C", fill=True)
        pdf.ln(6)

        # Table rows
        pdf.set_text_color(0, 0, 0)
        for idx, txn in enumerate(txns[:50]):  # Limit to 50 rows per page
            if idx % 2 == 0:
                pdf.set_fill_color(240, 240, 240)
            else:
                pdf.set_fill_color(255, 255, 255)

            pdf.set_font("Helvetica", "", 7)

            # Date
            date_str = txn.timestamp.split(" ")[0] if " " in txn.timestamp else txn.timestamp[:10]
            pdf.cell(20, 5, date_str, border=1, fill=True)

            # Item name
            name = txn.display_name[:25]
            pdf.cell(45, 5, name, border=1, fill=True)

            # Operation
            pdf.cell(16, 5, txn.operation, border=1, align="C", fill=True)

            # Quantity
            pdf.cell(14, 5, str(txn.quantity), border=1, align="C", fill=True)

            # Stock before
            pdf.cell(18, 5, str(txn.stock_before), border=1, align="C", fill=True)

            # Stock after
            pdf.cell(18, 5, str(txn.stock_after), border=1, align="C", fill=True)

            pdf.ln(5)

    def _save_pdf(self, pdf: FPDF, output_path: str | None, filename_base: str) -> str:
        """Save PDF to file and return the path."""
        if output_path is None:
            # Use temp directory
            temp_dir = tempfile.gettempdir()
            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(Path(temp_dir) / f"{filename_base}_{now}.pdf")

        # Ensure directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        pdf.output(output_path)
        return output_path
