"""
app/ui/tabs/quick_scan_tab.py — Barcode-driven Quick Scan tab.

Shows live pricing per line + a totals card under the pending table.
On confirm the user picks an invoice layout (A4 or Thermal), the scan
commit writes an invoice row via InvoiceRepository, then ScanInvoiceService
renders the PDF and surfaces an "Open" action.
"""
from __future__ import annotations

import os
import sys

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy, QToolButton, QLineEdit,
    QDialog, QDialogButtonBox,
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QFont, QColor

from app.core.theme import THEME, _rgba
from app.core.i18n import t
from app.core.config import ShopConfig
from app.ui.components.barcode_line_edit import BarcodeLineEdit
from app.ui.components.collapsible_section import CollapsibleSection


# ── Layout-picker dialog ────────────────────────────────────────────────────

class _InvoiceLayoutDialog(QDialog):
    """Asks the user 'A4 invoice' vs 'Thermal receipt' before commit.
    Remembers the last choice via QSettings so subsequent scans skip the
    decision if the user prefers."""

    def __init__(self, parent=None, default: str = "a4"):
        super().__init__(parent)
        self.setWindowTitle("Save invoice as")
        self.setModal(True)
        self.setMinimumWidth(360)
        self._choice = default

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)

        hdr = QLabel("Save invoice as…")
        hdr.setObjectName("dlg_header")
        root.addWidget(hdr)

        tip = QLabel("Choose the output format for this commit.")
        tip.setObjectName("admin_form_card_desc")
        root.addWidget(tip)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._a4_btn = QPushButton("  A4 invoice")
        self._a4_btn.setObjectName("btn_primary")
        self._a4_btn.setMinimumHeight(40)
        self._a4_btn.clicked.connect(lambda: self._pick("a4"))

        self._th_btn = QPushButton("  Thermal receipt")
        self._th_btn.setObjectName("btn_secondary")
        self._th_btn.setMinimumHeight(40)
        self._th_btn.clicked.connect(lambda: self._pick("thermal"))

        btn_row.addWidget(self._a4_btn, 1)
        btn_row.addWidget(self._th_btn, 1)
        root.addLayout(btn_row)

        cancel = QPushButton(t("op_cancel"))
        cancel.setObjectName("btn_ghost")
        cancel.setMinimumHeight(32)
        cancel.clicked.connect(self.reject)
        root.addWidget(cancel)

    def _pick(self, choice: str) -> None:
        self._choice = choice
        self.accept()

    def choice(self) -> str:
        return self._choice


# ── Main tab ────────────────────────────────────────────────────────────────

