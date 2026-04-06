"""
app/ui/pages/transactions_page.py — Full transactions page with filters,
date-range picker, summary strip, pagination, and export.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QDateEdit, QPushButton, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, QDate, QTimer
from PyQt6.QtGui import QFont

from app.core.theme import THEME
from app.core.i18n import t
from app.core.icon_utils import get_button_icon
from app.repositories.transaction_repo import TransactionRepository
from app.ui.components.transaction_table import TransactionTable
from app.ui.workers.worker_pool import POOL

_PAGE_SIZE = 100


class TransactionsPage(QWidget):
    """Full-featured transaction history viewer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._repo = TransactionRepository()
        self._offset = 0
        self._total = 0
        self._build_ui()
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(300)
        self._debounce.timeout.connect(self._apply_filters)

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)

        # ── Title bar ────────────────────────────────────────────────────────
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        self._title = QLabel(t("txn_page_title"))
        self._title.setObjectName("section_caption")
        self._title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_row.addWidget(self._title)
        title_row.addStretch()

        self._export_btn = QPushButton(t("txn_export"))
        self._export_btn.setObjectName("btn_secondary")
        self._export_btn.setIcon(get_button_icon("export"))
        self._export_btn.clicked.connect(self._export)
        title_row.addWidget(self._export_btn)

        self._refresh_btn = QPushButton()
        self._refresh_btn.setObjectName("btn_secondary")
        self._refresh_btn.setIcon(get_button_icon("refresh"))
        self._refresh_btn.clicked.connect(self._apply_filters)
        title_row.addWidget(self._refresh_btn)
        outer.addLayout(title_row)

        # ── Filter bar ───────────────────────────────────────────────────────
        filt = QHBoxLayout()
        filt.setContentsMargins(0, 0, 0, 0)
        filt.setSpacing(8)

        self._search = QLineEdit()
        self._search.setPlaceholderText(t("txn_search_ph"))
        self._search.setMinimumWidth(180)
        self._search.textChanged.connect(lambda: self._debounce.start())
        filt.addWidget(self._search)

        self._op_combo = QComboBox()
        self._op_combo.addItem(t("txn_filter_all_ops"), "")
        self._op_combo.addItem(t("txn_filter_in"), "IN")
        self._op_combo.addItem(t("txn_filter_out"), "OUT")
        self._op_combo.addItem(t("txn_filter_adjust"), "ADJUST")
        self._op_combo.addItem(t("txn_filter_create"), "CREATE")
        self._op_combo.currentIndexChanged.connect(lambda: self._apply_filters())
        filt.addWidget(self._op_combo)

        filt.addWidget(QLabel(t("txn_date_from")))
        self._date_from = QDateEdit()
        self._date_from.setCalendarPopup(True)
        self._date_from.setDate(QDate.currentDate().addMonths(-1))
        self._date_from.setDisplayFormat("yyyy-MM-dd")
        self._date_from.dateChanged.connect(lambda: self._apply_filters())
        filt.addWidget(self._date_from)

        filt.addWidget(QLabel(t("txn_date_to")))
        self._date_to = QDateEdit()
        self._date_to.setCalendarPopup(True)
        self._date_to.setDate(QDate.currentDate())
        self._date_to.setDisplayFormat("yyyy-MM-dd")
        self._date_to.dateChanged.connect(lambda: self._apply_filters())
        filt.addWidget(self._date_to)

        filt.addStretch()
        outer.addLayout(filt)

        # ── Summary strip ────────────────────────────────────────────────────
        self._summary_frame = QFrame()
        self._summary_frame.setObjectName("summary_strip")
        self._summary_frame.setMinimumHeight(32)
        self._summary_frame.setMaximumHeight(40)
        sf_lay = QHBoxLayout(self._summary_frame)
        sf_lay.setContentsMargins(12, 0, 12, 0)
        sf_lay.setSpacing(20)

        self._lbl_total = QLabel()
        self._lbl_total.setObjectName("summary_stat")
        self._lbl_in = QLabel()
        self._lbl_in.setObjectName("summary_stat_green")
        self._lbl_out = QLabel()
        self._lbl_out.setObjectName("summary_stat_red")
        self._lbl_net = QLabel()
        self._lbl_net.setObjectName("summary_stat")

        sf_lay.addWidget(self._lbl_total)
        sf_lay.addWidget(self._lbl_in)
        sf_lay.addWidget(self._lbl_out)
        sf_lay.addWidget(self._lbl_net)
        sf_lay.addStretch()

        self._lbl_showing = QLabel()
        self._lbl_showing.setObjectName("summary_stat_dim")
        sf_lay.addWidget(self._lbl_showing)
        outer.addWidget(self._summary_frame)

        # ── Table ────────────────────────────────────────────────────────────
        self._table = TransactionTable()
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_ctx)
        outer.addWidget(self._table, 1)

        # ── Load More button ─────────────────────────────────────────────────
        self._more_row = QHBoxLayout()
        self._more_row.setContentsMargins(0, 0, 0, 0)
        self._more_row.addStretch()
        self._more_btn = QPushButton(t("txn_load_more"))
        self._more_btn.setObjectName("btn_secondary")
        self._more_btn.clicked.connect(self._load_more)
        self._more_row.addWidget(self._more_btn)
        self._more_row.addStretch()
        outer.addLayout(self._more_row)

        # ── Empty state ──────────────────────────────────────────────────────
        self._empty = QWidget()
        el = QVBoxLayout(self._empty)
        el.setAlignment(Qt.AlignmentFlag.AlignCenter)
        em_icon = QLabel("📋")
        em_icon.setFont(QFont("Segoe UI Emoji", 36))
        em_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(em_icon)
        self._empty_title = QLabel(t("empty_transactions"))
        self._empty_title.setObjectName("empty_title")
        self._empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        el.addWidget(self._empty_title)
        self._empty_sub = QLabel(t("empty_transactions_sub"))
        self._empty_sub.setObjectName("empty_sub")
        self._empty_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(self._empty_sub)
        self._empty.hide()
        outer.addWidget(self._empty)

    # ── Data ─────────────────────────────────────────────────────────────────

    def _get_filter_params(self) -> dict:
        return {
            "search": self._search.text().strip(),
            "operation": self._op_combo.currentData() or "",
            "date_from": self._date_from.date().toString("yyyy-MM-dd"),
            "date_to": self._date_to.date().toString("yyyy-MM-dd"),
        }

    def fetch_filtered(self) -> dict:
        """Background-safe: run all three DB queries and return raw data."""
        params = self._get_filter_params()
        return {
            "rows":  self._repo.get_filtered(**params, limit=_PAGE_SIZE, offset=0),
            "total": self._repo.count_filtered(**params),
            "stats": self._repo.get_summary_stats(**params),
        }

    def load_results(self, data: dict) -> None:
        """Main-thread only: push fetched data into widgets."""
        rows, stats = data["rows"], data["stats"]
        self._offset = 0
        self._total  = data["total"]
        self._table.load(rows)
        self._update_summary(stats, len(rows))
        self._toggle_empty(len(rows) == 0 and self._total == 0)

    def _apply_filters(self) -> None:
        """Async: kick off background fetch, 100 ms debounce to absorb rapid signals."""
        POOL.submit_debounced("txn_filter", self.fetch_filtered, self.load_results,
                              delay_ms=100)

    def _load_more(self) -> None:
        self._offset += _PAGE_SIZE
        params = self._get_filter_params()
        rows = self._repo.get_filtered(**params, limit=_PAGE_SIZE, offset=self._offset)
        if rows:
            existing = self._table.rowCount()
            self._table.load(
                self._repo.get_filtered(**params, limit=self._offset + _PAGE_SIZE, offset=0)
            )
        shown = min(self._offset + _PAGE_SIZE, self._total)
        self._lbl_showing.setText(t("txn_showing", shown=shown, total=self._total))
        self._more_btn.setVisible(shown < self._total)

    def _update_summary(self, stats: dict, shown: int) -> None:
        total = stats["total"]
        total_in = stats["total_in"]
        total_out = stats["total_out"]
        net = total_in - total_out

        self._lbl_total.setText(t("txn_summary_total", n=total))
        self._lbl_in.setText(t("txn_summary_in", n=total_in))
        self._lbl_out.setText(t("txn_summary_out", n=total_out))
        net_str = f"+{net}" if net >= 0 else str(net)
        self._lbl_net.setText(t("txn_summary_net", n=net_str))
        self._lbl_showing.setText(t("txn_showing", shown=shown, total=self._total))
        self._more_btn.setVisible(shown < self._total)

    def _toggle_empty(self, empty: bool) -> None:
        self._table.setVisible(not empty)
        self._summary_frame.setVisible(not empty)
        self._more_btn.setVisible(not empty and self._table.rowCount() < self._total)
        self._empty.setVisible(empty)

    # ── Context menu ─────────────────────────────────────────────────────────

    def _show_ctx(self, pos) -> None:
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QGuiApplication
        row = self._table.rowAt(pos.y())
        if row < 0:
            return
        menu = QMenu(self)

        copy_act = menu.addAction(t("ctx_copy_txn"))
        action = menu.exec(self._table.viewport().mapToGlobal(pos))
        if action == copy_act:
            texts = []
            for c in range(self._table.columnCount()):
                it = self._table.item(row, c)
                if it:
                    texts.append(it.text())
            QGuiApplication.clipboard().setText("  |  ".join(texts))

    # ── Export ───────────────────────────────────────────────────────────────

    def _export(self) -> None:
        try:
            from app.services.report_service import ReportService
            svc = ReportService()
            path = svc.generate_transaction_report()
            if path:
                import os, subprocess, sys
                if sys.platform == "win32":
                    os.startfile(path)
                else:
                    subprocess.Popen(["xdg-open", path])
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, t("db_tools_error"), str(e))

    # ── Public API ───────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Called when page becomes visible."""
        self._apply_filters()

    def retranslate(self) -> None:
        self._title.setText(t("txn_page_title"))
        self._search.setPlaceholderText(t("txn_search_ph"))
        self._export_btn.setText(t("txn_export"))
        self._more_btn.setText(t("txn_load_more"))
        self._empty_title.setText(t("empty_transactions"))
        self._empty_sub.setText(t("empty_transactions_sub"))
        # Rebuild combo
        self._op_combo.blockSignals(True)
        idx = self._op_combo.currentIndex()
        self._op_combo.clear()
        self._op_combo.addItem(t("txn_filter_all_ops"), "")
        self._op_combo.addItem(t("txn_filter_in"), "IN")
        self._op_combo.addItem(t("txn_filter_out"), "OUT")
        self._op_combo.addItem(t("txn_filter_adjust"), "ADJUST")
        self._op_combo.addItem(t("txn_filter_create"), "CREATE")
        self._op_combo.setCurrentIndex(idx)
        self._op_combo.blockSignals(False)
        self._table.retranslate()
        # No _apply_filters() here — data refresh is deferred by main_window via POOL.
