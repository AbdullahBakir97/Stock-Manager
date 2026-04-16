"""
app/ui/components/matrix_widget.py — Generic phone-model × part-type matrix table.

Excel-like color banding:
  - Model name column: strong distinct background (stands out from data)
  - Each part type group (4 columns) gets its OWN color band
  - All 4 fields within a part type share the same background
  - Different part types have visually different backgrounds
  - Header row: bold colored banners per part type

Sticky scrolling:
  - FrozenMatrixContainer wraps a model-column table (left, no h-scroll)
    and the data table (right, h+v scroll), both sharing vertical scroll.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QAbstractItemView, QMessageBox, QFrame,
    QStyledItemDelegate, QStyleOptionViewItem, QMenu,
    QWidget, QVBoxLayout, QHBoxLayout,
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
_COL_W = {"model": 160, "stamm": 108, "bestbung": 104, "stock": 84, "inventur": 112}
_HEADER_ROW = 0

# Fonts
_FONT_MONO   = QFont("JetBrains Mono", 11, QFont.Weight.Bold)
_FONT_MONO.setStyleHint(QFont.StyleHint.Monospace)
_FONT_MODEL  = QFont("Segoe UI", 11, QFont.Weight.DemiBold)
_FONT_HEADER = QFont("Segoe UI", 10, QFont.Weight.Bold)
_FONT_DATA   = QFont("Segoe UI", 10)
_FONT_COLOR  = QFont("Segoe UI", 9)


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

        # 2a) Row-wide hover highlight (before selection so selection wins)
        widget = option.widget
        if widget is not None:
            hover_row = getattr(widget, "_hover_row", -1)
            if hover_row >= 0 and index.row() == hover_row:
                hov = QColor(THEME.tokens.t1)
                hov.setAlpha(28)  # subtle — just enough to trace the row
                painter.fillRect(rect, hov)

        # 2b) Selection highlight
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


import re as _re

def _model_series(name: str) -> str:
    """Extract the series prefix from a model name for grouping.

    Examples:
        "X"           → "X"
        "XS"          → "X"
        "XS max"      → "X"
        "XR"          → "X"
        "11"          → "11"
        "11 Pro"      → "11"
        "11 Pro max"  → "11"
        "12 / 12 Pro" → "12"
        "12 mini"     → "12"
        "Galaxy A04"  → "A0"
        "Galaxy S22"  → "S2"
        "Galaxy S23 Ultra" → "S2"
    """
    # Strip common brand prefixes
    n = name.strip()
    for prefix in ("Galaxy ", "iPhone ", "Pixel "):
        if n.startswith(prefix):
            n = n[len(prefix):]

    # Leading number → series is that number: "11 Pro max" → "11"
    m = _re.match(r'^(\d+)', n)
    if m:
        return m.group(1)
    # Letter + digits: group by letter + tens digit
    # "A04" → "A0", "A05s" → "A0", "A11" → "A1", "A22" → "A2"
    # "S22" → "S2", "S23" → "S2", "S24" → "S2"
    m = _re.match(r'^([A-Za-z])(\d)', n)
    if m:
        return (m.group(1) + m.group(2)).upper()
    # Pure letter names: "X", "XS", "XR" → first char "X"
    m = _re.match(r'^([A-Za-z])', n)
    if m:
        return m.group(1).upper()
    return n[0].upper() if n else ""


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
        # Blend accent into #F5F5F5 base at 28% — strong enough to be visible on white
        r = int(0.28 * c.red()   + 0.72 * 245)
        g = int(0.28 * c.green() + 0.72 * 245)
        b = int(0.28 * c.blue()  + 0.72 * 245)
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

    def __init__(self, refresh_cb, parent=None, skip_banner_row=False):
        super().__init__(parent)
        self.setObjectName("matrix_table")
        self._refresh_cb = refresh_cb
        self._cat: CategoryConfig | None = None
        self._skip_banner = skip_banner_row
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        # Whole-row selection for easier reading across wide matrices
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setMinimumSectionSize(1)
        self.setAlternatingRowColors(False)
        self.setShowGrid(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        # Row-wide hover highlight
        self.setMouseTracking(True)
        self._hover_row = -1
        self.cellDoubleClicked.connect(self._on_dbl)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

    # ── Row-wide hover / selection visual feedback ────────────────────────────
    def mouseMoveEvent(self, event):
        """Track hovered row; emit a signal so the frozen model column syncs."""
        idx = self.indexAt(event.pos())
        row = idx.row() if idx.isValid() else -1
        if row != self._hover_row:
            self._hover_row = row
            # Repaint only the affected rows (old + new)
            self.viewport().update()
            # Notify container to highlight the frozen model-table row too
            parent = self.parent()
            if parent is not None and hasattr(parent, "_on_data_hover_row"):
                parent._on_data_hover_row(row)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self._hover_row != -1:
            self._hover_row = -1
            self.viewport().update()
            parent = self.parent()
            if parent is not None and hasattr(parent, "_on_data_hover_row"):
                parent._on_data_hover_row(-1)
        super().leaveEvent(event)

    def load(self, cat: CategoryConfig, models,
             item_map: dict[tuple[int, str], InventoryItem],
             brand_boundaries: list[tuple[int, str]] | None = None) -> None:
        self._cat = cat
        self._build_headers(cat)
        tk = THEME.tokens
        is_dark = THEME.is_dark
        self.clearContents()

        model_bg = _model_col_bg(is_dark)

        # Pre-compute default background colors for each part type group
        type_bgs = [_part_type_bg(pt.accent_color, is_dark) for pt in cat.part_types]

        # Row offset: 0 if no banner row, 1 if banner row exists
        if self._skip_banner:
            self._row_offset = 0
            self.setRowCount(len(models))
        else:
            self._row_offset = 1
            self.setRowCount(1 + len(models))
            self.setRowHeight(_HEADER_ROW, 36)

            # Row 0 — colour-coded group-name banner
            corner = self._ro("")
            corner.setBackground(model_bg)
            self.setItem(_HEADER_ROW, 0, corner)
            for ti, pt in enumerate(cat.part_types):
                b = _base(ti)
                self.setSpan(_HEADER_ROW, b, 1, _COLS_PER_TYPE)
                it = self._ro(pt.name)
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
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

        # Pre-index item_map by model_id for O(1) lookup (was O(n*m) nested loop)
        _items_by_model: dict[int, list[tuple[str, str]]] = {}
        for (mid, pt_key, color) in item_map.keys():
            _items_by_model.setdefault(mid, []).append((pt_key, color))

        # Build brand boundary set for quick lookup
        _brand_at: dict[int, str] = {}
        if brand_boundaries:
            for idx, bname in brand_boundaries:
                _brand_at[idx] = bname

        # Build row list: brand headers + model rows + color sub-rows + separators
        row_data: list[dict] = []
        prev_series = ""
        for mi, model in enumerate(models):
            # Insert brand header row if this is a brand boundary
            if mi in _brand_at:
                prev_series = ""  # reset series tracking for new brand
                row_data.append({"type": "brand", "brand_name": _brand_at[mi]})

            series = _model_series(model.name)
            if prev_series and series != prev_series:
                row_data.append({"type": "sep"})
            prev_series = series

            # O(k) lookup where k = items for this model only
            model_colors: dict[str, list[str]] = {}
            for pt_key, color in _items_by_model.get(model.id, []):
                if color:
                    model_colors.setdefault(pt_key, []).append(color)

            row_data.append({"type": "model", "model": model, "colors": model_colors})

            # Add color sub-rows if any part type has colors
            if model_colors:
                all_colors = sorted(set(c for colors in model_colors.values() for c in colors))
                for color in all_colors:
                    row_data.append({"type": "color", "model": model, "color": color})

        self.setUpdatesEnabled(False)
        self.setRowCount(self._row_offset + len(row_data))

        # Separator row color
        sep_bg = QColor(tk.t3)

        # Brand header colors
        brand_bg = QColor(tk.card2)
        brand_fg = QColor(tk.t1)
        _FONT_BRAND = QFont("Segoe UI", 12, QFont.Weight.Bold)

        for ri, rd in enumerate(row_data):
            r = ri + self._row_offset

            if rd["type"] == "brand":
                # Brand header row — full-width colored bar
                self.setRowHeight(r, 32)
                bname = rd["brand_name"]
                for c in range(self.columnCount()):
                    cell = self._ro("")
                    cell.setBackground(brand_bg)
                    if c == 0:
                        cell = self._ro(f"  {bname}")
                        cell.setTextAlignment(
                            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                        )
                        cell.setFont(_FONT_BRAND)
                        cell.setForeground(QColor(tk.green))
                        cell.setBackground(brand_bg)
                    self.setItem(r, c, cell)
                continue

            if rd["type"] == "sep":
                # Visible separator line between model series
                self.setRowHeight(r, 3)
                for c in range(self.columnCount()):
                    cell = self._ro("")
                    cell.setBackground(sep_bg)
                    self.setItem(r, c, cell)
                continue

            model = rd["model"]

            if rd["type"] == "model":
                self.setRowHeight(r, 48)
                # Model name cell
                name_it = self._ro(f"  {model.name}")
                name_it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                name_it.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                name_it.setFont(_FONT_MODEL)
                name_it.setForeground(QColor("#FFFFFF"))
                name_it.setBackground(model_bg)
                self.setItem(r, 0, name_it)

                for ti, pt in enumerate(cat.part_types):
                    b  = _base(ti)
                    bg = type_bgs[ti]

                    # For colored part types, show aggregate; for colorless, show direct
                    has_colors = pt.key in rd.get("colors", {})
                    if has_colors:
                        # Aggregate: sum stock/min_stock across all colors
                        colors = rd["colors"][pt.key]
                        total_stock = 0
                        total_min = 0
                        total_inv = 0
                        any_item = None
                        for color in colors:
                            item = item_map.get((model.id, pt.key, color))
                            if item:
                                total_stock += item.stock
                                total_min += item.min_stock
                                total_inv += (item.inventur or 0)
                                any_item = item

                        if not any_item:
                            for c in range(_COLS_PER_TYPE):
                                cell = self._ro("—")
                                cell.setBackground(bg)
                                self.setItem(r, b + c, cell)
                            continue

                        best = total_stock - total_min
                        meta = {
                            "item_id": any_item.id,
                            "model_id": model.id,
                            "part_type_id": pt.id,
                            "model_name": model.name,
                            "dtype_lbl": pt.name,
                            "min_stock": total_min,
                            "stock": total_stock,
                        }
                    else:
                        # Colorless item — direct lookup
                        item = item_map.get((model.id, pt.key, ""))
                        if not item:
                            for c in range(_COLS_PER_TYPE):
                                cell = self._ro("—")
                                cell.setBackground(bg)
                                cell.setForeground(QColor(tk.t4))
                                self.setItem(r, b + c, cell)
                            continue

                        total_min = item.min_stock
                        total_stock = item.stock
                        total_inv = item.inventur or 0
                        best = item.best_bung
                        meta = {
                            "item_id": item.id,
                            "model_id": model.id,
                            "part_type_id": pt.id,
                            "model_name": model.name,
                            "dtype_lbl": pt.name,
                            "min_stock": total_min,
                            "stock": total_stock,
                        }

                    self._render_data_cells(r, b, bg, tk, meta, total_min, total_stock, best, total_inv, has_colors)

            elif rd["type"] == "color":
                color = rd["color"]
                self.setRowHeight(r, 36)

                # Map color names to hex values
                _CLR_HEX = {
                    "Black": "#444444", "Blue": "#2563EB", "Silver": "#B0B0BC",
                    "Gold": "#D4A520", "Green": "#10B981", "Purple": "#8B5CF6",
                    "White": "#E0E0E0", "Red": "#EF4444", "Pink": "#EC4899",
                    "Yellow": "#F59E0B", "Orange": "#F97316",
                }
                clr_hex = _CLR_HEX.get(color, tk.t2)

                # Color sub-row: colored dot + name
                color_bg = QColor(model_bg)
                color_bg.setAlpha(180)
                name_it = self._ro(f"      ● {color}")
                name_it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                name_it.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                name_it.setFont(_FONT_COLOR)
                name_it.setForeground(QColor(clr_hex))
                name_it.setBackground(color_bg)
                self.setItem(r, 0, name_it)

                for ti, pt in enumerate(cat.part_types):
                    b  = _base(ti)
                    bg = type_bgs[ti]
                    item = item_map.get((model.id, pt.key, color))

                    if not item:
                        for c in range(_COLS_PER_TYPE):
                            cell = self._ro("")
                            cell.setBackground(bg)
                            self.setItem(r, b + c, cell)
                        continue

                    meta = {
                        "item_id": item.id,
                        "model_id": model.id,
                        "part_type_id": pt.id,
                        "model_name": model.name,
                        "dtype_lbl": f"{pt.name} ({color})",
                        "min_stock": item.min_stock,
                        "stock": item.stock,
                    }
                    self._render_data_cells(r, b, bg, tk, meta, item.min_stock, item.stock, item.best_bung, item.inventur)

        self.setUpdatesEnabled(True)

    def _render_data_cells(self, r: int, b: int, bg: QColor, tk,
                           meta: dict, min_stock: int, stock: int,
                           best: int, inventur, has_colors: bool = False):
        """Render the 4 data cells (MinStock, BestBung, Stock, Order) for a row."""
        # Min-Stock
        st = self._cell(str(min_stock), meta | {"field": "stamm_zahl"})
        st.setForeground(QColor(tk.t2))
        st.setFont(_FONT_DATA)
        st.setBackground(bg)
        st.setToolTip(t("disp_tip_stamm"))
        self.setItem(r, b, st)

        # Best-Bung
        if best == 0:
            bb_txt, bb_col, bb_tip = "0", tk.yellow, t("disp_tip_bb_zero")
        elif best < 0:
            bb_txt, bb_col = str(best), tk.red
            bb_tip = t("disp_tip_bb_neg", n=abs(best))
        else:
            bb_txt, bb_col = f"+{best}", tk.green
            bb_tip = t("disp_tip_bb_pos", n=best)
        bb = self._cell(bb_txt, meta | {"field": "best_bung"})
        bb.setForeground(QColor(bb_col))
        bb.setFont(_FONT_MONO)
        bb.setBackground(bg)
        bb.setToolTip(bb_tip)
        self.setItem(r, b + 1, bb)

        # Stock
        stk = self._cell(str(stock), meta | {"field": "stock"})
        if stock == 0:
            stk.setForeground(QColor(tk.red))
        elif min_stock > 0 and stock <= min_stock:
            stk.setForeground(QColor(tk.yellow))
        else:
            stk.setForeground(QColor(tk.green))
        stk.setFont(_FONT_MONO)
        stk.setBackground(bg)
        stk.setToolTip(t("disp_tip_stock"))
        if has_colors:
            stk.setToolTip("Total across all colors")
        self.setItem(r, b + 2, stk)

        # Order
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

        # Per-model color override
        if "model_id" in meta and "part_type_id" in meta:
            menu.addSeparator()
            _mid = meta["model_id"]
            _ptid = meta["part_type_id"]
            act_color = menu.addAction(f"🎨  Set {_mn} Colors…")
            act_color.triggered.connect(
                lambda _=False, mid=_mid, ptid=_ptid, mn=_mn, dl=_dl:
                    self._ctx_set_color(mid, ptid, mn, dl)
            )

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
            new_val = dlg.value()
            _item_repo.update_min_stock(item_id, new_val)
            from app.services.undo_manager import UNDO, Command
            iid, prev, curr = item_id, current, new_val
            # Undo commands must be thread-safe — only DB ops, no UI calls.
            # UI refresh is triggered by MainWindow._on_undo_done on main thread.
            UNDO.push(Command(
                label=f"Min-Stock {model_name} · {dtype_lbl} ({prev} → {curr})",
                undo_fn=lambda: _item_repo.update_min_stock(iid, prev),
                redo_fn=lambda: _item_repo.update_min_stock(iid, curr),
            ))
            self._refresh_cb()

    def _ctx_order(self, item_id: int, model_name: str, dtype_lbl: str, stock: int) -> None:
        dlg = InventurDialog(model_name, dtype_lbl, stock, self, item_id=item_id)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_val = dlg.value()
            item = _item_repo.get_by_id(item_id)
            prev_val = item.inventur if item else 0
            _item_repo.update_inventur(item_id, new_val)
            from app.services.undo_manager import UNDO, Command
            iid, prev, curr = item_id, prev_val, new_val
            UNDO.push(Command(
                label=f"Order {model_name} · {dtype_lbl} ({prev} → {curr})",
                undo_fn=lambda: _item_repo.update_inventur(iid, prev),
                redo_fn=lambda: _item_repo.update_inventur(iid, curr),
            ))
            self._refresh_cb()

    def _ctx_set_color(self, model_id: int, part_type_id: int,
                       model_name: str, dtype_lbl: str) -> None:
        """Open the same color-toggle popup as settings — select which product
        colors (Black, Silver, Gold…) apply to this model + part type."""
        from PyQt6.QtWidgets import QPushButton, QLabel
        from app.repositories.category_repo import CategoryRepository
        from app.core.database import ensure_matrix_entries
        cat_repo = CategoryRepository()
        tk = THEME.tokens

        # All colors defined globally for this part type
        all_colors = cat_repo.get_pt_colors(part_type_id)
        if not all_colors:
            QMessageBox.information(
                self, dtype_lbl,
                "No colors defined for this part type.\n"
                "Add colors in Admin → Part Types first.",
            )
            return

        # Currently selected colors for this model (empty = use all global)
        current = set(cat_repo.get_model_pt_colors(model_id, part_type_id))
        use_all = len(current) == 0  # no override → all global colors active

        _ALL_HEX = {
            "Black": "#333333", "Blue": "#2563EB", "Silver": "#A0A0B0",
            "Gold": "#D4A520", "Green": "#10B981", "Purple": "#8B5CF6",
            "White": "#E0E0E0", "Red": "#EF4444", "Pink": "#EC4899",
            "Yellow": "#F59E0B", "Orange": "#F97316",
        }

        dlg = QDialog(self)
        dlg.setWindowTitle(f"{model_name} · {dtype_lbl}")
        dlg.setMinimumWidth(360)
        THEME.apply(dlg)

        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 20, 20, 16)
        lay.setSpacing(12)

        hdr = QLabel(f"{model_name} — {dtype_lbl}")
        hdr.setObjectName("dlg_header")
        lay.addWidget(hdr)

        hint = QLabel("Select which colors this model should have:")
        hint.setStyleSheet(f"font-size:12px; color:{tk.t3};")
        lay.addWidget(hint)

        # Color toggle buttons — same style as settings
        grid = QHBoxLayout()
        grid.setSpacing(8)
        selected: dict[str, bool] = {}
        btn_map: dict[str, QPushButton] = {}

        for clr in all_colors:
            name = clr["color_name"]
            hex_val = _ALL_HEX.get(name, "#888888")
            is_on = use_all or name in current
            selected[name] = is_on
            btn = QPushButton()
            btn.setFixedSize(44, 44)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(name)
            btn_map[name] = btn

            def _toggle(_, c=name, b=btn, h=hex_val):
                selected[c] = not selected[c]
                is_light = QColor(h).lightness() > 180
                brd = "#666" if is_light else "transparent"
                if selected[c]:
                    b.setStyleSheet(
                        f"QPushButton {{ background:{h}; border:3px solid {tk.green}; border-radius:8px; }}"
                    )
                else:
                    b.setStyleSheet(
                        f"QPushButton {{ background:{h}; border:2px solid {brd}; border-radius:8px; }}"
                        f"QPushButton:hover {{ border:3px solid {tk.green}; }}"
                    )

            # Initial style
            is_light = QColor(hex_val).lightness() > 180
            brd = "#666" if is_light else "transparent"
            if is_on:
                btn.setStyleSheet(
                    f"QPushButton {{ background:{hex_val}; border:3px solid {tk.green}; border-radius:8px; }}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ background:{hex_val}; border:2px solid {brd}; border-radius:8px; }}"
                    f"QPushButton:hover {{ border:3px solid {tk.green}; }}"
                )
            btn.clicked.connect(_toggle)
            grid.addWidget(btn)

        grid.addStretch()
        lay.addLayout(grid)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        sel_all = QPushButton("Select All")
        sel_all.setObjectName("btn_ghost")
        sel_all.setFixedHeight(32)
        def _select_all():
            for c in selected:
                selected[c] = True
                b = btn_map[c]
                h = _ALL_HEX.get(c, "#888888")
                b.setStyleSheet(
                    f"QPushButton {{ background:{h}; border:3px solid {tk.green}; border-radius:8px; }}"
                )
        sel_all.clicked.connect(_select_all)
        btn_row.addWidget(sel_all)

        # "No Colors" — remove all color variants, keep only the base product
        no_clr_btn = QPushButton("No Colors")
        no_clr_btn.setObjectName("btn_ghost")
        no_clr_btn.setFixedHeight(32)
        no_clr_btn.setToolTip("Remove all colors — only the base product (no color variants)")
        def _no_colors():
            from app.core.database import get_connection
            all_pt_ids = [pt.id for pt in self._cat.part_types] if self._cat else [part_type_id]
            with get_connection() as conn:
                for ptid in all_pt_ids:
                    # Set override to empty list (= explicitly no colors)
                    conn.execute(
                        "DELETE FROM model_part_type_colors WHERE model_id=? AND part_type_id=?",
                        (model_id, ptid),
                    )
                    # Insert a special marker: empty string means "no colors"
                    conn.execute(
                        "INSERT OR IGNORE INTO model_part_type_colors "
                        "(model_id, part_type_id, color_name) VALUES (?, ?, ?)",
                        (model_id, ptid, "__NONE__"),
                    )
                    # Delete all colored inventory items (zero stock only)
                    conn.execute(
                        "DELETE FROM inventory_items "
                        "WHERE model_id=? AND part_type_id=? AND color != '' "
                        "AND stock=0 AND min_stock=0 "
                        "AND (inventur IS NULL OR inventur=0)",
                        (model_id, ptid),
                    )
                    # Ensure colorless parent row exists
                    conn.execute(
                        "INSERT OR IGNORE INTO inventory_items "
                        "(model_id, part_type_id, color) VALUES (?,?,'')",
                        (model_id, ptid),
                    )
            dlg.accept()
            self._refresh_cb()
        no_clr_btn.clicked.connect(_no_colors)
        btn_row.addWidget(no_clr_btn)

        reset_btn = QPushButton("Use Default")
        reset_btn.setObjectName("btn_ghost")
        reset_btn.setFixedHeight(32)
        reset_btn.setToolTip("Remove override — use global part type colors")
        def _reset():
            all_pt_ids = [pt.id for pt in self._cat.part_types] if self._cat else [part_type_id]
            for ptid in all_pt_ids:
                cat_repo.clear_model_pt_colors(model_id, ptid)
            ensure_matrix_entries()
            dlg.accept()
            self._refresh_cb()
        reset_btn.clicked.connect(_reset)
        btn_row.addWidget(reset_btn)
        btn_row.addStretch()

        cancel = QPushButton(t("op_cancel"))
        cancel.setObjectName("btn_ghost")
        cancel.setFixedHeight(32)
        cancel.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel)

        confirm = QPushButton("Save")
        confirm.setObjectName("btn_primary")
        confirm.setFixedHeight(32)
        def _save():
            chosen = [c for c, v in selected.items() if v]
            from app.core.database import get_connection
            chosen_set = set(chosen)

            # Get ALL part type IDs for this category so we apply
            # the color selection across every part type for this model
            all_pt_ids = [pt.id for pt in self._cat.part_types] if self._cat else [part_type_id]

            with get_connection() as conn:
                for ptid in all_pt_ids:
                    # 1. Set the per-model color override for each part type
                    conn.execute(
                        "DELETE FROM model_part_type_colors "
                        "WHERE model_id=? AND part_type_id=?",
                        (model_id, ptid),
                    )
                    for name in chosen:
                        conn.execute(
                            "INSERT OR IGNORE INTO model_part_type_colors "
                            "(model_id, part_type_id, color_name) VALUES (?, ?, ?)",
                            (model_id, ptid, name),
                        )
                    # 2. Delete inventory rows for unselected colors
                    rows = conn.execute(
                        "SELECT id, color FROM inventory_items "
                        "WHERE model_id=? AND part_type_id=? AND color != ''",
                        (model_id, ptid),
                    ).fetchall()
                    for row in rows:
                        if row["color"] not in chosen_set:
                            conn.execute(
                                "DELETE FROM inventory_items WHERE id=? "
                                "AND stock=0 AND min_stock=0 "
                                "AND (inventur IS NULL OR inventur=0)",
                                (row["id"],),
                            )
                    # 3. Insert rows for newly selected colors
                    for name in chosen:
                        conn.execute(
                            "INSERT OR IGNORE INTO inventory_items "
                            "(model_id, part_type_id, color) VALUES (?,?,?)",
                            (model_id, ptid, name),
                        )
                    # 4. Reset the colorless parent row to 0 stock
                    # (it's only used for barcode scanning, should not hold real stock)
                    conn.execute(
                        "UPDATE inventory_items SET stock=0, min_stock=0, inventur=NULL "
                        "WHERE model_id=? AND part_type_id=? AND color=''",
                        (model_id, ptid),
                    )
            dlg.accept()
            self._refresh_cb()
        confirm.clicked.connect(_save)
        btn_row.addWidget(confirm)
        lay.addLayout(btn_row)

        dlg.exec()

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
        if (not self._skip_banner and row == _HEADER_ROW) or col == 0:
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

        from app.services.undo_manager import UNDO, Command

        if field == "stamm_zahl":
            dlg = ThresholdDialog(model_name, dtype_lbl, min_stock, self, item_id=item_id)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                new_val = dlg.value()
                _item_repo.update_min_stock(item_id, new_val)
                iid, prev, curr = item_id, min_stock, new_val
                UNDO.push(Command(
                    label=f"Min-Stock {model_name} · {dtype_lbl} ({prev} → {curr})",
                    undo_fn=lambda: _item_repo.update_min_stock(iid, prev),
                    redo_fn=lambda: _item_repo.update_min_stock(iid, curr),
                ))
                self._refresh_cb()

        elif field == "stock":
            item = _item_repo.get_by_id(item_id)
            if not item:
                return
            dlg = StockOpDialog(item, dtype_lbl, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                op, qty = dlg.result_data()
                try:
                    iid, q = item_id, qty
                    if op == "IN":
                        _stock_svc.stock_in(iid, q)
                        UNDO.push(Command(
                            label=f"Stock IN {model_name} · {dtype_lbl} (+{q})",
                            undo_fn=lambda: _stock_svc.stock_out(iid, q, "undo"),
                            redo_fn=lambda: _stock_svc.stock_in(iid, q, "redo"),
                        ))
                    elif op == "OUT":
                        _stock_svc.stock_out(iid, q)
                        UNDO.push(Command(
                            label=f"Stock OUT {model_name} · {dtype_lbl} (-{q})",
                            undo_fn=lambda: _stock_svc.stock_in(iid, q, "undo"),
                            redo_fn=lambda: _stock_svc.stock_out(iid, q, "redo"),
                        ))
                    else:
                        prev_stock = item.stock
                        _stock_svc.stock_adjust(iid, q)
                        UNDO.push(Command(
                            label=f"Adjust {model_name} · {dtype_lbl} ({prev_stock} → {q})",
                            undo_fn=lambda p=prev_stock: _stock_svc.stock_adjust(iid, p, "undo"),
                            redo_fn=lambda n=q: _stock_svc.stock_adjust(iid, n, "redo"),
                        ))
                    self._refresh_cb()
                except ValueError as exc:
                    QMessageBox.warning(self, t("disp_stock_err"), str(exc))

        elif field == "inventur":
            dlg = InventurDialog(model_name, dtype_lbl, stock, self, item_id=item_id)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                new_val = dlg.value()
                item_cur = _item_repo.get_by_id(item_id)
                prev_val = item_cur.inventur if item_cur else 0
                _item_repo.update_inventur(item_id, new_val)
                iid, prev, curr = item_id, prev_val, new_val
                UNDO.push(Command(
                    label=f"Order {model_name} · {dtype_lbl} ({prev} → {curr})",
                    undo_fn=lambda: _item_repo.update_inventur(iid, prev),
                    redo_fn=lambda: _item_repo.update_inventur(iid, curr),
                ))
                self._refresh_cb()


# ── Frozen container: sticky model column ─────────────────────────────────────

class FrozenMatrixContainer(QWidget):
    """Wraps a MatrixWidget with:
    - A frozen model-name column on the left
    - Part-type banner labels ABOVE the column headers

    Layout:
    ┌──────────────┬──[ (JK) incell FHD ]──[ (D.D) Soft-OLED ]──┐  ← banner
    ├──────────────┼──MS──Δ──Stock──Ord──┼──MS──Δ──Stock──Ord──┤  ← col headers
    │  X           │  0   0   0     —    │  0   0   0     —    │
    │  XS          │  …                                         │
    └──────────────┴────────────────────────────────────────────┘
    """

    def __init__(self, refresh_cb, parent=None):
        super().__init__(parent)
        self._refresh_cb = refresh_cb
        self._cat = None
        self._banner_labels: list[QWidget] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Row 0: banner bar (part-type names) ────────────────
        self._banner_row = QHBoxLayout()
        self._banner_row.setContentsMargins(0, 0, 0, 0)
        self._banner_row.setSpacing(0)

        # Left spacer matching model column
        self._banner_spacer = QWidget()
        self._banner_spacer.setFixedWidth(_COL_W["model"] + 2)
        self._banner_spacer.setFixedHeight(30)
        self._banner_row.addWidget(self._banner_spacer)

        # Scrollable area for banner labels (synced with data table h-scroll)
        from PyQt6.QtWidgets import QScrollArea
        self._banner_scroll = QScrollArea()
        self._banner_scroll.setFixedHeight(0)  # hidden until load
        self._banner_scroll.setWidgetResizable(False)
        self._banner_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._banner_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._banner_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._banner_inner = QWidget()
        self._banner_lay = QHBoxLayout(self._banner_inner)
        self._banner_lay.setContentsMargins(0, 0, 0, 0)
        self._banner_lay.setSpacing(0)
        self._banner_scroll.setWidget(self._banner_inner)
        self._banner_row.addWidget(self._banner_scroll, 1)

        self._banner_labels: list[QWidget] = []
        root.addLayout(self._banner_row)

        # ── Row 1: side-by-side tables ─────────────────────────
        tables_row = QHBoxLayout()
        tables_row.setContentsMargins(0, 0, 0, 0)
        tables_row.setSpacing(0)

        # Left: frozen model column
        self._model_table = QTableWidget()
        self._model_table.setObjectName("matrix_frozen_models")
        self._model_table.verticalHeader().setMinimumSectionSize(1)
        self._model_table.setColumnCount(1)
        self._model_table.setHorizontalHeaderLabels([t("disp_col_model")])
        self._model_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Fixed
        )
        self._model_table.setColumnWidth(0, _COL_W["model"])
        self._model_table.setFixedWidth(_COL_W["model"] + 2)
        self._model_table.verticalHeader().setVisible(False)
        self._model_table.setShowGrid(True)
        self._model_table.setFrameShape(QFrame.Shape.NoFrame)
        self._model_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._model_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._model_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._model_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._model_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        delegate = _MatrixCellDelegate(self._model_table)
        self._model_table.setItemDelegateForColumn(0, delegate)
        tables_row.addWidget(self._model_table)

        # Right: data table (MatrixWidget) — banner is rendered externally
        self._table = MatrixWidget(refresh_cb=refresh_cb, parent=self, skip_banner_row=True)
        tables_row.addWidget(self._table, 1)

        # Sync vertical scrolling
        self._table.verticalScrollBar().valueChanged.connect(
            self._model_table.verticalScrollBar().setValue
        )
        self._model_table.verticalScrollBar().valueChanged.connect(
            self._table.verticalScrollBar().setValue
        )

        # Sync row selection → highlight model column when data row is selected
        self._table.currentCellChanged.connect(self._on_data_current_changed)

        # Enable hover tracking on the model table too
        self._model_table.setMouseTracking(True)
        self._model_table._hover_row = -1
        # Monkey-patch mouse move/leave on the model table to update hover
        _orig_mm = self._model_table.mouseMoveEvent
        _orig_le = self._model_table.leaveEvent
        def _mt_mm(event, self=self, _orig=_orig_mm):
            idx = self._model_table.indexAt(event.pos())
            row = idx.row() if idx.isValid() else -1
            if row != self._model_table._hover_row:
                self._model_table._hover_row = row
                self._model_table.viewport().update()
                # Mirror to data table
                if self._table._hover_row != row:
                    self._table._hover_row = row
                    self._table.viewport().update()
            _orig(event)
        def _mt_le(event, self=self, _orig=_orig_le):
            if self._model_table._hover_row != -1:
                self._model_table._hover_row = -1
                self._model_table.viewport().update()
                if self._table._hover_row != -1:
                    self._table._hover_row = -1
                    self._table.viewport().update()
            _orig(event)
        self._model_table.mouseMoveEvent = _mt_mm
        self._model_table.leaveEvent = _mt_le

        root.addLayout(tables_row, 1)

    @property
    def data_table(self) -> MatrixWidget:
        return self._table

    # ── Hover / selection sync with frozen model column ───────────────────────
    def _on_data_hover_row(self, row: int) -> None:
        """Called by data-table mouseMoveEvent to mirror hover onto model table."""
        if self._model_table._hover_row != row:
            self._model_table._hover_row = row
            self._model_table.viewport().update()

    def _on_data_current_changed(self, cur_row, _cc, prev_row, _pc):
        """Highlight the selected row on both tables by triggering a repaint."""
        # Model table has no selection, but the delegate reads _hover_row;
        # we reuse it as a "current row" marker for visual parity. When the
        # selection changes we ensure the model side mirrors it briefly so
        # the whole row reads as a unit.
        self._model_table.viewport().update()

    def load(self, cat, models, item_map, brand_boundaries=None):
        """Load data into both tables and build the banner."""
        self._cat = cat
        self._table.load(cat, models, item_map, brand_boundaries=brand_boundaries)

        # Hide column 0 in data table — shown by frozen side table
        self._table.setColumnHidden(0, True)

        self._sync_model_column()
        self._build_banner(cat)

    def _build_banner(self, cat):
        """Build part-type name labels above the table, aligned with columns."""
        for w in self._banner_labels:
            w.deleteLater()
        self._banner_labels.clear()
        while self._banner_lay.count():
            self._banner_lay.takeAt(0)

        if not cat or not cat.part_types:
            self._banner_scroll.setFixedHeight(0)
            self._banner_spacer.setFixedHeight(0)
            return

        from PyQt6.QtWidgets import QLabel
        tk = THEME.tokens
        is_dark = tk.is_dark

        total_w = 0
        for ti, pt in enumerate(cat.part_types):
            hdr_bg = QColor(pt.accent_color)
            if is_dark:
                r = int(0.30 * hdr_bg.red()   + 0.70 * 15)
                g = int(0.30 * hdr_bg.green() + 0.70 * 15)
                b = int(0.30 * hdr_bg.blue()  + 0.70 * 15)
            else:
                r = int(0.35 * hdr_bg.red()   + 0.65 * 245)
                g = int(0.35 * hdr_bg.green() + 0.65 * 245)
                b = int(0.35 * hdr_bg.blue()  + 0.65 * 245)

            # Calculate actual pixel width from the data table's columns
            base = _base(ti)
            w = 0
            for c in range(_COLS_PER_TYPE):
                w += self._table.columnWidth(base + c)
            total_w += w

            lbl = QLabel(pt.name)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedHeight(30)
            lbl.setFixedWidth(w)
            lbl.setStyleSheet(
                f"background: rgb({r},{g},{b}); "
                f"color: {pt.accent_color}; "
                f"font-size: 10pt; font-weight: 700; "
                f"border: none; padding: 0 4px;"
            )
            self._banner_lay.addWidget(lbl)
            self._banner_labels.append(lbl)

        self._banner_inner.setFixedWidth(total_w)
        self._banner_inner.setFixedHeight(30)
        self._banner_scroll.setFixedHeight(30)
        self._banner_spacer.setFixedHeight(30)

        # Sync banner horizontal scroll with data table
        try:
            self._table.horizontalScrollBar().valueChanged.disconnect(self._on_h_scroll)
        except (TypeError, RuntimeError):
            pass
        self._table.horizontalScrollBar().valueChanged.connect(self._on_h_scroll)

    def _on_h_scroll(self, value):
        """Sync the banner scroll position with the data table."""
        self._banner_scroll.horizontalScrollBar().setValue(value)

    def _sync_model_column(self):
        """Copy column 0 from the main table to the frozen model table."""
        mt = self._model_table
        dt = self._table

        mt.setRowCount(dt.rowCount())
        max_text_w = 0
        fm = mt.fontMetrics()
        for r in range(dt.rowCount()):
            src = dt.item(r, 0)
            if src:
                clone = QTableWidgetItem(src.text())
                clone.setFlags(src.flags())
                clone.setTextAlignment(src.textAlignment())
                clone.setFont(src.font())
                clone.setForeground(src.foreground())
                clone.setBackground(src.background())
                mt.setItem(r, 0, clone)
                # Measure text width using the item's font
                text_w = fm.horizontalAdvance(src.text()) + 24  # padding
                if src.font().bold() or src.font().weight() >= QFont.Weight.DemiBold:
                    text_w += 10  # bold text is wider
                if text_w > max_text_w:
                    max_text_w = text_w
            mt.setRowHeight(r, dt.rowHeight(r))

        # Auto-fit column width to longest model name
        col_w = max(max_text_w, _COL_W["model"])
        mt.setColumnWidth(0, col_w)
        mt.setFixedWidth(col_w + 2)
        self._banner_spacer.setFixedWidth(col_w + 2)

        mt.horizontalHeader().setFixedHeight(dt.horizontalHeader().height())

    def retranslate(self):
        self._model_table.setHorizontalHeaderLabels([t("disp_col_model")])
        self._table.retranslate()
        if self._cat:
            self._build_banner(self._cat)
