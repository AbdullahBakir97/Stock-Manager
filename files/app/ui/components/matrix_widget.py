"""
app/ui/components/matrix_widget.py — Generic phone-model × part-type matrix table.

Used by MatrixTab for every inventory category (Displays, Batteries, Cases, …).
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QAbstractItemView, QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

from app.core.theme import THEME
from app.models.category import CategoryConfig
from app.models.item import InventoryItem
from app.repositories.item_repo import ItemRepository
from app.services.stock_service import StockService
from app.ui.dialogs.matrix_dialogs import StockOpDialog, ThresholdDialog, InventurDialog
from app.core.theme import THEME, qc
from app.core.i18n import t

_item_repo  = ItemRepository()
_stock_svc  = StockService()

_COLS_PER_TYPE = 4   # Min-Stock | Best-Bung | Stock | Inventur
_COL_W = {"model": 140, "stamm": 82, "bestbung": 82, "stock": 72, "inventur": 82}
_HEADER_ROW = 0


def _base(ti: int) -> int:
    return 1 + ti * _COLS_PER_TYPE


class MatrixWidget(QTableWidget):
    """
    Generic matrix table: phone models (rows) × part types (column groups, 4 cols each).
    Driven by CategoryConfig loaded from DB — works for any category without code changes.
    """

    def __init__(self, refresh_cb, parent=None):
        super().__init__(parent)
        self._refresh_cb = refresh_cb
        self._cat: CategoryConfig | None = None
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True); self.setShowGrid(True)  # Enable alternating colors like Excel
        self.cellDoubleClicked.connect(self._on_dbl)

    def load(self, cat: CategoryConfig, models,
             item_map: dict[tuple[int, str], InventoryItem]) -> None:
        """
        cat      — CategoryConfig with part_types list
        models   — list[PhoneModel]
        item_map — {(model_id, part_type_key): InventoryItem}
        """
        self._cat = cat
        self._build_headers(cat)
        tk = THEME.tokens
        self.clearContents()
        self.setRowCount(1 + len(models))
        self.setRowHeight(_HEADER_ROW, 30)

        # Row 0 — colour-coded group-name banner
        corner = self._ro("")
        corner.setBackground(QColor(tk.card2))
        self.setItem(_HEADER_ROW, 0, corner)
        for ti, pt in enumerate(cat.part_types):
            b = _base(ti)
            self.setSpan(_HEADER_ROW, b, 1, _COLS_PER_TYPE)
            it = self._ro(pt.name)
            it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it.setBackground(qc(pt.accent_color, 0x35))
            it.setForeground(QColor(pt.accent_color))
            it.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.setItem(_HEADER_ROW, b, it)

        # Model rows
        for ri, model in enumerate(models):
            r = ri + 1
            self.setRowHeight(r, 40)
            name_it = self._ro(f"  {model.name}")
            name_it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            name_it.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            name_it.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            name_it.setForeground(QColor(tk.t1))
            self.setItem(r, 0, name_it)

            for ti, pt in enumerate(cat.part_types):
                b    = _base(ti)
                item = item_map.get((model.id, pt.key))
                if not item:
                    for c in range(_COLS_PER_TYPE):
                        self.setItem(r, b + c, self._ro("—"))
                    continue

                min_stock = item.min_stock
                stock     = item.stock
                inventur  = item.inventur
                best      = item.best_bung

                meta = {
                    "item_id":    item.id,
                    "model_name": model.name,
                    "dtype_lbl":  pt.name,
                    "min_stock":  min_stock,
                    "stock":      stock,
                }

                # Min-Stock (Stamm-Zahl)
                st = self._cell(str(min_stock), meta | {"field": "stamm_zahl"})
                st.setForeground(QColor(tk.t2))
                st.setToolTip(t("disp_tip_stamm"))
                self.setItem(r, b, st)

                # Best-Bung
                if best == 0:
                    bb_txt, bb_col, bb_tip = "0",        tk.yellow, t("disp_tip_bb_zero")
                elif best < 0:
                    bb_txt = str(best)
                    bb_col = tk.red
                    bb_tip = t("disp_tip_bb_neg", n=abs(best))
                else:
                    bb_txt = f"+{best}"
                    bb_col = tk.green
                    bb_tip = t("disp_tip_bb_pos", n=best)
                bb = self._cell(bb_txt, meta | {"field": "best_bung"})
                bb.setForeground(QColor(bb_col))
                bb.setToolTip(bb_tip)
                self.setItem(r, b + 1, bb)

                # Stock
                stk = self._cell(str(stock), meta | {"field": "stock"})
                if stock == 0:
                    stk.setForeground(QColor(tk.red))
                elif item.is_low:
                    stk.setForeground(QColor(tk.yellow))
                else:
                    stk.setForeground(QColor(tk.green))
                stk.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                stk.setToolTip(t("disp_tip_stock"))
                self.setItem(r, b + 2, stk)

                # Inventur
                inv_txt = str(inventur) if inventur is not None else "—"
                inv = self._cell(inv_txt, meta | {"field": "inventur"})
                inv.setForeground(QColor(tk.t3))
                inv.setToolTip(t("disp_tip_inv"))
                self.setItem(r, b + 3, inv)

    def retranslate(self) -> None:
        if not self._cat:
            return
        labels = [t("disp_col_model")]
        for _ in self._cat.part_types:
            labels += [t("col_stamm_zahl"), t("col_best_bung"),
                       t("disp_col_stock"), t("col_inventur")]
        self.setHorizontalHeaderLabels(labels)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _build_headers(self, cat: CategoryConfig) -> None:
        n_types = len(cat.part_types)
        total   = 1 + n_types * _COLS_PER_TYPE
        self.setColumnCount(total)
        labels  = [t("disp_col_model")]
        for _ in cat.part_types:
            labels += [t("col_stamm_zahl"), t("col_best_bung"),
                       t("disp_col_stock"), t("col_inventur")]
        self.setHorizontalHeaderLabels(labels)
        hh = self.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.setColumnWidth(0, _COL_W["model"])
        for i in range(n_types):
            b = _base(i)
            self.setColumnWidth(b,     _COL_W["stamm"])
            self.setColumnWidth(b + 1, _COL_W["bestbung"])
            self.setColumnWidth(b + 2, _COL_W["stock"])
            self.setColumnWidth(b + 3, _COL_W["inventur"])
            # Set alternating row delegate for all data cells
            for col in range(4):
                self.setItemDelegateForColumn(col, MatrixAlternatingRowDelegate(self))
        self.setColumnWidth(0, _COL_W["model"])
        for i in range(n_types):
            b = _base(i)
            self.setColumnWidth(b,     _COL_W["stamm"])
            self.setColumnWidth(b + 1, _COL_W["bestbung"])
            self.setColumnWidth(b + 2, _COL_W["stock"])
            self.setColumnWidth(b + 3, _COL_W["inventur"])

    @staticmethod
    def _ro(text: str) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        it.setFlags(Qt.ItemFlag.ItemIsEnabled)
        it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return it

    @staticmethod
    def _cell(text: str, meta: dict) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        it.setData(Qt.ItemDataRole.UserRole, meta)
        return it

    # ── Double-click handler ───────────────────────────────────────────────────

    def _on_dbl(self, row: int, col: int) -> None:
        if row == _HEADER_ROW or col == 0:
            return
        it = self.item(row, col)
        if not it:
            return
        meta = it.data(Qt.ItemDataRole.UserRole)
        if not isinstance(meta, dict):
            return

        field      = meta.get("field")
        item_id    = meta["item_id"]
        model_name = meta["model_name"]
        dtype_lbl  = meta["dtype_lbl"]
        min_stock  = meta["min_stock"]
        stock      = meta["stock"]

        if field == "stamm_zahl":
            dlg = ThresholdDialog(model_name, dtype_lbl, min_stock, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                _item_repo.update_min_stock(item_id, dlg.value())
                self._refresh_cb()

        elif field == "stock":
            item = _item_repo.get_by_id(item_id)
            if not item:
                return
            dlg = StockOpDialog(item, dtype_lbl, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                op, qty = dlg.result_data()
                try:
                    if op == "IN":
                        _stock_svc.stock_in(item_id, qty)
                    elif op == "OUT":
                        _stock_svc.stock_out(item_id, qty)
                    else:
                        _stock_svc.stock_adjust(item_id, qty)
                    self._refresh_cb()
                except ValueError as exc:
                    QMessageBox.warning(self, t("disp_stock_err"), str(exc))

        elif field == "inventur":
            dlg = InventurDialog(model_name, dtype_lbl, stock, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                _item_repo.update_inventur(item_id, dlg.value())
                self._refresh_cb()
