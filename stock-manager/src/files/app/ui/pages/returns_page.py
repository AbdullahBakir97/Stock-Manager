"""
app/ui/pages/returns_page.py — Professional returns management page.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QSizePolicy, QMessageBox, QDialog, QFormLayout, QLineEdit,
    QComboBox, QSpinBox, QDoubleSpinBox, QStackedWidget,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor

from app.core.config import ShopConfig
from app.core.theme import THEME, _rgba
from app.core.i18n import t
from app.ui.components.responsive_table import make_table_responsive
from app.core.icon_utils import get_colored_icon
from app.repositories.return_repo import ReturnRepository
from app.repositories.item_repo import ItemRepository
from app.services.return_service import ReturnService

_ret_repo = ReturnRepository()
_ret_svc = ReturnService()
_item_repo = ItemRepository()


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


# ── New Return Dialog ─────────────────────────────────────────────────────────

class _ReturnDialog(QDialog):
    """Modal dialog for processing a return."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("ret_dlg_title"))
        self.setMinimumWidth(440)
        THEME.apply(self)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(14)

        hdr = QLabel(t("ret_dlg_title"))
        hdr.setObjectName("dlg_header")
        lay.addWidget(hdr)

        # Item search
        self._search = QLineEdit()
        self._search.setPlaceholderText(t("po_dlg_item_search"))
        self._search.textChanged.connect(self._filter)
        lay.addWidget(self._search)

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
        self._item_table.setMaximumHeight(180)
        lay.addWidget(self._item_table)

        form = QFormLayout()
        form.setSpacing(8)
        self._qty_spin = QSpinBox()
        self._qty_spin.setRange(1, 9999)
        self._qty_spin.setValue(1)
        form.addRow(t("ret_dlg_qty"), self._qty_spin)

        self._reason_edit = QLineEdit()
        self._reason_edit.setPlaceholderText(t("ret_dlg_reason_ph"))
        form.addRow(t("ret_dlg_reason"), self._reason_edit)

        self._action_combo = QComboBox()
        self._action_combo.addItem(t("ret_action_restock"), "RESTOCK")
        self._action_combo.addItem(t("ret_action_writeoff"), "WRITEOFF")
        form.addRow(t("ret_dlg_action"), self._action_combo)

        self._refund_spin = QDoubleSpinBox()
        self._refund_spin.setRange(0, 999999)
        self._refund_spin.setDecimals(2)
        form.addRow(t("ret_dlg_refund"), self._refund_spin)
        lay.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton(t("alert_cancel"))
        cancel_btn.setObjectName("btn_ghost")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        ok_btn = QPushButton(t("ret_btn_new"))
        ok_btn.setObjectName("btn_primary")
        ok_btn.clicked.connect(self._validate)
        btn_row.addWidget(ok_btn)
        lay.addLayout(btn_row)

        self._items_data: list = []
        self._filter("")

    def _filter(self, text: str):
        search = text.strip()
        items = _item_repo.get_all_items(search=search if len(search) >= 2 else "")
        self._items_data = items[:40]
        self._item_table.setRowCount(len(self._items_data))
        for i, item in enumerate(self._items_data):
            self._item_table.setItem(i, 0, QTableWidgetItem(item.display_name))
            self._item_table.setItem(i, 1, QTableWidgetItem(item.barcode or "—"))
            self._item_table.setItem(i, 2, QTableWidgetItem(str(item.stock)))
            self._item_table.setRowHeight(i, 34)

    def _validate(self):
        row = self._item_table.currentRow()
        if row < 0 or row >= len(self._items_data):
            QMessageBox.warning(self, t("ret_dlg_title"), t("ret_warn_select_item"))
            return
        self.accept()

    def get_data(self) -> dict | None:
        row = self._item_table.currentRow()
        if row < 0 or row >= len(self._items_data):
            return None
        return {
            "item_id": self._items_data[row].id,
            "quantity": self._qty_spin.value(),
            "reason": self._reason_edit.text().strip(),
            "action": self._action_combo.currentData(),
            "refund_amount": self._refund_spin.value(),
        }


# ── Empty State ───────────────────────────────────────────────────────────────

