"""
app/ui/pages/purchase_orders_page.py — Professional purchase order management page.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy, QMessageBox, QDialog,
    QFormLayout, QLineEdit, QComboBox, QDialogButtonBox,
    QTextEdit, QSpinBox, QDoubleSpinBox, QStackedWidget,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from app.core.config import ShopConfig
from app.core.theme import THEME, _rgba
from app.core.i18n import t
from app.core.icon_utils import get_colored_icon
from app.ui.components.responsive_table import make_table_responsive
from app.repositories.purchase_order_repo import PurchaseOrderRepository
from app.repositories.item_repo import ItemRepository
from app.repositories.supplier_repo import SupplierRepository
from app.services.purchase_order_service import PurchaseOrderService
from app.models.purchase_order import PurchaseOrder
from app.ui.workers.worker_pool import POOL

_po_repo = PurchaseOrderRepository()
_po_svc = PurchaseOrderService()
_item_repo = ItemRepository()
_sup_repo = SupplierRepository()


# ── KPI Card ──────────────────────────────────────────────────────────────────

class _KpiCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("summary_card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(88)
        self.setMaximumHeight(96)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(4)
        self._label = QLabel()
        self._label.setObjectName("card_label")
        self._value = QLabel("0")
        self._value.setObjectName("card_value")
        lay.addWidget(self._label)
        lay.addWidget(self._value)

    def set_data(self, label: str, value: str) -> None:
        self._label.setText(label)
        self._value.setText(value)


# ── Create/Edit PO Dialog ────────────────────────────────────────────────────

class _PODialog(QDialog):
    """Modal dialog for creating or editing a purchase order."""

    def __init__(self, parent=None, po: PurchaseOrder | None = None):
        super().__init__(parent)
        self._po = po
        self.setWindowTitle(t("po_dlg_title_edit") if po else t("po_dlg_title_new"))
        self.setMinimumWidth(480)
        THEME.apply(self)
        self._build()
        if po:
            self._populate(po)

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(16)

        hdr = QLabel(t("po_dlg_title_edit") if self._po else t("po_dlg_title_new"))
        hdr.setObjectName("dlg_header")
        lay.addWidget(hdr)

        form = QFormLayout()
        form.setSpacing(10)

        # Supplier dropdown
        self._supplier_combo = QComboBox()
        self._supplier_combo.addItem(t("po_supplier_none"), None)
        suppliers = _sup_repo.get_all()
        for sup in suppliers:
            if sup.is_active:
                self._supplier_combo.addItem(sup.name, sup.id)
        form.addRow(t("po_dlg_supplier"), self._supplier_combo)

        # Notes
        self._notes_edit = QTextEdit()
        self._notes_edit.setMaximumHeight(80)
        self._notes_edit.setPlaceholderText(t("po_dlg_notes"))
        form.addRow(t("po_dlg_notes"), self._notes_edit)

        lay.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton(t("alert_cancel"))
        cancel_btn.setObjectName("btn_ghost")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        ok_btn = QPushButton(t("po_dlg_title_edit") if self._po else t("po_btn_new"))
        ok_btn.setObjectName("btn_primary")
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        lay.addLayout(btn_row)

    def _populate(self, po: PurchaseOrder) -> None:
        if po.supplier_id:
            idx = self._supplier_combo.findData(po.supplier_id)
            if idx >= 0:
                self._supplier_combo.setCurrentIndex(idx)
        self._notes_edit.setPlainText(po.notes)

    def get_data(self) -> dict:
        return {
            "supplier_id": self._supplier_combo.currentData(),
            "notes": self._notes_edit.toPlainText().strip(),
        }


# ── Add Item to PO Dialog ────────────────────────────────────────────────────

class _AddItemDialog(QDialog):
    """Quick dialog to add an inventory item to a PO."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("po_dlg_add_item"))
        self.setMinimumWidth(440)
        THEME.apply(self)
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        hdr = QLabel(t("po_dlg_add_item"))
        hdr.setObjectName("dlg_header")
        lay.addWidget(hdr)

        # Item search
        self._search = QLineEdit()
        self._search.setPlaceholderText(t("po_dlg_item_search"))
        self._search.textChanged.connect(self._filter)
        lay.addWidget(self._search)

        # Item list
        self._item_table = QTableWidget(0, 3)
        self._item_table.setHorizontalHeaderLabels([t("col_item"), t("col_barcode"), t("col_stock")])
        hh = self._item_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._item_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._item_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._item_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._item_table.verticalHeader().setVisible(False)
        self._item_table.setMinimumHeight(150)
        lay.addWidget(self._item_table)

        # Qty and cost
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(QLabel(t("po_dlg_qty")))
        self._qty_spin = QSpinBox()
        self._qty_spin.setRange(1, 99999)
        self._qty_spin.setValue(1)
        row.addWidget(self._qty_spin)
        row.addWidget(QLabel(t("po_dlg_cost")))
        self._cost_spin = QDoubleSpinBox()
        self._cost_spin.setRange(0, 999999)
        self._cost_spin.setDecimals(2)
        row.addWidget(self._cost_spin)
        lay.addLayout(row)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton(t("alert_cancel"))
        cancel_btn.setObjectName("btn_ghost")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        ok_btn = QPushButton(t("po_dlg_add_item"))
        ok_btn.setObjectName("btn_primary")
        ok_btn.clicked.connect(self._validate_and_accept)
        btn_row.addWidget(ok_btn)
        lay.addLayout(btn_row)

        self._items_data: list = []
        self._filter("")

    def _filter(self, text: str):
        search = text.strip()
        items = _item_repo.get_all_items(search=search if len(search) >= 2 else "")
        self._items_data = items[:50]  # Limit to 50 for performance
        self._item_table.setRowCount(len(self._items_data))
        for i, item in enumerate(self._items_data):
            self._item_table.setItem(i, 0, QTableWidgetItem(item.display_name))
            self._item_table.setItem(i, 1, QTableWidgetItem(item.barcode or "—"))
            self._item_table.setItem(i, 2, QTableWidgetItem(str(item.stock)))
            self._item_table.setRowHeight(i, 36)

    def _validate_and_accept(self):
        row = self._item_table.currentRow()
        if row < 0 or row >= len(self._items_data):
            QMessageBox.warning(self, t("po_dlg_add_item"), t("po_warn_select_item"))
            return
        self.accept()

    def get_data(self) -> dict | None:
        row = self._item_table.currentRow()
        if row < 0 or row >= len(self._items_data):
            return None
        return {
            "item_id": self._items_data[row].id,
            "item_name": self._items_data[row].display_name,
            "quantity": self._qty_spin.value(),
            "cost_price": self._cost_spin.value(),
        }


