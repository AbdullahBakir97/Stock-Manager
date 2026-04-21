r"""
app/ui/pages/reports_page.py — Report generation page.

Layout:
  +----------------------------------------------+
  |  Title                                        |
  |  [Today] [7d] [30d] [90d] [Year] [Custom]    |  date preset bar
  |  (From: ___  To: ___)    -- shown when Custom|
  |  Operation filter (contextual per report)    |
  |                                               |
  |  Inventory              Low Stock             |   report cards grid
  |  Transactions           Summary               |
  |  Audit Sheet            Discrepancy           |
  |  Barcode Labels         Stock Valuation       |
  |  Sales                  Scan Invoices         |
  |  Expiring Stock         Category Performance  |
  |                                               |
  |  OK Report saved -- C:\...\foo.pdf            |
  |              [Open PDF] [Folder] [Copy Path]  |
  +----------------------------------------------+
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QToolButton, QFrame, QSizePolicy,
    QMessageBox, QDateEdit, QComboBox, QApplication,
)
from PyQt6.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from app.core.theme import THEME
from app.core.i18n import t


# ── Background worker ────────────────────────────────────────────────────────

class _ReportWorker(QThread):
    finished = pyqtSignal(str)    # path
    errored  = pyqtSignal(str)    # message

    def __init__(self, report_type: str, context: dict, parent=None):
        super().__init__(parent)
        self._type = report_type
        self._ctx = context or {}

    def run(self):
        try:
            from app.services.report_service import ReportService
            svc = ReportService()
            date_from = self._ctx.get("date_from")
            date_to = self._ctx.get("date_to")
            op_filter = self._ctx.get("op_filter") or ""

            rt = self._type
            if rt == "inventory":
                path = svc.generate_inventory_report()
            elif rt == "low_stock":
                path = svc.generate_low_stock_report()
            elif rt == "transactions":
                path = svc.generate_transaction_report(
                    date_from=date_from, date_to=date_to, op_filter=op_filter,
                )
            elif rt == "summary":
                path = svc.generate_summary_report()
            elif rt == "audit":
                path = svc.generate_audit_sheet()
            elif rt == "discrepancy":
                path = svc.generate_discrepancy_report()
            elif rt == "barcode_labels":
                path = svc.generate_barcode_labels()
            elif rt == "valuation":
                path = svc.generate_valuation_report()
            elif rt == "sales":
                path = svc.generate_sales_report(
                    date_from=date_from, date_to=date_to,
                )
            elif rt == "scan_invoices":
                path = svc.generate_scan_invoices_report(
                    date_from=date_from, date_to=date_to,
                    op_filter=op_filter or "ALL",
                )
            elif rt == "expiring":
                days = self._ctx.get("days_ahead", 30)
                path = svc.generate_expiring_report(days_ahead=int(days))
            elif rt == "category_performance":
                path = svc.generate_category_performance_report(
                    date_from=date_from, date_to=date_to,
                )
            else:
                self.errored.emit(f"Unknown report type: {rt}")
                return
            self.finished.emit(path)
        except Exception as e:
            import traceback
            self.errored.emit(f"{e}\n{traceback.format_exc()[-400:]}")


# ── Report card ──────────────────────────────────────────────────────────────

class _ReportCard(QFrame):
    """Clickable card representing one report type."""
    clicked = pyqtSignal(str)

    def __init__(self, report_type: str, icon: str,
                 title: str, desc: str, parent=None):
        super().__init__(parent)
        self._type = report_type
        self.setObjectName("report_card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(84)
        self.setMaximumHeight(110)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(12)

        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Segoe UI Emoji", 24))
        icon_lbl.setFixedWidth(42)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(icon_lbl)

        text_lay = QVBoxLayout()
        text_lay.setSpacing(2)
        self._title_lbl = QLabel(title)
        self._title_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        text_lay.addWidget(self._title_lbl)
        self._desc_lbl = QLabel(desc)
        self._desc_lbl.setObjectName("card_meta_dim")
        self._desc_lbl.setWordWrap(True)
        text_lay.addWidget(self._desc_lbl)
        lay.addLayout(text_lay, 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._type)
        super().mousePressEvent(event)


# ── Main page ────────────────────────────────────────────────────────────────

class ReportsPage(QWidget):
    """Report selection, date range, filters, + output path + actions."""

    # Which reports consume date_from / date_to
    _USES_DATE = {"transactions", "sales", "scan_invoices", "category_performance"}
    # Which reports consume an operation filter
    _USES_OP = {
        "transactions": ("", "IN", "OUT", "ADJUST", "CREATE"),
        "scan_invoices": ("ALL", "IN", "OUT"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: _ReportWorker | None = None
        self._last_path: str = ""
        self._active_preset: str = "30d"
        self._current_type: str | None = None
        self._date_from: str = ""
        self._date_to: str = ""
        self._build_ui()
        self._apply_preset("30d")

    # ── Build ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)

        self._title = QLabel(t("reports_title"))
        self._title.setObjectName("section_caption")
        self._title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        outer.addWidget(self._title)

        # ── Date preset bar ──
        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)
        preset_lbl = QLabel("Date range:")
        preset_lbl.setObjectName("card_meta_dim")
        preset_row.addWidget(preset_lbl)

        self._preset_btns: dict[str, QToolButton] = {}
        for key, label in [
            ("today", "Today"), ("7d", "7 days"), ("30d", "30 days"),
            ("90d", "90 days"), ("year", "This year"), ("custom", "Custom"),
        ]:
            b = QToolButton()
            b.setText(label)
            b.setCheckable(True)
            b.setObjectName("reports_preset_btn")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFixedHeight(28)
            b.clicked.connect(lambda _=False, k=key: self._apply_preset(k))
            preset_row.addWidget(b)
            self._preset_btns[key] = b

        preset_row.addSpacing(12)
        self._from_edit = QDateEdit()
        self._from_edit.setCalendarPopup(True)
        self._from_edit.setDisplayFormat("yyyy-MM-dd")
        self._from_edit.setFixedHeight(28)
        self._from_edit.setDate(QDate.currentDate().addDays(-30))
        self._from_edit.dateChanged.connect(self._on_custom_date)

        self._to_edit = QDateEdit()
        self._to_edit.setCalendarPopup(True)
        self._to_edit.setDisplayFormat("yyyy-MM-dd")
        self._to_edit.setFixedHeight(28)
        self._to_edit.setDate(QDate.currentDate())
        self._to_edit.dateChanged.connect(self._on_custom_date)

        self._from_lbl = QLabel("From")
        self._from_lbl.setObjectName("card_meta_dim")
        self._to_lbl = QLabel("To")
        self._to_lbl.setObjectName("card_meta_dim")
        preset_row.addWidget(self._from_lbl)
        preset_row.addWidget(self._from_edit)
        preset_row.addWidget(self._to_lbl)
        preset_row.addWidget(self._to_edit)
        preset_row.addStretch()
        outer.addLayout(preset_row)
        self._set_custom_visible(False)

        # ── Filter row (operation, contextual) ──
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)
        self._op_lbl = QLabel("Operation:")
        self._op_lbl.setObjectName("card_meta_dim")
        self._op_combo = QComboBox()
        self._op_combo.setFixedHeight(28)
        filter_row.addWidget(self._op_lbl)
        filter_row.addWidget(self._op_combo)
        filter_row.addStretch()
        outer.addLayout(filter_row)
        self._set_filter_visible(False)

        # ── Report cards grid (2 columns) ──
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        report_defs = [
            ("inventory",            "📦", "Inventory",           "Complete stock list with price, status, min-stock."),
            ("low_stock",            "⚠",  "Low Stock",            "Items below minimum, sorted by urgency."),
            ("transactions",         "📋", "Transactions",         "Stock movements in the selected date range."),
            ("summary",              "📊", "Summary",              "Executive KPIs + top restock priorities."),
            ("audit",                "📝", "Audit Sheet",          "Blank physical-count sheet with system qty."),
            ("discrepancy",          "🔍", "Discrepancy",          "Audit variance — shrinkage, surplus, accuracy."),
            ("barcode_labels",       "🏷", "Barcode Labels",       "Printable barcode label sheets."),
            ("valuation",            "💰", "Stock Valuation",      "Total value split by part type + category subtotals."),
            ("sales",                "🛒", "Sales",                "POS sales + revenue + top sellers."),
            ("scan_invoices",        "🧾", "Scan Invoices",        "Quick Scan IN/OUT invoice history."),
            ("expiring",             "⏰", "Expiring Stock",       "Items with expiry within 30 days."),
            ("category_performance", "📈", "Category Performance", "Stock value + movement per category."),
        ]

        self._cards: list[_ReportCard] = []
        for i, (rt, icon, title, desc) in enumerate(report_defs):
            card = _ReportCard(rt, icon, title, desc, parent=self)
            card.clicked.connect(self._generate)
            grid.addWidget(card, i // 2, i % 2)
            self._cards.append(card)
        outer.addLayout(grid)
        outer.addStretch()

        # ── Status / actions bar ──
        self._status_frame = QFrame()
        self._status_frame.setObjectName("report_status_bar")
        self._status_frame.setFixedHeight(44)
        sl = QHBoxLayout(self._status_frame)
        sl.setContentsMargins(12, 0, 12, 0)
        sl.setSpacing(8)
        self._status_lbl = QLabel("Pick a report above.")
        self._status_lbl.setObjectName("footer_status")
        sl.addWidget(self._status_lbl, 1)

        self._open_btn = QPushButton("Open PDF")
        self._open_btn.setObjectName("btn_primary")
        self._open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_btn.setFixedHeight(30)
        self._open_btn.setEnabled(False)
        self._open_btn.clicked.connect(self._open_last)
        sl.addWidget(self._open_btn)

        self._folder_btn = QPushButton("Open folder")
        self._folder_btn.setObjectName("btn_secondary")
        self._folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._folder_btn.setFixedHeight(30)
        self._folder_btn.setEnabled(False)
        self._folder_btn.clicked.connect(self._open_folder)
        sl.addWidget(self._folder_btn)

        self._copy_btn = QPushButton("Copy path")
        self._copy_btn.setObjectName("btn_ghost")
        self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_btn.setFixedHeight(30)
        self._copy_btn.setEnabled(False)
        self._copy_btn.clicked.connect(self._copy_path)
        sl.addWidget(self._copy_btn)

        outer.addWidget(self._status_frame)

    # ── Date range handling ───────────────────────────────────────────────

    def _set_custom_visible(self, v: bool) -> None:
        for w in (self._from_lbl, self._from_edit, self._to_lbl, self._to_edit):
            w.setVisible(v)

    def _apply_preset(self, key: str) -> None:
        self._active_preset = key
        for k, btn in self._preset_btns.items():
            btn.setChecked(k == key)
        today = datetime.now().date()
        if key == "today":
            self._date_from = today.strftime("%Y-%m-%d")
            self._date_to = today.strftime("%Y-%m-%d")
        elif key == "7d":
            self._date_from = (today - timedelta(days=6)).strftime("%Y-%m-%d")
            self._date_to = today.strftime("%Y-%m-%d")
        elif key == "30d":
            self._date_from = (today - timedelta(days=29)).strftime("%Y-%m-%d")
            self._date_to = today.strftime("%Y-%m-%d")
        elif key == "90d":
            self._date_from = (today - timedelta(days=89)).strftime("%Y-%m-%d")
            self._date_to = today.strftime("%Y-%m-%d")
        elif key == "year":
            self._date_from = f"{today.year}-01-01"
            self._date_to = today.strftime("%Y-%m-%d")
        elif key == "custom":
            # Don't modify dates; user picks
            self._date_from = self._from_edit.date().toString("yyyy-MM-dd")
            self._date_to = self._to_edit.date().toString("yyyy-MM-dd")
        self._set_custom_visible(key == "custom")

    def _on_custom_date(self, *_args) -> None:
        if self._active_preset != "custom":
            return
        self._date_from = self._from_edit.date().toString("yyyy-MM-dd")
        self._date_to = self._to_edit.date().toString("yyyy-MM-dd")

    # ── Filter row handling ───────────────────────────────────────────────

    def _set_filter_visible(self, v: bool) -> None:
        self._op_lbl.setVisible(v)
        self._op_combo.setVisible(v)

    def _configure_filter_for(self, report_type: str) -> None:
        options = self._USES_OP.get(report_type)
        if not options:
            self._set_filter_visible(False)
            return
        self._op_combo.blockSignals(True)
        self._op_combo.clear()
        for v in options:
            self._op_combo.addItem(v if v else "All operations", v)
        self._op_combo.blockSignals(False)
        self._set_filter_visible(True)

    # ── Generate ───────────────────────────────────────────────────────────

    def _generate(self, report_type: str) -> None:
        if self._worker and self._worker.isRunning():
            return
        self._current_type = report_type
        self._configure_filter_for(report_type)

        # Build context
        ctx = {}
        if report_type in self._USES_DATE:
            ctx["date_from"] = self._date_from
            ctx["date_to"] = self._date_to
        if report_type in self._USES_OP:
            ctx["op_filter"] = self._op_combo.currentData() or ""

        self._status_lbl.setText("⏳ Generating…")
        self._open_btn.setEnabled(False)
        self._folder_btn.setEnabled(False)
        self._copy_btn.setEnabled(False)
        self._worker = _ReportWorker(report_type, ctx, self)
        self._worker.finished.connect(self._on_done)
        self._worker.errored.connect(self._on_error)
        self._worker.start()

    def _on_done(self, path: str) -> None:
        self._last_path = path
        # Middle-ellipsis truncate the path for display
        shown = self._elide_middle(path, 70)
        self._status_lbl.setText(f"✓ Report saved  —  {shown}")
        self._status_lbl.setToolTip(path)
        self._open_btn.setEnabled(True)
        self._folder_btn.setEnabled(True)
        self._copy_btn.setEnabled(True)

    def _on_error(self, msg: str) -> None:
        self._status_lbl.setText(f"✗ Error: {msg.splitlines()[0]}")
        self._status_lbl.setToolTip(msg)
        self._open_btn.setEnabled(False)
        self._folder_btn.setEnabled(False)
        self._copy_btn.setEnabled(False)

    # ── Actions ────────────────────────────────────────────────────────────

    def _open_last(self) -> None:
        if not self._last_path:
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(self._last_path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self._last_path])
            else:
                subprocess.Popen(["xdg-open", self._last_path])
        except Exception as e:
            QMessageBox.critical(self, "Open failed", str(e))

    def _open_folder(self) -> None:
        if not self._last_path:
            return
        folder = os.path.dirname(self._last_path) or self._last_path
        try:
            if sys.platform.startswith("win"):
                # Select the file in Explorer
                subprocess.Popen(["explorer", "/select,", self._last_path])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", self._last_path])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            QMessageBox.critical(self, "Open folder failed", str(e))

    def _copy_path(self) -> None:
        if not self._last_path:
            return
        QApplication.clipboard().setText(self._last_path)
        self._status_lbl.setText(f"✓ Path copied  —  {self._elide_middle(self._last_path, 70)}")

    # ── Utilities ──────────────────────────────────────────────────────────

    @staticmethod
    def _elide_middle(s: str, max_len: int) -> str:
        if len(s) <= max_len:
            return s
        half = (max_len - 3) // 2
        return s[:half] + "…" + s[-half:]

    # ── Public API ────────────────────────────────────────────────────────

    def refresh(self) -> None:
        pass

    def retranslate(self) -> None:
        self._title.setText(t("reports_title"))
