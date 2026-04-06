"""
app/ui/pages/reports_page.py — Report generation page with selectable report
types and PDF preview/open capability.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QMessageBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from app.core.theme import THEME
from app.core.i18n import t
from app.core.icon_utils import get_button_icon


# ── Background worker ────────────────────────────────────────────────────────

class _ReportWorker(QThread):
    finished = pyqtSignal(str)    # path on success
    errored  = pyqtSignal(str)    # message on error

    def __init__(self, report_type: str, parent=None):
        super().__init__(parent)
        self._type = report_type

    def run(self):
        try:
            from app.services.report_service import ReportService
            svc = ReportService()
            if self._type == "inventory":
                path = svc.generate_inventory_report()
            elif self._type == "low_stock":
                path = svc.generate_low_stock_report()
            elif self._type == "transactions":
                path = svc.generate_transaction_report()
            elif self._type == "summary":
                path = svc.generate_summary_report()
            elif self._type == "audit":
                path = svc.generate_audit_sheet()
            elif self._type == "discrepancy":
                path = svc.generate_discrepancy_report()
            elif self._type == "barcode_labels":
                path = svc.generate_barcode_labels()
            else:
                self.errored.emit(f"Unknown report type: {self._type}")
                return
            self.finished.emit(path)
        except Exception as e:
            self.errored.emit(str(e))


# ── Report card widget ───────────────────────────────────────────────────────

class _ReportCard(QFrame):
    """Clickable card representing one report type."""
    clicked = pyqtSignal(str)  # report_type

    def __init__(self, report_type: str, icon: str,
                 title_key: str, desc_key: str, parent=None):
        super().__init__(parent)
        self._type = report_type
        self._title_key = title_key
        self._desc_key = desc_key
        self.setObjectName("report_card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(80)
        self.setMaximumHeight(110)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(14)

        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Segoe UI Emoji", 28))
        icon_lbl.setFixedWidth(48)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(icon_lbl)

        text_lay = QVBoxLayout()
        text_lay.setSpacing(4)
        self._title_lbl = QLabel(t(title_key))
        self._title_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        text_lay.addWidget(self._title_lbl)
        self._desc_lbl = QLabel(t(desc_key))
        self._desc_lbl.setObjectName("card_meta_dim")
        self._desc_lbl.setWordWrap(True)
        text_lay.addWidget(self._desc_lbl)
        lay.addLayout(text_lay, 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._type)
        super().mousePressEvent(event)

    def retranslate(self):
        self._title_lbl.setText(t(self._title_key))
        self._desc_lbl.setText(t(self._desc_key))


# ── Main page ────────────────────────────────────────────────────────────────

class ReportsPage(QWidget):
    """Page for selecting and generating PDF reports."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: _ReportWorker | None = None
        self._cards: list[_ReportCard] = []
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(16)

        # Title
        self._title = QLabel(t("reports_title"))
        self._title.setObjectName("section_caption")
        self._title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        outer.addWidget(self._title)

        # Report cards
        report_types = [
            ("inventory",    "📦", "report_type_inventory",    "report_type_inventory_desc"),
            ("low_stock",    "⚠",  "report_type_low_stock",    "report_type_low_stock_desc"),
            ("transactions", "📋", "report_type_transactions", "report_type_transactions_desc"),
            ("summary",      "📊", "report_type_summary",      "report_type_summary_desc"),
            ("audit",        "📝", "report_type_audit",        "report_type_audit_desc"),
            ("discrepancy",  "🔍", "report_type_discrepancy",  "report_type_discrepancy_desc"),
            ("barcode_labels","🏷", "report_type_barcode",      "report_type_barcode_desc"),
        ]
        for rtype, icon, title_key, desc_key in report_types:
            card = _ReportCard(rtype, icon, title_key, desc_key, parent=self)
            card.clicked.connect(self._generate)
            outer.addWidget(card)
            self._cards.append(card)

        outer.addStretch()

        # Status bar
        self._status_frame = QFrame()
        self._status_frame.setFixedHeight(40)
        sl = QHBoxLayout(self._status_frame)
        sl.setContentsMargins(12, 0, 12, 0)
        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("footer_status")
        sl.addWidget(self._status_lbl)
        sl.addStretch()
        self._open_btn = QPushButton(t("report_open"))
        self._open_btn.setObjectName("btn_primary")
        self._open_btn.setIcon(get_button_icon("export"))
        self._open_btn.hide()
        self._open_btn.clicked.connect(self._open_last)
        sl.addWidget(self._open_btn)
        outer.addWidget(self._status_frame)

        self._last_path: str = ""

    # ── Generate ─────────────────────────────────────────────────────────────

    def _generate(self, report_type: str) -> None:
        if self._worker and self._worker.isRunning():
            return
        self._status_lbl.setText(t("report_generating"))
        self._open_btn.hide()
        self._worker = _ReportWorker(report_type, self)
        self._worker.finished.connect(self._on_done)
        self._worker.errored.connect(self._on_error)
        self._worker.start()

    def _on_done(self, path: str) -> None:
        self._last_path = path
        self._status_lbl.setText(t("report_success"))
        self._open_btn.show()

    def _on_error(self, msg: str) -> None:
        self._status_lbl.setText(t("report_error", err=msg))
        self._open_btn.hide()

    def _open_last(self) -> None:
        if not self._last_path:
            return
        import os, subprocess, sys
        try:
            if sys.platform == "win32":
                os.startfile(self._last_path)
            else:
                subprocess.Popen(["xdg-open", self._last_path])
        except Exception as e:
            QMessageBox.critical(self, t("db_tools_error"), str(e))

    # ── Public API ───────────────────────────────────────────────────────────

    def refresh(self) -> None:
        pass  # Nothing to preload

    def retranslate(self) -> None:
        self._title.setText(t("reports_title"))
        self._open_btn.setText(t("report_open"))
        for card in self._cards:
            card.retranslate()