# ── Empty State ───────────────────────────────────────────────────────────────

class _EmptyState(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(8)
        icon_lbl = QLabel("📋")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 48px;")
        lay.addWidget(icon_lbl)
        self._title = QLabel(t("po_empty_title"))
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setStyleSheet("font-size: 16px; font-weight: 600;")
        lay.addWidget(self._title)
        self._sub = QLabel(t("po_empty_sub"))
        self._sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sub.setObjectName("detail_threshold")
        lay.addWidget(self._sub)


# ── Main Page ─────────────────────────────────────────────────────────────────

class PurchaseOrdersPage(QWidget):
    """Professional purchase order management page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._build()
        self._refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(12)

        # ── Header ──
        hdr_row = QHBoxLayout()
        hdr_row.setSpacing(12)
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self._title = QLabel(t("po_title"))
        self._title.setStyleSheet("font-size: 20px; font-weight: 700;")
        title_col.addWidget(self._title)
        self._subtitle = QLabel(t("po_subtitle"))
        self._subtitle.setObjectName("admin_panel_subtitle")
        self._subtitle.setStyleSheet("font-size: 12px;")
        title_col.addWidget(self._subtitle)
        hdr_row.addLayout(title_col)
        hdr_row.addStretch()

        self._new_btn = QPushButton(t("po_btn_new"))
        self._new_btn.setObjectName("btn_primary")
        self._new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._new_btn.clicked.connect(self._create_po)
        hdr_row.addWidget(self._new_btn)
        root.addLayout(hdr_row)

        # ── KPIs ──
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)
        self._kpi_total = _KpiCard()
        self._kpi_draft = _KpiCard()
        self._kpi_sent = _KpiCard()
        self._kpi_received = _KpiCard()
        for card in (self._kpi_total, self._kpi_draft, self._kpi_sent, self._kpi_received):
            kpi_row.addWidget(card)
        root.addLayout(kpi_row)

        # ── Filter bar ──
        bar_row = QHBoxLayout()
        bar_row.setSpacing(8)
        self._search = QLineEdit()
        self._search.setObjectName("search_bar")
        self._search.setPlaceholderText(t("po_search_ph"))
        self._search.setMinimumHeight(38)
        self._search.setMaximumHeight(38)
        self._search.textChanged.connect(self._on_search)
        bar_row.addWidget(self._search, 1)

        self._status_combo = QComboBox()
        self._status_combo.setMinimumHeight(38)
        self._status_combo.addItem(t("po_filter_all"), "")
        for status_key, label_key in [
            ("DRAFT", "po_status_draft"), ("SENT", "po_status_sent"),
            ("PARTIAL", "po_status_partial"), ("RECEIVED", "po_status_received"),
            ("CLOSED", "po_status_closed"), ("CANCELLED", "po_status_cancelled"),
        ]:
            self._status_combo.addItem(t(label_key), status_key)
        self._status_combo.currentIndexChanged.connect(lambda: self._refresh())
        bar_row.addWidget(self._status_combo)
        root.addLayout(bar_row)

        # ── Table / Empty state ──
        self._stack = QStackedWidget()

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels([
            t("po_col_number"), t("po_col_supplier"), t("po_col_items"),
            t("po_col_total"), t("po_col_status"), t("po_col_date"), "",
        ])
        hh = self._table.horizontalHeader()
        hh.setMinimumSectionSize(40)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)
        self._table.setColumnWidth(6, 130)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.doubleClicked.connect(self._on_double_click)
        # Cols: 0=PO#  1=Supplier  2=Items  3=Total  4=Status  5=Date  6=Actions
        make_table_responsive(self._table, [
            (3, 820),   # Total  — hide when viewport < 820 px
            (2, 700),   # Items  — hide when viewport < 700 px
            (5, 580),   # Date   — hide when viewport < 580 px
        ])

        self._empty = _EmptyState()
        self._stack.addWidget(self._table)
        self._stack.addWidget(self._empty)
        root.addWidget(self._stack, 1)

    # ── Data ──────────────────────────────────────────────────────────────────

    def _refresh(self):
        """Fetch orders + summary off the UI thread; apply on return."""
        status = self._status_combo.currentData() if hasattr(self, '_status_combo') else ""
        search = self._search.text().strip() if hasattr(self, '_search') else ""
        def _fetch():
            return {
                "orders":  _po_repo.get_all(status=status or "", search=search),
                "summary": _po_repo.get_summary(),
            }
        POOL.submit_debounced("po_refresh", _fetch, self._apply_po_data, delay_ms=150)

    def _apply_po_data(self, payload: dict):
        """Main-thread render of PO KPIs + table with pre-fetched data."""
        orders = payload.get("orders", [])
        summary = payload.get("summary", {})
        self._orders = orders

        # KPIs
        self._kpi_total.set_data(t("po_kpi_total"), str(summary.get("total", 0) or 0))
        self._kpi_draft.set_data(t("po_kpi_draft"), str(summary.get("draft_count", 0) or 0))
        self._kpi_sent.set_data(t("po_kpi_sent"), str(summary.get("sent_count", 0) or 0))
        self._kpi_received.set_data(t("po_kpi_received"), str(summary.get("received_count", 0) or 0))

        if not orders:
            self._stack.setCurrentIndex(1)
            return
        self._stack.setCurrentIndex(0)

        tk = THEME.tokens
        cfg = ShopConfig.get()
        self._table.setRowCount(len(orders))
        for i, po in enumerate(orders):
            # PO number
            self._table.setItem(i, 0, QTableWidgetItem(po.po_number))
            # Supplier
            self._table.setItem(i, 1, QTableWidgetItem(po.supplier_name or "—"))
            # Items count
            items_it = QTableWidgetItem(str(po.line_count))
            items_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, 2, items_it)
            # Total
            self._table.setItem(i, 3, QTableWidgetItem(
                cfg.format_currency(po.total_value) if po.total_value else "—"
            ))
            # Status badge
            status_map = {
                "DRAFT":     (tk.t3,     _rgba(tk.t3, "20")),
                "SENT":      (tk.blue,   _rgba(tk.blue, "20")),
                "PARTIAL":   (tk.orange, _rgba(tk.orange, "20")),
                "RECEIVED":  (tk.green,  _rgba(tk.green, "20")),
                "CLOSED":    (tk.t4,     _rgba(tk.t4, "20")),
                "CANCELLED": (tk.red,    _rgba(tk.red, "20")),
            }
            status_labels = {
                "DRAFT": t("po_status_draft"), "SENT": t("po_status_sent"),
                "PARTIAL": t("po_status_partial"), "RECEIVED": t("po_status_received"),
                "CLOSED": t("po_status_closed"), "CANCELLED": t("po_status_cancelled"),
            }
            fg, bg = status_map.get(po.status, (tk.t3, "transparent"))
            lbl = QLabel(status_labels.get(po.status, po.status))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                f"color:{fg}; background:{bg}; border-radius:8px;"
                "font-weight:700; font-size:9px; padding:3px 8px;"
            )
            self._table.setCellWidget(i, 4, lbl)

            # Date
            self._table.setItem(i, 5, QTableWidgetItem(po.created_at[:10] if po.created_at else ""))

            # Action buttons — responsive width
            action_w = QWidget()
            action_lay = QHBoxLayout(action_w)
            action_lay.setContentsMargins(4, 2, 4, 2)
            action_lay.setSpacing(4)

            buttons = []
            if po.status == "DRAFT":
                buttons = [
                    ("edit", tk.blue, t("po_dlg_title_edit"), lambda _, p=po: self._edit_po(p)),
                    ("up", tk.green, t("po_action_send"), lambda _, p=po: self._send_po(p)),
                    ("delete", tk.red, t("po_confirm_delete"), lambda _, p=po: self._delete_po(p)),
                ]
            elif po.status == "SENT":
                buttons = [
                    ("down", tk.green, t("po_action_receive"), lambda _, p=po: self._receive_po(p)),
                    ("close", tk.red, t("po_action_cancel"), lambda _, p=po: self._cancel_po(p)),
                ]
            elif po.status == "PARTIAL":
                buttons = [
                    ("down", tk.green, t("po_action_receive"), lambda _, p=po: self._receive_po(p)),
                    ("close", tk.t3, t("po_action_close"), lambda _, p=po: self._close_po(p)),
                ]
            elif po.status == "RECEIVED":
                buttons = [
                    ("close", tk.t3, t("po_action_close"), lambda _, p=po: self._close_po(p)),
                ]

            for icon_name, color, tip, cb in buttons:
                btn = QPushButton()
                btn.setObjectName("admin_edit_btn")
                btn.setIcon(get_colored_icon(icon_name, color))
                btn.setIconSize(QSize(14, 14))
                btn.setToolTip(tip)
                btn.setFixedSize(28, 28)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(cb)
                action_lay.addWidget(btn)

            self._table.setCellWidget(i, 6, action_w)
            self._table.setRowHeight(i, 52)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _create_po(self):
        dlg = _PODialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            po_id = _po_svc.create_order(
                supplier_id=data["supplier_id"],
                notes=data["notes"],
            )
            # Open add items dialog
            self._add_items_to(po_id)
            self._refresh()

    def _edit_po(self, po: PurchaseOrder):
        full = _po_repo.get_by_id(po.id)
        if not full:
            return
        dlg = _PODialog(self, po=full)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            _po_repo.update(po.id, supplier_id=data["supplier_id"], notes=data["notes"])
            self._refresh()

    def _add_items_to(self, po_id: int):
        """Loop adding items until user cancels."""
        while True:
            dlg = _AddItemDialog(self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                break
            data = dlg.get_data()
            if data:
                _po_svc.add_item(po_id, data["item_id"], data["quantity"], data["cost_price"])

    def _send_po(self, po: PurchaseOrder):
        try:
            _po_svc.send_order(po.id)
            self._refresh()
        except ValueError as e:
            QMessageBox.warning(self, t("po_action_send"), str(e))

    def _receive_po(self, po: PurchaseOrder):
        try:
            result = _po_svc.receive_order(po.id)
            QMessageBox.information(
                self, t("po_action_receive"),
                t("po_receive_success", units=result["units"], items=result["items"]),
            )
            self._refresh()
        except ValueError as e:
            QMessageBox.warning(self, t("po_action_receive"), str(e))

    def _close_po(self, po: PurchaseOrder):
        try:
            _po_svc.close_order(po.id)
            self._refresh()
        except ValueError as e:
            QMessageBox.warning(self, t("po_action_close"), str(e))

    def _cancel_po(self, po: PurchaseOrder):
        ok = QMessageBox.question(
            self, t("po_action_cancel"), t("po_confirm_delete"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ok == QMessageBox.StandardButton.Yes:
            try:
                _po_svc.cancel_order(po.id)
                self._refresh()
            except ValueError as e:
                QMessageBox.warning(self, t("po_action_cancel"), str(e))

    def _delete_po(self, po: PurchaseOrder):
        ok = QMessageBox.question(
            self, t("po_confirm_delete"), t("po_confirm_delete"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ok == QMessageBox.StandardButton.Yes:
            _po_repo.delete(po.id)
            self._refresh()

    def _on_double_click(self):
        row = self._table.currentRow()
        if 0 <= row < len(self._orders):
            po = self._orders[row]
            if po.status == "DRAFT":
                self._add_items_to(po.id)
                self._refresh()

    def _on_search(self, _text: str):
        self._refresh()

    def retranslate(self):
        self._title.setText(t("po_title"))
        self._subtitle.setText(t("po_subtitle"))
        self._new_btn.setText(t("po_btn_new"))
        self._refresh()

    def refresh(self):
        self._refresh()