class _EmptyState(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(8)
        icon_lbl = QLabel("↩")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 48px;")
        lay.addWidget(icon_lbl)
        self._title = QLabel(t("ret_empty_title"))
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setStyleSheet("font-size: 16px; font-weight: 600;")
        lay.addWidget(self._title)
        self._sub = QLabel(t("ret_empty_sub"))
        self._sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sub.setObjectName("detail_threshold")
        lay.addWidget(self._sub)


# ── Main Page ─────────────────────────────────────────────────────────────────

class ReturnsPage(QWidget):
    """Professional returns management page."""

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
        self._title = QLabel(t("ret_title"))
        self._title.setStyleSheet("font-size: 20px; font-weight: 700;")
        title_col.addWidget(self._title)
        self._subtitle = QLabel(t("ret_subtitle"))
        self._subtitle.setObjectName("admin_panel_subtitle")
        self._subtitle.setStyleSheet("font-size: 12px;")
        title_col.addWidget(self._subtitle)
        hdr_row.addLayout(title_col)
        hdr_row.addStretch()

        self._new_btn = QPushButton(t("ret_btn_new"))
        self._new_btn.setObjectName("btn_primary")
        self._new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._new_btn.clicked.connect(self._create_return)
        hdr_row.addWidget(self._new_btn)
        root.addLayout(hdr_row)

        # ── KPIs ──
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)
        self._kpi_total = _KpiCard()
        self._kpi_restocked = _KpiCard()
        self._kpi_writeoff = _KpiCard()
        self._kpi_refunded = _KpiCard()
        for card in (self._kpi_total, self._kpi_restocked,
                     self._kpi_writeoff, self._kpi_refunded):
            kpi_row.addWidget(card)
        root.addLayout(kpi_row)

        # ── Table / Empty state ──
        self._stack = QStackedWidget()

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels([
            t("ret_col_item"), t("ret_col_qty"), t("ret_col_reason"),
            t("ret_col_action"), t("ret_col_refund"), t("ret_col_date"),
        ])
        hh = self._table.horizontalHeader()
        hh.setMinimumSectionSize(40)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        # Cols: 0=Item  1=Qty  2=Reason  3=Type  4=Refund  5=Date
        make_table_responsive(self._table, [
            (5, 800),   # Date   — hide when viewport < 800 px
            (4, 700),   # Refund — hide when viewport < 700 px
            (3, 580),   # Type   — hide when viewport < 580 px
        ])

        self._empty = _EmptyState()
        self._stack.addWidget(self._table)
        self._stack.addWidget(self._empty)
        root.addWidget(self._stack, 1)

    # ── Data ──────────────────────────────────────────────────────────────────

    def _refresh(self):
        # KPIs
        summary = _ret_repo.get_summary()
        cfg = ShopConfig.get()
        self._kpi_total.set_data(t("ret_kpi_total"), str(summary.get("total", 0) or 0))
        self._kpi_restocked.set_data(t("ret_kpi_restocked"), str(summary.get("restocked", 0) or 0))
        self._kpi_writeoff.set_data(t("ret_kpi_writeoff"), str(summary.get("writeoff", 0) or 0))
        refunded = summary.get("total_refunded", 0) or 0
        self._kpi_refunded.set_data(
            t("ret_kpi_refunded"),
            cfg.format_currency(refunded) if refunded else "—"
        )

        # Table
        returns = _ret_repo.get_all()
        if not returns:
            self._stack.setCurrentIndex(1)
            return
        self._stack.setCurrentIndex(0)

        tk = THEME.tokens
        self._table.setRowCount(len(returns))
        for i, ret in enumerate(returns):
            self._table.setItem(i, 0, QTableWidgetItem(ret.item_name or f"#{ret.item_id}"))

            qty_it = QTableWidgetItem(str(ret.quantity))
            qty_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, 1, qty_it)

            self._table.setItem(i, 2, QTableWidgetItem(ret.reason))

            # Action badge
            is_restock = ret.action == "RESTOCK"
            action_lbl = QLabel(t("ret_action_restock") if is_restock else t("ret_action_writeoff"))
            action_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fg = tk.green if is_restock else tk.orange
            bg = _rgba(fg, "20")
            action_lbl.setStyleSheet(
                f"color:{fg}; background:{bg}; border-radius:8px;"
                "font-weight:700; font-size:9px; padding:3px 8px;"
            )
            self._table.setCellWidget(i, 3, action_lbl)

            # Refund
            refund_str = cfg.format_currency(ret.refund_amount) if ret.refund_amount else "—"
            self._table.setItem(i, 4, QTableWidgetItem(refund_str))

            # Date
            self._table.setItem(i, 5, QTableWidgetItem(ret.created_at[:16] if ret.created_at else ""))
            self._table.setRowHeight(i, 42)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _create_return(self):
        dlg = _ReturnDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if data:
                try:
                    _ret_svc.process_return(**data)
                    self._refresh()
                except ValueError as e:
                    QMessageBox.warning(self, t("ret_dlg_title"), str(e))

    def retranslate(self):
        self._title.setText(t("ret_title"))
        self._subtitle.setText(t("ret_subtitle"))
        self._new_btn.setText(t("ret_btn_new"))
        self._refresh()

    def refresh(self):
        self._refresh()
