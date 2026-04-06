"""
app/ui/components/product_table.py — Inventory product table widget.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QMenu,
    QPushButton, QWidget, QHBoxLayout, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QGuiApplication

from app.core.config import ShopConfig
from app.core.theme import THEME, _rgba
from app.core.i18n import t
from app.models.item import InventoryItem
from app.ui.delegates import (
    AlternatingRowDelegate, ColorDotDelegate, DifferenceDelegate,
    StatusBadgeDelegate,
)
from app.ui.helpers import _sc, _sl
from app.ui.components.responsive_table import make_table_responsive


class ProductTable(QTableWidget):
    """Main inventory table showing all products with color-coded status."""
    row_selected = pyqtSignal(object)
    # Quick inline action signals (item_id)
    quick_in  = pyqtSignal(int)
    quick_out = pyqtSignal(int)
    # Context menu signals
    ctx_stock_in  = pyqtSignal(object)   # InventoryItem
    ctx_stock_out = pyqtSignal(object)
    ctx_adjust    = pyqtSignal(object)
    ctx_edit      = pyqtSignal(object)
    ctx_delete    = pyqtSignal(object)
    ctx_view_txns = pyqtSignal(object)
    # Bulk signals
    ctx_bulk_in     = pyqtSignal(list)   # list[InventoryItem]
    ctx_bulk_out    = pyqtSignal(list)
    ctx_bulk_delete = pyqtSignal(list)
    ctx_bulk_price  = pyqtSignal(list)

    _COL_KEYS = ["col_num", "col_item", "col_color", "col_barcode", "col_price",
                 "col_stock", "col_min", "col_best_bung", "col_status", "col_actions"]
    _WIDTHS    = [40, 200, 50, 100, 70, 60, 50, 80, 80, 90]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(len(self._COL_KEYS))
        self.setHorizontalHeaderLabels([t(k) for k in self._COL_KEYS])
        hh = self.horizontalHeader()
        hh.setMinimumSectionSize(30)
        hh.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.setSelectionBehavior(self.SelectionBehavior.SelectRows)
        self.setSelectionMode(self.SelectionMode.ExtendedSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.setEditTriggers(self.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(False); self.setSortingEnabled(True)
        self.verticalHeader().setVisible(False); self.setShowGrid(False)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setVerticalScrollMode(self.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(self.ScrollMode.ScrollPerPixel)
        self.setItemDelegateForColumn(0, AlternatingRowDelegate(self))
        self.setItemDelegateForColumn(1, AlternatingRowDelegate(self))
        self.setItemDelegateForColumn(2, ColorDotDelegate(self))
        self.setItemDelegateForColumn(3, AlternatingRowDelegate(self))
        self.setItemDelegateForColumn(4, AlternatingRowDelegate(self))
        self.setItemDelegateForColumn(5, AlternatingRowDelegate(self))
        self.setItemDelegateForColumn(6, AlternatingRowDelegate(self))
        self.setItemDelegateForColumn(7, DifferenceDelegate(self))
        self.setItemDelegateForColumn(8, StatusBadgeDelegate(self))
        self._data: list[InventoryItem] = []
        self.itemSelectionChanged.connect(self._emit)
        self._default_widths = self._WIDTHS.copy()

        # ── Responsive column hiding ────────────────────────────────────────
        # Columns: 0=#  1=Item  2=Color  3=Barcode  4=Price  5=Stock
        #          6=Min  7=Diff  8=Status  9=Actions
        # 1=Item, 5=Stock, 8=Status, 9=Actions are always visible.
        make_table_responsive(self, [
            (7, 1100),   # Diff     — hide when viewport < 1100 px
            (6,  950),   # Min      — hide when viewport <  950 px
            (4,  800),   # Price    — hide when viewport <  800 px
            (3,  650),   # Barcode  — hide when viewport <  650 px
            (2,  540),   # Color    — hide when viewport <  540 px
            (0,  440),   # #        — hide when viewport <  440 px
        ])

    def retranslate(self):
        self.setHorizontalHeaderLabels([t(k) for k in self._COL_KEYS])

    def reset_column_widths(self):
        """Reset columns — keep Stretch on name, ResizeToContents on rest."""
        hh = self.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

    def load(self, items: list[InventoryItem]):
        self._data = list(items)

        # Pre-compute shared resources once
        cfg = ShopConfig.get()
        tk = THEME.tokens
        _mono = QFont("JetBrains Mono", 11, QFont.Weight.Bold)
        _mono.setStyleHint(QFont.StyleHint.Monospace)
        _mono_sm = QFont("JetBrains Mono", 10)
        btn_in_ss = (
            f"background:{_rgba(tk.green, '20')}; color:{tk.green};"
            f"border:1px solid {_rgba(tk.green, '40')}; border-radius:5px;"
            "font-weight:700; font-size:11px; padding:0; margin:0;"
        )
        btn_out_ss = (
            f"background:{_rgba(tk.red, '20')}; color:{tk.red};"
            f"border:1px solid {_rgba(tk.red, '40')}; border-radius:5px;"
            "font-weight:700; font-size:11px; padding:0; margin:0;"
        )
        tip_in = t("btn_stock_in")
        tip_out = t("btn_stock_out")

        self.setSortingEnabled(False)
        self.setUpdatesEnabled(False)
        self.blockSignals(True)
        try:
            self.setRowCount(len(self._data))
            for i, item in enumerate(self._data):
                sc  = _sc(item.stock, item.min_stock)
                sl  = _sl(item.stock, item.min_stock)
                sp  = item.sell_price
                price_str = cfg.format_currency(sp) if sp is not None else "—"
                diff = item.stock - item.min_stock
                diff_str = f"Δ{diff:+d}" if item.min_stock > 0 else "—"

                vals = [str(item.id), item.display_name,
                        item.color or "—", item.barcode or "—", price_str,
                        str(item.stock), str(item.min_stock), diff_str, sl, ""]
                for j, v in enumerate(vals):
                    it = QTableWidgetItem(v)
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if j == 3:
                        it.setFont(_mono_sm)
                    elif j == 5:
                        it.setForeground(sc)
                        it.setFont(_mono)
                    elif j == 7:
                        it.setForeground(sc)
                        it.setFont(_mono)
                    self.setItem(i, j, it)

                # Quick action buttons (+1 / -1)
                action_w = QWidget()
                action_lay = QHBoxLayout(action_w)
                action_lay.setContentsMargins(4, 4, 4, 4)
                action_lay.setSpacing(3)

                btn_in = QPushButton("+1")
                btn_in.setToolTip(tip_in)
                btn_in.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_in.setMaximumSize(36, 30)
                btn_in.setStyleSheet(btn_in_ss)
                btn_in.clicked.connect(lambda _, iid=item.id: self.quick_in.emit(iid))
                action_lay.addWidget(btn_in)

                btn_out = QPushButton("-1")
                btn_out.setToolTip(tip_out)
                btn_out.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_out.setMaximumSize(36, 30)
                btn_out.setStyleSheet(btn_out_ss)
                btn_out.clicked.connect(lambda _, iid=item.id: self.quick_out.emit(iid))
                action_lay.addWidget(btn_out)

                self.setCellWidget(i, 9, action_w)
                self.setRowHeight(i, 48)
        finally:
            self.blockSignals(False)
            self.setUpdatesEnabled(True)
        self.setSortingEnabled(True)

    def _emit(self):
        r = self.currentRow()
        if r < 0: self.row_selected.emit(None); return
        it = self.item(r, 0)
        if it:
            pid = int(it.text())
            for item in self._data:
                if item.id == pid: self.row_selected.emit(item); return
        self.row_selected.emit(None)

    def update_row_by_id(self, item: InventoryItem) -> bool:
        """Lightweight update of a single row without rebuilding the entire table.
        Returns True if the row was found and updated."""
        cfg = ShopConfig.get()
        tk = THEME.tokens
        _mono = QFont("JetBrains Mono", 11, QFont.Weight.Bold)
        _mono.setStyleHint(QFont.StyleHint.Monospace)
        _mono_sm = QFont("JetBrains Mono", 10)

        for r in range(self.rowCount()):
            it = self.item(r, 0)
            if it and int(it.text()) == item.id:
                # Update the data list too
                for idx, d in enumerate(self._data):
                    if d.id == item.id:
                        self._data[idx] = item
                        break

                sc = _sc(item.stock, item.min_stock)
                sl = _sl(item.stock, item.min_stock)
                sp = item.sell_price
                price_str = cfg.format_currency(sp) if sp is not None else "—"
                diff = item.stock - item.min_stock
                diff_str = f"Δ{diff:+d}" if item.min_stock > 0 else "—"

                vals = [str(item.id), item.display_name,
                        item.color or "—", item.barcode or "—", price_str,
                        str(item.stock), str(item.min_stock), diff_str, sl, ""]
                for j, v in enumerate(vals):
                    cell = self.item(r, j)
                    if cell:
                        cell.setText(v)
                        if j == 5:
                            cell.setForeground(sc)
                            cell.setFont(_mono)
                        elif j == 7:
                            cell.setForeground(sc)
                            cell.setFont(_mono)
                return True
        return False

    def select_by_id(self, pid: int):
        for r in range(self.rowCount()):
            it = self.item(r, 0)
            if it and int(it.text()) == pid:
                self.selectRow(r); self.scrollToItem(it); return

    def get_selected_items(self) -> list[InventoryItem]:
        """Return all currently selected InventoryItem objects."""
        rows = sorted({idx.row() for idx in self.selectedIndexes()})
        result: list[InventoryItem] = []
        for r in rows:
            it = self.item(r, 0)
            if it:
                pid = int(it.text())
                for item in self._data:
                    if item.id == pid:
                        result.append(item)
                        break
        return result

    def _show_context_menu(self, pos) -> None:
        row = self.rowAt(pos.y())
        if row < 0:
            return
        selected = self.get_selected_items()
        multi = len(selected) > 1

        menu = QMenu(self)

        if multi:
            # Bulk operations
            n = len(selected)
            act_bulk_in  = menu.addAction(t("ctx_bulk_in"))
            act_bulk_out = menu.addAction(t("ctx_bulk_out"))
            menu.addSeparator()
            act_bulk_price = menu.addAction(t("ctx_bulk_price"))
            menu.addSeparator()
            act_bulk_del = menu.addAction(t("ctx_bulk_delete", n=n))
            menu.addSeparator()
            act_sel_all  = menu.addAction(t("ctx_select_all"))

            action = menu.exec(self.viewport().mapToGlobal(pos))
            if action == act_bulk_in:
                self.ctx_bulk_in.emit(selected)
            elif action == act_bulk_out:
                self.ctx_bulk_out.emit(selected)
            elif action == act_bulk_price:
                self.ctx_bulk_price.emit(selected)
            elif action == act_bulk_del:
                self.ctx_bulk_delete.emit(selected)
            elif action == act_sel_all:
                self.selectAll()
        else:
            # Single item — find it
            it = self.item(row, 0)
            if not it:
                return
            pid = int(it.text())
            item = None
            for i in self._data:
                if i.id == pid:
                    item = i
                    break
            if not item:
                return

            act_in   = menu.addAction(f'{t("ctx_stock_in")}\tCtrl+I')
            act_out  = menu.addAction(f'{t("ctx_stock_out")}\tCtrl+O')
            act_adj  = menu.addAction(f'{t("ctx_adjust")}\tCtrl+J')
            menu.addSeparator()
            act_edit = menu.addAction(t("ctx_edit"))
            act_del  = menu.addAction(t("ctx_delete"))
            menu.addSeparator()
            act_txns = menu.addAction(t("ctx_view_txns"))
            menu.addSeparator()
            act_cp_name = menu.addAction(t("ctx_copy_name"))
            act_cp_bc   = None
            if item.barcode:
                act_cp_bc = menu.addAction(t("ctx_copy_barcode"))

            action = menu.exec(self.viewport().mapToGlobal(pos))
            if action == act_in:
                self.ctx_stock_in.emit(item)
            elif action == act_out:
                self.ctx_stock_out.emit(item)
            elif action == act_adj:
                self.ctx_adjust.emit(item)
            elif action == act_edit:
                self.ctx_edit.emit(item)
            elif action == act_del:
                self.ctx_delete.emit(item)
            elif action == act_txns:
                self.ctx_view_txns.emit(item)
            elif action == act_cp_name:
                QGuiApplication.clipboard().setText(item.display_name)
            elif act_cp_bc and action == act_cp_bc:
                QGuiApplication.clipboard().setText(item.barcode)
