"""
app/ui/tabs/quick_scan_tab.py — Barcode-driven Quick Scan tab.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy, QToolButton,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

from app.core.theme import THEME, _rgba
from app.core.i18n import t
from app.ui.components.barcode_line_edit import BarcodeLineEdit
from app.ui.components.collapsible_section import CollapsibleSection


class QuickScanTab(QWidget):
    """Barcode-driven Quick Scan with TAKEOUT/INSERT modes and pending list."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        from app.services.scan_session_service import ScanSessionService
        self._session = ScanSessionService()
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        _scroll = QScrollArea()
        _scroll.setWidgetResizable(True)
        _scroll.setFrameShape(QFrame.Shape.NoFrame)
        _inner = QWidget()
        _scroll.setWidget(_inner)
        outer.addWidget(_scroll)

        root = QVBoxLayout(_inner)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Top bar: title
        top = QHBoxLayout()
        self._title = QLabel(t("qscan_title")); self._title.setObjectName("dlg_header")
        top.addWidget(self._title); top.addStretch()
        root.addLayout(top)

        # Mode indicator bar
        self._mode_bar = QFrame(); self._mode_bar.setObjectName("scan_mode_idle")
        mb_lay = QHBoxLayout(self._mode_bar); mb_lay.setContentsMargins(16, 10, 16, 10)
        self._mode_icon = QLabel(""); self._mode_icon.setFixedWidth(24)
        self._mode_label = QLabel(t("qscan_mode_idle"))
        self._mode_label.setStyleSheet("font-weight:600; font-size:13px;")
        self._cancel_session_btn = QPushButton(t("qscan_cancel_btn"))
        self._cancel_session_btn.setObjectName("btn_ghost")
        self._cancel_session_btn.setFixedHeight(30)
        self._cancel_session_btn.clicked.connect(self._cancel_session)
        self._cancel_session_btn.hide()
        mb_lay.addWidget(self._mode_icon); mb_lay.addWidget(self._mode_label)
        mb_lay.addStretch(); mb_lay.addWidget(self._cancel_session_btn)
        root.addWidget(self._mode_bar)

        # Scan input
        self._scan_input = BarcodeLineEdit()
        self._scan_input.setObjectName("search_bar")
        self._scan_input.setPlaceholderText(t("qscan_scan_field"))
        self._scan_input.setMinimumHeight(52)
        self._scan_input.setFont(QFont("Segoe UI", 14))
        self._scan_input.barcode_scanned.connect(self._on_scan)
        root.addWidget(self._scan_input)

        # Pending table header
        self._pending_hdr = QLabel(t("qscan_pending_hdr", n=0))
        self._pending_hdr.setObjectName("detail_section_hdr")
        root.addWidget(self._pending_hdr)

        # Pending table
        self._pending_tbl = QTableWidget()
        self._pending_tbl.setColumnCount(6)
        self._pending_tbl.setHorizontalHeaderLabels(["#", t("col_item"), t("col_barcode"), "Qty", "After", ""])
        hh = self._pending_tbl.horizontalHeader()
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._pending_tbl.setColumnWidth(0, 30)
        self._pending_tbl.setColumnWidth(2, 100)
        self._pending_tbl.setColumnWidth(3, 45)
        self._pending_tbl.setColumnWidth(4, 55)
        self._pending_tbl.setColumnWidth(5, 30)
        self._pending_tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._pending_tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._pending_tbl.verticalHeader().setVisible(False)
        self._pending_tbl.setAlternatingRowColors(True)
        self._pending_tbl.setShowGrid(False)
        root.addWidget(self._pending_tbl, 1)

        # Action bar
        action = QHBoxLayout(); action.setSpacing(8)
        self._summary_lbl = QLabel("")
        self._summary_lbl.setObjectName("section_caption")
        action.addWidget(self._summary_lbl); action.addStretch()
        self._btn_cancel = QPushButton(t("qscan_cancel_btn"))
        self._btn_cancel.setObjectName("btn_ghost"); self._btn_cancel.setFixedHeight(36)
        self._btn_cancel.clicked.connect(self._cancel_session)
        self._btn_confirm = QPushButton(t("qscan_confirm_btn"))
        self._btn_confirm.setObjectName("btn_primary"); self._btn_confirm.setFixedHeight(36)
        self._btn_confirm.clicked.connect(self._confirm_session)
        action.addWidget(self._btn_cancel); action.addWidget(self._btn_confirm)
        root.addLayout(action)

        # Recent sessions feed
        self._recent_section = CollapsibleSection(t("qscan_recent"))
        recent_scroll = QScrollArea()
        recent_scroll.setWidgetResizable(True)
        recent_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        recent_scroll.setFrameShape(QFrame.Shape.NoFrame)
        recent_inner = QWidget()
        self._recent_lay = QVBoxLayout(recent_inner)
        self._recent_lay.setContentsMargins(0, 0, 0, 0)
        self._recent_lay.setSpacing(4)
        self._recent_lay.addStretch()
        recent_scroll.setWidget(recent_inner)
        self._recent_section.add_widget(recent_scroll)
        root.addWidget(self._recent_section, 1)
        self._feed_items: list[QFrame] = []

        self._update_ui()

    def process_command_barcode(self, bc: str):
        self._on_scan(bc)

    def _update_ui(self):
        mode = self._session.mode
        tk = THEME.tokens

        if self._session.waiting_for_color:
            self._mode_bar.setObjectName("scan_mode_insert")
            self._mode_icon.setText("🎨")
            self._mode_icon.setStyleSheet(f"color:{tk.orange}; font-size:18px;")
            colors = ", ".join(self._session.available_colors)
            self._mode_label.setText(
                f"{t('qscan_waiting_color')} — {self._session.waiting_item_name}\n{colors}"
            )
            self._mode_label.setStyleSheet(f"color:{tk.orange}; font-weight:600; font-size:12px;")
            self._cancel_session_btn.show()
        elif mode == "TAKEOUT":
            self._mode_bar.setObjectName("scan_mode_takeout")
            self._mode_icon.setText("↓")
            self._mode_icon.setStyleSheet(f"color:{tk.red}; font-size:18px; font-weight:700;")
            self._mode_label.setText(t("qscan_mode_takeout"))
            self._mode_label.setStyleSheet(f"color:{tk.red}; font-weight:600; font-size:13px;")
            self._cancel_session_btn.show()
        elif mode == "INSERT":
            self._mode_bar.setObjectName("scan_mode_insert")
            self._mode_icon.setText("↑")
            self._mode_icon.setStyleSheet(f"color:{tk.green}; font-size:18px; font-weight:700;")
            self._mode_label.setText(t("qscan_mode_insert"))
            self._mode_label.setStyleSheet(f"color:{tk.green}; font-weight:600; font-size:13px;")
            self._cancel_session_btn.show()
        else:
            self._mode_bar.setObjectName("scan_mode_idle")
            self._mode_icon.setText("")
            self._mode_label.setText(t("qscan_mode_idle"))
            self._mode_label.setStyleSheet(f"color:{tk.t3}; font-weight:600; font-size:13px;")
            self._cancel_session_btn.hide()

        self._mode_bar.style().unpolish(self._mode_bar)
        self._mode_bar.style().polish(self._mode_bar)
        self._refresh_pending()

    def _cancel_session(self):
        self._session.cancel()
        self._update_ui()

    def _confirm_session(self):
        from app.models.scan_session import ScanEventType
        event = self._session.commit()
        if event.event_type == ScanEventType.BATCH_COMMITTED:
            self._add_feed_item(event.message, "success")
        self._update_ui()

    def _refresh_pending(self):
        items = self._session.pending_items
        tk = THEME.tokens
        self._pending_hdr.setText(t("qscan_pending_hdr", n=len(items)))
        self._pending_tbl.setRowCount(len(items))

        for i, p in enumerate(items):
            row_color = tk.red if self._session.mode == "TAKEOUT" else tk.green

            num_it = QTableWidgetItem(str(i + 1))
            num_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._pending_tbl.setItem(i, 0, num_it)

            name_it = QTableWidgetItem(p.item.display_name)
            name_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._pending_tbl.setItem(i, 1, name_it)

            bc_it = QTableWidgetItem(p.item.barcode or "—")
            bc_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._pending_tbl.setItem(i, 2, bc_it)

            qty_it = QTableWidgetItem(str(p.quantity))
            qty_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            qty_it.setFont(QFont("JetBrains Mono", 11, QFont.Weight.Bold))
            qty_it.setForeground(QColor(row_color))
            self._pending_tbl.setItem(i, 3, qty_it)

            after_it = QTableWidgetItem(str(p.predicted_after))
            after_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            after_it.setFont(QFont("JetBrains Mono", 11))
            after_it.setForeground(QColor(tk.red) if p.predicted_after <= 0 else QColor(tk.t2))
            self._pending_tbl.setItem(i, 4, after_it)

            rm_btn = QToolButton()
            rm_btn.setText("×")
            rm_btn.setFixedSize(24, 24)
            rm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            rm_btn.setStyleSheet(
                f"QToolButton {{ color:{tk.red}; background:transparent; border:none;"
                f"  font-weight:700; font-size:13px; }}"
                f"QToolButton:hover {{ background:{_rgba(tk.red, '20')}; border-radius:4px; }}"
            )
            rm_btn.clicked.connect(lambda _=False, idx=i: self._remove_pending(idx))
            self._pending_tbl.setCellWidget(i, 5, rm_btn)

            self._pending_tbl.setRowHeight(i, 40)

        total_qty = self._session.pending_count
        total_items = self._session.pending_item_count
        self._summary_lbl.setText(
            t("qscan_total_summary", ops=total_qty, items=total_items) if total_items else ""
        )
        has_pending = total_items > 0
        self._btn_cancel.setEnabled(has_pending or self._session.mode is not None)
        self._btn_confirm.setEnabled(has_pending)

    def _remove_pending(self, index: int):
        self._session.remove_pending(index)
        self._refresh_pending()
        self._scan_input.setFocus()

    def _add_feed_item(self, text: str, style: str):
        frame = QFrame()
        obj_map = {"success": "scan_feed_success", "error": "scan_feed_error", "warn": "scan_feed_warn"}
        frame.setObjectName(obj_map.get(style, "scan_feed_item"))
        lay = QHBoxLayout(frame); lay.setContentsMargins(12, 8, 12, 8)
        lbl = QLabel(text); lbl.setWordWrap(True)
        tk = THEME.tokens
        color_map = {"success": tk.green, "error": tk.red, "warn": tk.orange}
        lbl.setStyleSheet(f"color:{color_map.get(style, tk.t1)}; font-size:12px;")
        lay.addWidget(lbl)
        self._recent_lay.insertWidget(0, frame)
        self._feed_items.insert(0, frame)
        while len(self._feed_items) > 50:
            old = self._feed_items.pop()
            self._recent_lay.removeWidget(old)
            old.deleteLater()

    def retranslate(self):
        self._title.setText(t("qscan_title"))
        self._scan_input.setPlaceholderText(t("qscan_scan_field"))
        self._btn_cancel.setText(t("qscan_cancel_btn"))
        self._btn_confirm.setText(t("qscan_confirm_btn"))
        self._cancel_session_btn.setText(t("qscan_cancel_btn"))
        self._update_ui()

    def _on_scan(self, bc: str):
        from app.models.scan_session import ScanEventType
        event = self._session.process_barcode(bc)

        if event.event_type == ScanEventType.MODE_CHANGED:
            self._update_ui()
        elif event.event_type in (ScanEventType.ITEM_ADDED, ScanEventType.ITEM_INCREMENTED):
            self._update_ui()
        elif event.event_type == ScanEventType.BATCH_COMMITTED:
            self._add_feed_item(event.message, "success")
            self._update_ui()
        elif event.event_type == ScanEventType.BATCH_EMPTY:
            self._add_feed_item(event.message, "warn")
        elif event.event_type == ScanEventType.NOT_FOUND:
            self._add_feed_item(event.message, "error")
        elif event.event_type == ScanEventType.NO_MODE:
            self._add_feed_item(event.message, "warn")
        elif event.event_type == ScanEventType.INSUFFICIENT_STOCK:
            self._add_feed_item(event.message, "warn")
        elif event.event_type == ScanEventType.SESSION_ACTIVE:
            self._add_feed_item(event.message, "warn")
        elif event.event_type == ScanEventType.WAITING_COLOR:
            self._add_feed_item(event.message, "warn")
            self._update_ui()
        elif event.event_type == ScanEventType.COLOR_APPLIED:
            self._update_ui()

        self._scan_input.clear()
        self._scan_input.setFocus()

    def focus_input(self):
        self._scan_input.setFocus()
        self._scan_input.clear()
