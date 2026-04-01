"""
app/ui/components/matrix_widget.py — Generic phone-model × part-type matrix table.

Excel-like color banding:
  - Model name column: strong distinct background (stands out from data)
  - Each part type group (4 columns) gets its OWN color band
  - All 4 fields within a part type share the same background
  - Different part types have visually different backgrounds
  - Header row: bold colored banners per part type
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QAbstractItemView, QMessageBox, QFrame,
    QStyledItemDelegate, QStyleOptionViewItem, QMenu,
)
from PyQt6.QtCore import Qt, QModelIndex, QPoint
from PyQt6.QtGui import QColor, QFont, QPainter

from app.core.theme import THEME
from app.models.category import CategoryConfig
from app.models.item import InventoryItem
from app.repositories.item_repo import ItemRepository
from app.services.stock_service import StockService
from app.ui.dialogs.matrix_dialogs import StockOpDialog, ThresholdDialog, InventurDialog
from app.core.i18n import t

_item_repo  = ItemRepository()
_stock_svc  = StockService()

_COLS_PER_TYPE = 4   # Min-Stock | Best-Bung | Stock | Order
_COL_W = {"model": 150, "stamm": 80, "bestbung": 80, "stock": 70, "inventur": 80}
_HEADER_ROW = 0

# Fonts
_FONT_MONO   = QFont("JetBrains Mono", 11, QFont.Weight.Bold)
_FONT_MONO.setStyleHint(QFont.StyleHint.Monospace)
_FONT_MODEL  = QFont("Segoe UI", 11, QFont.Weight.DemiBold)
_FONT_HEADER = QFont("Segoe UI", 10, QFont.Weight.Bold)
_FONT_DATA   = QFont("Segoe UI", 10)


class _MatrixCellDelegate(QStyledItemDelegate):
    """Delegate that paints the cell background from BackgroundRole.

    QSS `QTableWidget::item { background }` overrides programmatic
    setBackground(). This delegate bypasses QSS by painting the
    background directly, then drawing text with the item's foreground and font.
    """

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        from PyQt6.QtWidgets import QStyle
        from PyQt6.QtGui import QBrush

        painter.save()
        rect = option.rect

        # 1) Paint cell background from the item's BackgroundRole
        bg = index.data(Qt.ItemDataRole.BackgroundRole)
        if isinstance(bg, QBrush):
            painter.fillRect(rect, bg)
        elif isinstance(bg, QColor):
            painter.fillRect(rect, bg)

        # 2) Selection highlight
        if option.state & QStyle.StateFlag.State_Selected:
            sel = QColor(THEME.tokens.blue)
            sel.setAlpha(100)
            painter.fillRect(rect, sel)

        # 3) Text
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        fg = index.data(Qt.ItemDataRole.ForegroundRole)
        if isinstance(fg, QBrush):
            painter.setPen(fg.color())
        elif isinstance(fg, QColor):
            painter.setPen(fg)
        else:
            painter.setPen(QColor(THEME.tokens.t1))

        font = index.data(Qt.ItemDataRole.FontRole)
        if isinstance(font, QFont):
            painter.setFont(font)

        alignment = index.data(Qt.ItemDataRole.TextAlignmentRole)
        if alignment is None:
            alignment = int(Qt.AlignmentFlag.AlignCenter)
        painter.drawText(rect.adjusted(6, 0, -6, 0), int(alignment), text)

        painter.restore()


def _base(ti: int) -> int:
    return 1 + ti * _COLS_PER_TYPE


def _part_type_bg(accent_hex: str, is_dark: bool) -> QColor:
    """Visible background tint for a part-type column group.

    Blends the part type's accent color into the base background
    at a strength that's clearly visible but still readable.
    """
    c = QColor(accent_hex)
    if is_dark:
        # Blend accent into #0F0F0F base at 15%
        r = int(0.15 * c.red()   + 0.85 * 15)
        g = int(0.15 * c.green() + 0.85 * 15)
        b = int(0.15 * c.blue()  + 0.85 * 15)
        return QColor(r, g, b)
    else:
        # Blend accent into #FFFFFF base at 12%
        r = int(0.12 * c.red()   + 0.88 * 255)
        g = int(0.12 * c.green() + 0.88 * 255)
        b = int(0.12 * c.blue()  + 0.88 * 255)
        return QColor(r, g, b)


def _model_col_bg(is_dark: bool) -> QColor:
    """Strong distinct background for the model name column."""
    if is_dark:
        return QColor(30, 33, 54)     # blue-slate
    else:
        return QColor(55, 65, 81)     # dark slate-gray (dark enough for white text)


class MatrixWidget(QTableWidget):
    """
    Matrix table: phone models (rows) × part types (column groups).

    Color banding (Excel-like):
    ┌──────────┬──────────────────┬──────────────────┬────────────────┐
    │  MODEL   │   Part Type A    │   Part Type B    │  Part Type C   │
    │ (slate)  │   (red tint)     │  (blue tint)     │ (green tint)   │
    ├──────────┼────┬────┬───┬────┼────┬────┬───┬────┼────┬───┬───┬───┤
    │ iPhone15 │ MS │ BB │ S │ O  │ MS │ BB │ S │ O  │ MS │BB │ S │ O │
    │ iPhone14 │ MS │ BB │ S │ O  │ MS │ BB │ S │ O  │ MS │BB │ S │ O │
    └──────────┴────┴────┴───┴────┴────┴────┴───┴────┴────┴───┴───┴───┘
    """

    def __init__(self, refresh_cb, parent=None):
        super().__init__(parent)
        self.setObjectName("matrix_table")
        self._refresh_cb = refresh_cb
        self._cat: CategoryConfig | None = None
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(False)
        self.setShowGrid(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.cellDoubleClicked.connect(self._on_dbl)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

    def load(self, cat: CategoryConfig, models,
             item_map: dict[tuple[int, str], InventoryItem]) -> None:
        self._cat = cat
        self._build_headers(cat)
        tk = THEME.tokens
        is_dark = THEME.is_dark
        self.clearContents()
        self.setRowCount(1 + len(models))
        self.setRowHeight(_HEADER_ROW, 36)

        model_bg = _model_col_bg(is_dark)

        # Pre-compute background colors for each part type group
        type_bgs = [_part_type_bg(pt.accent_color, is_dark) for pt in cat.part_types]

        # Row 0 — colour-coded group-name banner
        corner = self._ro("")
        corner.setBackground(model_bg)
        self.setItem(_HEADER_ROW, 0, corner)
        for ti, pt in enumerate(cat.part_types):
            b = _base(ti)
            self.setSpan(_HEADER_ROW, b, 1, _COLS_PER_TYPE)
            it = self._ro(pt.name)
            it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # Header banner: stronger version of the column tint
            hdr_bg = QColor(pt.accent_color)
            if is_dark:
                it.setBackground(QColor(
                    int(0.30 * hdr_bg.red()   + 0.70 * 15),
                    int(0.30 * hdr_bg.green() + 0.70 * 15),
                    int(0.30 * hdr_bg.blue()  + 0.70 * 15),
                ))
            else:
                it.setBackground(QColor(
                    int(0.25 * hdr_bg.red()   + 0.75 * 255),
                    int(0.25 * hdr_bg.green() + 0.75 * 255),
                    int(0.25 * hdr_bg.blue()  + 0.75 * 255),
                ))
            it.setForeground(QColor(pt.accent_color))
            it.setFont(_FONT_HEADER)
            self.setItem(_HEADER_ROW, b, it)

        # Model rows
        for ri, model in enumerate(models):
            r = ri + 1
            self.setRowHeight(r, 48)

            # Model name cell — strong distinct background, always white text
            name_it = self._ro(f"  {model.name}")
            name_it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            name_it.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            name_it.setFont(_FONT_MODEL)
            name_it.setForeground(QColor("#FFFFFF"))
            name_it.setBackground(model_bg)
            self.setItem(r, 0, name_it)

            for ti, pt in enumerate(cat.part_types):
                b    = _base(ti)
                item = item_map.get((model.id, pt.key))
                bg   = type_bgs[ti]

                if not item:
                    for c in range(_COLS_PER_TYPE):
                        cell = self._ro("—")
                        cell.setBackground(bg)
                        cell.setForeground(QColor(tk.t4))
                        self.setItem(r, b + c, cell)
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
                st.setFont(_FONT_DATA)
                st.setBackground(bg)
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
                bb.setFont(_FONT_MONO)
                bb.setBackground(bg)
                bb.setToolTip(bb_tip)
                self.setItem(r, b + 1, bb)

                # Stock — monospace, bold, color-coded
                stk = self._cell(str(stock), meta | {"field": "stock"})
                if stock == 0:
                    stk.setForeground(QColor(tk.red))
                elif item.is_low:
                    stk.setForeground(QColor(tk.yellow))
                else:
                    stk.setForeground(QColor(tk.green))
                stk.setFont(_FONT_MONO)
                stk.setBackground(bg)
                stk.setToolTip(t("disp_tip_stock"))
                self.setItem(r, b + 2, stk)

                # Order (was Inventur)
                inv_txt = str(inventur) if inventur is not None else "—"
                inv = self._cell(inv_txt, meta | {"field": "inventur"})
                inv.setForeground(QColor(tk.t3))
                inv.setFont(_FONT_DATA)
                inv.setBackground(bg)
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
        # Apply cell delegate to every column so backgrounds render
        delegate = _MatrixCellDelegate(self)
        for col in range(total):
            self.setItemDelegateForColumn(col, delegate)
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

    # ── Right-click context menu ─────────────────────────────────────────────

    def _on_context_menu(self, pos: QPoint) -> None:
        item = self.itemAt(pos)
        if not item:
            return
        meta = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(meta, dict) or "item_id" not in meta:
            return

        item_id    = meta["item_id"]
        model_name = meta["model_name"]
        dtype_lbl  = meta["dtype_lbl"]

        menu = QMenu(self)
        _id = item_id
        _mn = model_name
        _dl = dtype_lbl
        _ms = meta["min_stock"]
        _st = meta["stock"]

        act_stock = menu.addAction(f"📦  Stock IN/OUT…")
        act_stock.triggered.connect(lambda _=False, i=_id, d=_dl: self._ctx_stock(i, d))

        act_min = menu.addAction(f"📊  Set Min Stock…")
        act_min.triggered.connect(lambda _=False, i=_id, m=_mn, d=_dl, v=_ms: self._ctx_threshold(i, m, d, v))

        act_order = menu.addAction(f"📋  Set Order…")
        act_order.triggered.connect(lambda _=False, i=_id, m=_mn, d=_dl, s=_st: self._ctx_order(i, m, d, s))

        menu.addSeparator()

        act_bc = menu.addAction(f"🏷  {t('barcode_ctx_assign')}")
        act_bc.triggered.connect(lambda _=False, i=_id, n=f"{_mn} · {_dl}": self._ctx_barcode(i, n))

        menu.exec(self.viewport().mapToGlobal(pos))

    def _ctx_stock(self, item_id: int, dtype_lbl: str) -> None:
        item = _item_repo.get_by_id(item_id)
        if not item:
            return
        dlg = StockOpDialog(item, dtype_lbl, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            op, qty = dlg.result_data()
            try:
                if op == "IN":    _stock_svc.stock_in(item_id, qty)
                elif op == "OUT": _stock_svc.stock_out(item_id, qty)
                else:             _stock_svc.stock_adjust(item_id, qty)
                self._refresh_cb()
            except ValueError as exc:
                QMessageBox.warning(self, t("disp_stock_err"), str(exc))

    def _ctx_threshold(self, item_id: int, model_name: str, dtype_lbl: str, current: int) -> None:
        dlg = ThresholdDialog(model_name, dtype_lbl, current, self, item_id=item_id)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            _item_repo.update_min_stock(item_id, dlg.value())
            self._refresh_cb()

    def _ctx_order(self, item_id: int, model_name: str, dtype_lbl: str, stock: int) -> None:
        dlg = InventurDialog(model_name, dtype_lbl, stock, self, item_id=item_id)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            _item_repo.update_inventur(item_id, dlg.value())
            self._refresh_cb()

    def _ctx_barcode(self, item_id: int, item_name: str) -> None:
        try:
            from app.ui.dialogs.barcode_assign_dialog import BarcodeAssignDialog
            item = _item_repo.get_by_id(item_id)
            bc = item.barcode if item else None
            dlg = BarcodeAssignDialog(item_id, item_name, bc, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self._refresh_cb()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

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
            dlg = ThresholdDialog(model_name, dtype_lbl, min_stock, self, item_id=item_id)
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
            dlg = InventurDialog(model_name, dtype_lbl, stock, self, item_id=item_id)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                _item_repo.update_inventur(item_id, dlg.value())
                self._refresh_cb()