class QuickScanTab(QWidget):
    """Barcode-driven Quick Scan with TAKEOUT/INSERT modes, pricing totals,
    customer field, and post-commit PDF invoice generation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        from app.services.scan_session_service import ScanSessionService
        self._session = ScanSessionService()
        self._qsettings = QSettings("StockPro", "StockManagerPro")
        self._build()

    # ── Build ──────────────────────────────────────────────────────────────

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
        self._title = QLabel(t("qscan_title"))
        self._title.setObjectName("dlg_header")
        top.addWidget(self._title)
        top.addStretch()
        root.addLayout(top)

        # Mode indicator bar
        self._mode_bar = QFrame()
        self._mode_bar.setObjectName("scan_mode_idle")
        mb_lay = QHBoxLayout(self._mode_bar)
        mb_lay.setContentsMargins(16, 10, 16, 10)
        self._mode_icon = QLabel("")
        self._mode_icon.setFixedWidth(24)
        self._mode_label = QLabel(t("qscan_mode_idle"))
        self._mode_label.setStyleSheet("font-weight:600; font-size:13px;")
        self._cancel_session_btn = QPushButton(t("qscan_cancel_btn"))
        self._cancel_session_btn.setObjectName("btn_ghost")
        self._cancel_session_btn.setFixedHeight(30)
        self._cancel_session_btn.clicked.connect(self._cancel_session)
        self._cancel_session_btn.hide()
        mb_lay.addWidget(self._mode_icon)
        mb_lay.addWidget(self._mode_label)
        mb_lay.addStretch()
        mb_lay.addWidget(self._cancel_session_btn)
        root.addWidget(self._mode_bar)

        # Customer row (optional, for invoice)
        cust_row = QHBoxLayout()
        cust_row.setSpacing(8)
        cust_lbl = QLabel("Customer")
        cust_lbl.setObjectName("card_label")
        cust_lbl.setFixedWidth(80)
        self._customer_edit = QLineEdit()
        self._customer_edit.setPlaceholderText("Customer name (optional, printed on invoice)")
        self._customer_edit.setMinimumHeight(34)
        cust_row.addWidget(cust_lbl)
        cust_row.addWidget(self._customer_edit, 1)
        root.addLayout(cust_row)

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

        # Pending table (8 columns: #, Item, Barcode, Qty, Unit Price, Line Total, After, Remove)
        # Column widths sized so every header label is fully visible at the
        # theme's 11px header font + 10/16 px padding. ITEM stays Stretch so
        # it only gets the leftover space (which keeps it from dominating).
        self._pending_tbl = QTableWidget()
        self._pending_tbl.setColumnCount(8)
        self._pending_tbl.setHorizontalHeaderLabels(
            ["#", t("col_item"), t("col_barcode"), "QTY",
             "UNIT PRICE", "LINE TOTAL", "AFTER", ""]
        )
        hh = self._pending_tbl.horizontalHeader()
        hh.setStretchLastSection(False)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col in (2, 3, 4, 5, 6, 7):
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
        self._pending_tbl.setColumnWidth(0, 40)
        self._pending_tbl.setColumnWidth(2, 140)   # BARCODE
        self._pending_tbl.setColumnWidth(3, 64)    # QTY
        self._pending_tbl.setColumnWidth(4, 110)   # UNIT PRICE
        self._pending_tbl.setColumnWidth(5, 120)   # LINE TOTAL
        self._pending_tbl.setColumnWidth(6, 80)    # AFTER
        self._pending_tbl.setColumnWidth(7, 40)    # ×
        self._pending_tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._pending_tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._pending_tbl.verticalHeader().setVisible(False)
        self._pending_tbl.setAlternatingRowColors(True)
        self._pending_tbl.setShowGrid(False)
        # Fixed generous height — inside a QScrollArea, without this the
        # table collapses to just its header row and pending rows vanish.
        self._pending_tbl.setMinimumHeight(320)
        self._pending_tbl.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        root.addWidget(self._pending_tbl, 2)

        # ── Totals card ──
        self._totals_card = QFrame()
        self._totals_card.setObjectName("qscan_totals_card")
        tc = QHBoxLayout(self._totals_card)
        tc.setContentsMargins(14, 10, 14, 10)
        tc.setSpacing(24)

        self._items_lbl = QLabel("ITEMS: 0")
        self._items_lbl.setStyleSheet("font-size:11px; font-weight:600; letter-spacing:0.06em;")
        self._subtotal_lbl = QLabel("SUBTOTAL: —")
        self._subtotal_lbl.setStyleSheet("font-size:12px; font-weight:600;")
        self._total_lbl = QLabel("GRAND TOTAL  —")
        self._total_lbl.setStyleSheet(
            "font-size:16px; font-weight:800;"
            " font-family:'JetBrains Mono', monospace;"
        )

        tc.addWidget(self._items_lbl)
        tc.addStretch()
        tc.addWidget(self._subtotal_lbl)
        tc.addWidget(self._total_lbl)
        root.addWidget(self._totals_card)

        # Action bar
        action = QHBoxLayout()
        action.setSpacing(8)
        self._summary_lbl = QLabel("")
        self._summary_lbl.setObjectName("section_caption")
        action.addWidget(self._summary_lbl)
        action.addStretch()
        self._btn_cancel = QPushButton(t("qscan_cancel_btn"))
        self._btn_cancel.setObjectName("btn_ghost")
        self._btn_cancel.setFixedHeight(36)
        self._btn_cancel.clicked.connect(self._cancel_session)
        self._btn_confirm = QPushButton(t("qscan_confirm_btn"))
        self._btn_confirm.setObjectName("btn_primary")
        self._btn_confirm.setFixedHeight(36)
        self._btn_confirm.clicked.connect(self._confirm_session)
        action.addWidget(self._btn_cancel)
        action.addWidget(self._btn_confirm)
        root.addLayout(action)

        # Recent sessions feed — larger so users can actually see feedback
        self._recent_section = CollapsibleSection(t("qscan_recent"))
        recent_scroll = QScrollArea()
        recent_scroll.setWidgetResizable(True)
        recent_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        recent_scroll.setFrameShape(QFrame.Shape.NoFrame)
        recent_scroll.setMinimumHeight(180)
        recent_inner = QWidget()
        self._recent_lay = QVBoxLayout(recent_inner)
        self._recent_lay.setContentsMargins(0, 0, 0, 0)
        self._recent_lay.setSpacing(4)
        self._recent_lay.addStretch()
        recent_scroll.setWidget(recent_inner)
        self._recent_section.add_widget(recent_scroll)
        self._recent_section.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        root.addWidget(self._recent_section)
        self._feed_items: list[QFrame] = []

        self._update_ui()

    def process_command_barcode(self, bc: str):
        self._on_scan(bc)

    # ── Update UI ──────────────────────────────────────────────────────────

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

    # ── Cancel / Confirm ───────────────────────────────────────────────────

    def _cancel_session(self):
        self._session.cancel()
        self._customer_edit.clear()
        self._update_ui()

    def _confirm_session(self):
        """Pop the layout-picker dialog, commit the session, render the PDF."""
        from app.models.scan_session import ScanEventType

        if not self._session.pending_items:
            self._add_feed_item(t("qscan_pending_empty"), "warn")
            return

        # Last layout remembered via QSettings
        last = self._qsettings.value("quick_scan/invoice_layout", "a4", type=str)
        dlg = _InvoiceLayoutDialog(self, default=last)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        layout = dlg.choice()
        self._qsettings.setValue("quick_scan/invoice_layout", layout)

        customer = self._customer_edit.text().strip()

        event = self._session.commit(layout=layout, customer_name=customer)

        if event.event_type == ScanEventType.BATCH_COMMITTED:
            self._add_feed_item(event.message, "success")

            invoice_id = getattr(event, "invoice_id", None)
            if invoice_id:
                try:
                    from app.services.scan_invoice_service import ScanInvoiceService
                    pdf_path = ScanInvoiceService().generate(invoice_id)
                    self._on_invoice_ready(invoice_id, pdf_path)
                except Exception as e:
                    self._add_feed_item(f"Invoice PDF failed: {e}", "error")

            self._customer_edit.clear()
        else:
            self._add_feed_item(event.message, "warn")

        self._update_ui()

    def _on_invoice_ready(self, invoice_id: int, pdf_path: str) -> None:
        """Feed a row with the invoice number + an Open button."""
        tk = THEME.tokens
        frame = QFrame()
        frame.setObjectName("scan_feed_success")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(8)

        name = os.path.basename(pdf_path)
        lbl = QLabel(f"✓  Invoice saved: {name}")
        lbl.setStyleSheet(f"color:{tk.green}; font-size:12px; font-weight:600;")
        lbl.setWordWrap(True)
        lay.addWidget(lbl, 1)

        open_btn = QPushButton("Open")
        open_btn.setObjectName("btn_secondary")
        open_btn.setFixedHeight(28)
        open_btn.clicked.connect(lambda: self._open_pdf(pdf_path))
        lay.addWidget(open_btn)

        self._recent_lay.insertWidget(0, frame)
        self._feed_items.insert(0, frame)
        while len(self._feed_items) > 50:
            old = self._feed_items.pop()
            self._recent_lay.removeWidget(old)
            old.deleteLater()

    @staticmethod
    def _open_pdf(path: str) -> None:
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", path])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass

    # ── Pending list render ────────────────────────────────────────────────

    def _refresh_pending(self):
        items = self._session.pending_items
        tk = THEME.tokens
        cfg = ShopConfig.get()
        self._pending_hdr.setText(t("qscan_pending_hdr", n=len(items)))
        self._pending_tbl.setRowCount(len(items))

        mono = QFont("JetBrains Mono", 11, QFont.Weight.Bold)
        mono_rg = QFont("JetBrains Mono", 11)

        for i, p in enumerate(items):
            row_color = tk.red if self._session.mode == "TAKEOUT" else tk.green

            num_it = QTableWidgetItem(str(i + 1))
            num_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._pending_tbl.setItem(i, 0, num_it)

            name_it = QTableWidgetItem(p.item.display_name)
            name_it.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self._pending_tbl.setItem(i, 1, name_it)

            bc_it = QTableWidgetItem(p.item.barcode or "—")
            bc_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._pending_tbl.setItem(i, 2, bc_it)

            qty_it = QTableWidgetItem(str(p.quantity))
            qty_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            qty_it.setFont(mono)
            qty_it.setForeground(QColor(row_color))
            self._pending_tbl.setItem(i, 3, qty_it)

            # Unit price
            price_text = cfg.format_currency(f"{p.unit_price:,.2f}") if p.unit_price else "—"
            up_it = QTableWidgetItem(price_text)
            up_it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            up_it.setFont(mono_rg)
            up_it.setForeground(QColor(tk.t2) if p.unit_price else QColor(tk.t4))
            self._pending_tbl.setItem(i, 4, up_it)

            # Line total
            lt_text = cfg.format_currency(f"{p.line_total:,.2f}") if p.unit_price else "—"
            lt_it = QTableWidgetItem(lt_text)
            lt_it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lt_it.setFont(mono)
            lt_it.setForeground(QColor(tk.t1) if p.unit_price else QColor(tk.t4))
            self._pending_tbl.setItem(i, 5, lt_it)

            # Predicted-after stock
            after_it = QTableWidgetItem(str(p.predicted_after))
            after_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            after_it.setFont(mono_rg)
            after_it.setForeground(QColor(tk.red) if p.predicted_after <= 0 else QColor(tk.t2))
            self._pending_tbl.setItem(i, 6, after_it)

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
            self._pending_tbl.setCellWidget(i, 7, rm_btn)

            self._pending_tbl.setRowHeight(i, 40)

        # Totals card
        subtotal = self._session.subtotal
        total = self._session.total
        self._items_lbl.setText(f"ITEMS: {self._session.pending_item_count}")
        if subtotal > 0:
            self._subtotal_lbl.setText(
                f"SUBTOTAL  {cfg.format_currency(f'{subtotal:,.2f}')}"
            )
            self._total_lbl.setText(
                f"GRAND TOTAL  {cfg.format_currency(f'{total:,.2f}')}"
            )
            self._total_lbl.setStyleSheet(
                f"color:{tk.green}; font-size:16px; font-weight:800;"
                f" font-family:'JetBrains Mono', monospace;"
            )
        else:
            self._subtotal_lbl.setText("SUBTOTAL  —")
            self._total_lbl.setText("GRAND TOTAL  —")
            self._total_lbl.setStyleSheet(
                f"color:{tk.t3}; font-size:16px; font-weight:800;"
                f" font-family:'JetBrains Mono', monospace;"
            )

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

    # ── Feed ────────────────────────────────────────────────────────────────

    def _add_feed_item(self, text: str, style: str):
        frame = QFrame()
        obj_map = {"success": "scan_feed_success", "error": "scan_feed_error", "warn": "scan_feed_warn"}
        frame.setObjectName(obj_map.get(style, "scan_feed_item"))
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(12, 8, 12, 8)
        lbl = QLabel(text)
        lbl.setWordWrap(True)
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

    # ── i18n / focus ────────────────────────────────────────────────────────

    def retranslate(self):
        self._title.setText(t("qscan_title"))
        self._scan_input.setPlaceholderText(t("qscan_scan_field"))
        self._btn_cancel.setText(t("qscan_cancel_btn"))
        self._btn_confirm.setText(t("qscan_confirm_btn"))
        self._cancel_session_btn.setText(t("qscan_cancel_btn"))
        self._pending_tbl.setHorizontalHeaderLabels(
            ["#", t("col_item"), t("col_barcode"), "Qty",
             "Unit Price", "Line Total", "After", ""]
        )
        self._update_ui()

    def _on_scan(self, bc: str):
        from app.models.scan_session import ScanEventType
        event = self._session.process_barcode(bc)

        if event.event_type == ScanEventType.MODE_CHANGED:
            self._update_ui()
        elif event.event_type in (ScanEventType.ITEM_ADDED, ScanEventType.ITEM_INCREMENTED):
            self._update_ui()
        elif event.event_type == ScanEventType.BATCH_COMMITTED:
            # CONFIRM barcode path — no layout dialog prompt; default to last choice
            self._add_feed_item(event.message, "success")
            invoice_id = getattr(event, "invoice_id", None)
            if invoice_id:
                try:
                    from app.services.scan_invoice_service import ScanInvoiceService
                    pdf_path = ScanInvoiceService().generate(invoice_id)
                    self._on_invoice_ready(invoice_id, pdf_path)
                except Exception as e:
                    self._add_feed_item(f"Invoice PDF failed: {e}", "error")
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
