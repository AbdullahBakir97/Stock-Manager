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
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
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

_COLS_PER_TYPE = 7   # Min-Stock | Best-Bung | Stock | Order | Sell | Price | Total
# Sub-column offsets within a part-type group (makes indexing self-documenting)
_SUB_MIN, _SUB_BB, _SUB_STOCK, _SUB_ORDER, _SUB_SELL, _SUB_PRICE, _SUB_TOTAL = 0, 1, 2, 3, 4, 5, 6
_COL_W = {"model": 160, "stamm": 108, "bestbung": 104, "stock": 70,
          "inventur": 72, "sell": 68, "price": 68, "total": 82}
_HEADER_ROW = 0

# Fonts — base point sizes (what items render at at 100% zoom)
_FONT_MONO   = QFont("JetBrains Mono", 11, QFont.Weight.Bold)
_FONT_MONO.setStyleHint(QFont.StyleHint.Monospace)
_FONT_MODEL  = QFont("Segoe UI", 11, QFont.Weight.DemiBold)
_FONT_HEADER = QFont("Segoe UI", 10, QFont.Weight.Bold)
_FONT_DATA   = QFont("Segoe UI", 10)
_FONT_COLOR  = QFont("Segoe UI", 9)
_FONT_BRAND  = QFont("Segoe UI", 12, QFont.Weight.Bold)

# Custom item role used to remember each item's original (100%) font size so
# apply_zoom can scale it correctly regardless of how many times it fires.
BASE_PT_ROLE = Qt.ItemDataRole.UserRole + 99


def _set_item_font(item, font: "QFont", base_pt: int) -> None:
    """Apply a font to an item AND record its base point size so that
    subsequent apply_zoom calls can recompute the scaled size."""
    item.setFont(font)
    item.setData(BASE_PT_ROLE, base_pt)


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


def _type_visible_width(table, ti: int) -> int:
    """Sum of the VISIBLE column widths for part-type group `ti`.

    Hidden columns (cost_price / total when the admin toggle is off) are
    excluded so that the banner chip above the group never over-stretches.
    """
    b = _base(ti)
    w = 0
    for c in range(_COLS_PER_TYPE):
        col = b + c
        if not table.isColumnHidden(col):
            w += table.columnWidth(col)
    return w


import re as _re


def _fmt_money(val) -> str:
    """Format a numeric value using the shop's configured currency symbol.

    Falls back to `{:,.2f}` (no symbol) if ShopConfig isn't loadable.
    Returns `'—'` for None / non-numeric input.
    """
    if val is None:
        return "—"
    try:
        v = float(val)
    except (TypeError, ValueError):
        return "—"
    try:
        from app.core.config import ShopConfig
        return ShopConfig.get().format_currency(v)
    except Exception:
        return f"{v:,.2f}"

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
        # Excel-like selection: click a cell → one cell; click-drag → rect
        # selection; Shift-click → extend; Ctrl-click → toggle. Required
        # for the Ctrl+D "Fill Down" feature (see `_fill_down_from_selection`).
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
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

    def keyPressEvent(self, event):
        """Excel-style keyboard shortcuts on the matrix table.

        Ctrl+D — Fill Down. The top-left cell in the current selection
        is the source; its value is copied to every other selected cell
        that shares the same field type (Min-Stock / Sell / Cost).
        """
        try:
            is_ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
            if is_ctrl and event.key() == Qt.Key.Key_D:
                self._fill_down_from_selection()
                event.accept()
                return
        except Exception:
            pass
        super().keyPressEvent(event)

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
                _set_item_font(it, _FONT_HEADER, 10)
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

        # Brand header colors (font comes from module-level _FONT_BRAND)
        brand_bg = QColor(tk.card2)
        brand_fg = QColor(tk.t1)

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
                        _set_item_font(cell, _FONT_BRAND, 12)
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
                _set_item_font(name_it, _FONT_MODEL, 11)
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
                            "is_aggregate": True,
                        }
                        price_src = any_item
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
                        price_src = item

                    self._render_data_cells(
                        r, b, bg, tk, meta,
                        total_min, total_stock, best, total_inv, has_colors,
                        sell_price=getattr(price_src, "sell_price", None),
                        pt_default_price=getattr(pt, "default_price", None),
                        cost_price=getattr(price_src, "cost_price", None),
                    )

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
                _set_item_font(name_it, _FONT_COLOR, 9)
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
                    self._render_data_cells(
                        r, b, bg, tk, meta,
                        item.min_stock, item.stock, item.best_bung, item.inventur,
                        sell_price=getattr(item, "sell_price", None),
                        pt_default_price=getattr(pt, "default_price", None),
                        cost_price=getattr(item, "cost_price", None),
                        is_color_row=True,
                    )

        self.setUpdatesEnabled(True)

    def _render_data_cells(self, r: int, b: int, bg: QColor, tk,
                           meta: dict, min_stock: int, stock: int,
                           best: int, inventur, has_colors: bool = False,
                           sell_price=None, pt_default_price=None,
                           cost_price=None, is_color_row: bool = False):
        """Render the 7 data cells per part-type group.

        Layout: MIN-STOCK | DIFF | STOCK | ORDER | SELL | PRICE | TOTAL
          SELL  = sell_price (falls back to part-type.default_price)
          PRICE = cost_price (purchase price — hidden by default, PIN-gated)
          TOTAL = stock × cost_price (valuation — hidden with PRICE)
        """
        # Min-Stock
        st = self._cell(str(min_stock), meta | {"field": "stamm_zahl"})
        st.setForeground(QColor(tk.t2))
        _set_item_font(st, _FONT_DATA, 10)
        st.setBackground(bg)
        st.setToolTip(t("disp_tip_stamm"))
        self.setItem(r, b + _SUB_MIN, st)

        # Best-Bung (difference)
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
        _set_item_font(bb, _FONT_MONO, 11)
        bb.setBackground(bg)
        bb.setToolTip(bb_tip)
        self.setItem(r, b + _SUB_BB, bb)

        # Stock
        stk = self._cell(str(stock), meta | {"field": "stock"})
        if stock == 0:
            stk.setForeground(QColor(tk.red))
        elif min_stock > 0 and stock <= min_stock:
            stk.setForeground(QColor(tk.yellow))
        else:
            stk.setForeground(QColor(tk.green))
        _set_item_font(stk, _FONT_MONO, 11)
        stk.setBackground(bg)
        stk.setToolTip(t("disp_tip_stock"))
        if has_colors:
            stk.setToolTip("Total across all colors")
        self.setItem(r, b + _SUB_STOCK, stk)

        # Order
        inv_txt = str(inventur) if inventur is not None else "—"
        inv = self._cell(inv_txt, meta | {"field": "inventur"})
        inv.setForeground(QColor(tk.t3))
        _set_item_font(inv, _FONT_DATA, 10)
        inv.setBackground(bg)
        inv.setToolTip(t("disp_tip_inv"))
        self.setItem(r, b + _SUB_ORDER, inv)

        # Color rows hide per-unit prices too when "show color totals" is off —
        # per-color prices are always identical to the parent's now, so they'd
        # just be redundant noise.
        hide_color_prices = False
        if is_color_row:
            try:
                from app.core.config import ShopConfig
                hide_color_prices = not ShopConfig.get().is_show_color_totals
            except Exception:
                pass

        # ── SELL price (sell_price with part-type default_price fallback) ──
        sell_val = sell_price
        sell_from_override = sell_val is not None
        if sell_val is None and pt_default_price is not None:
            sell_val = pt_default_price
        if hide_color_prices:
            sell_txt = "—"
            sell_col = tk.t4
            sell_tip = ""
        elif sell_val is None:
            sell_txt = "—"
            sell_col = tk.t4
            sell_tip = "Double-click to set sell price"
        else:
            try:
                sell_txt = _fmt_money(sell_val)
            except (TypeError, ValueError):
                sell_txt = "—"
                sell_col = tk.t4
            else:
                sell_col = tk.green if sell_from_override else tk.t3
            sell_tip = (
                f"Per-item override: {_fmt_money(sell_val)}"
                if sell_from_override
                else f"Default from part type: {_fmt_money(sell_val)}"
            )
        sell_meta = meta | {
            "field": "price",           # keep legacy field name for edit dispatch
            "sell_price": sell_price,
            "pt_default_price": pt_default_price,
        }
        sell_cell = self._cell(sell_txt, sell_meta)
        sell_cell.setForeground(QColor(sell_col))
        _set_item_font(sell_cell, _FONT_MONO, 11)
        sell_cell.setBackground(bg)
        sell_cell.setToolTip(sell_tip)
        if hide_color_prices:
            sell_cell.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self.setItem(r, b + _SUB_SELL, sell_cell)

        # ── PRICE (cost_price) — hidden by default ─────────────────────────
        if hide_color_prices:
            cp_txt, cp_col, cp_tip = "—", tk.t4, ""
        elif cost_price is None:
            cp_txt, cp_col, cp_tip = "—", tk.t4, "Double-click to set cost price"
        else:
            try:
                cp_txt = _fmt_money(cost_price)
                cp_col = tk.blue
                cp_tip = f"Cost / purchase price: {_fmt_money(cost_price)}"
            except (TypeError, ValueError):
                cp_txt, cp_col, cp_tip = "—", tk.t4, ""
        cp_meta = meta | {"field": "cost_price", "cost_price": cost_price}
        cp_cell = self._cell(cp_txt, cp_meta)
        cp_cell.setForeground(QColor(cp_col))
        _set_item_font(cp_cell, _FONT_MONO, 11)
        cp_cell.setBackground(bg)
        cp_cell.setToolTip(cp_tip)
        if hide_color_prices:
            cp_cell.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self.setItem(r, b + _SUB_PRICE, cp_cell)

        # ── TOTAL — always visible, metric flips with COST_VIS ────────────
        # Default (COST_VIS off): stock × effective_sell_price (sell_price or
        #                         part-type default_price)
        # Admin mode (COST_VIS on): stock × cost_price
        from app.services.cost_visibility import COST_VIS
        cost_mode = COST_VIS.visible
        try:
            stk_int = int(stock or 0)
        except (TypeError, ValueError):
            stk_int = 0

        if cost_mode:
            base_price = cost_price
            metric_tag = "cost"
        else:
            # Reuse the already-resolved sell_val above (sell_price with default fallback)
            base_price = sell_val
            metric_tag = "sell"

        try:
            total_val = float(base_price) * stk_int if base_price is not None else None
        except (TypeError, ValueError):
            total_val = None

        hide_color_total = False
        if is_color_row:
            try:
                from app.core.config import ShopConfig
                hide_color_total = not ShopConfig.get().is_show_color_totals
            except Exception:
                pass

        if hide_color_total:
            tot_txt, tot_col, tot_tip = "—", tk.t4, ""
        elif total_val is None:
            tot_txt, tot_col, tot_tip = "—", tk.t4, ""
        else:
            tot_txt = _fmt_money(total_val)
            tot_col = tk.t1
            tot_tip = (
                f"Stock × {metric_tag} = {stk_int} × {_fmt_money(base_price)}"
            )
        tot_meta = meta | {
            "field": "total_value",
            "readonly": True,
            "metric": metric_tag,
        }
        tot_cell = self._cell(tot_txt, tot_meta)
        tot_cell.setForeground(QColor(tot_col))
        _set_item_font(tot_cell, _FONT_MONO, 11)
        tot_cell.setBackground(bg)
        tot_cell.setToolTip(tot_tip)
        # Total is computed — not editable
        tot_cell.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self.setItem(r, b + _SUB_TOTAL, tot_cell)

    def _apply_cost_columns_visible(self) -> None:
        """Hide/show the PRICE (cost) and TOTAL columns per part-type group.

        Two independent toggles drive column visibility:

        * **PRICE** (cost_price) — controlled by `COST_VIS.visible`
          (session-local, PIN-gated via the 👁 button). Hidden by default.

        * **TOTAL** — controlled by the shop setting
          `ShopConfig.show_sell_totals` (persisted, toggled in the admin
          Shop Settings panel). Visible by default. When cost mode is on,
          we always show TOTAL regardless of the setting because the user
          has already authenticated — showing cost valuation without its
          corresponding TOTAL would be pointless.
        """
        from app.services.cost_visibility import COST_VIS
        cost_on = COST_VIS.visible
        try:
            from app.core.config import ShopConfig
            show_total = ShopConfig.get().is_show_sell_totals
        except Exception:
            show_total = True
        total_visible = show_total or cost_on

        n_types = len(self._cat.part_types) if self._cat else 0
        for i in range(n_types):
            b = _base(i)
            self.setColumnHidden(b + _SUB_PRICE, not cost_on)
            self.setColumnHidden(b + _SUB_TOTAL, not total_visible)

    def retranslate(self) -> None:
        if not self._cat:
            return
        labels = [t("disp_col_model")]
        for _ in self._cat.part_types:
            labels += [t("col_stamm_zahl"), t("col_best_bung"),
                       t("disp_col_stock"), t("col_inventur"),
                       "SELL", "COST", "TOTAL"]
        self.setHorizontalHeaderLabels(labels)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _build_headers(self, cat: CategoryConfig) -> None:
        n_types = len(cat.part_types)
        total   = 1 + n_types * _COLS_PER_TYPE
        self.setColumnCount(total)
        labels  = [t("disp_col_model")]
        for _ in cat.part_types:
            labels += [t("col_stamm_zahl"), t("col_best_bung"),
                       t("disp_col_stock"), t("col_inventur"),
                       "SELL", "COST", "TOTAL"]
        self.setHorizontalHeaderLabels(labels)
        hh = self.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.setColumnWidth(0, _COL_W["model"])
        # Apply cell delegate to every column so backgrounds render
        delegate = _MatrixCellDelegate(self)
        for col in range(total):
            self.setItemDelegateForColumn(col, delegate)
        # Columns per part type: MIN | DIFF | STOCK | ORDER | SELL | PRICE | TOTAL
        for i in range(n_types):
            b = _base(i)
            self.setColumnWidth(b + _SUB_MIN,   _COL_W["stamm"])
            self.setColumnWidth(b + _SUB_BB,    _COL_W["bestbung"])
            self.setColumnWidth(b + _SUB_STOCK, _COL_W["stock"])
            self.setColumnWidth(b + _SUB_ORDER, _COL_W["inventur"])
            self.setColumnWidth(b + _SUB_SELL,  _COL_W["sell"])
            self.setColumnWidth(b + _SUB_PRICE, _COL_W["price"])
            self.setColumnWidth(b + _SUB_TOTAL, _COL_W["total"])
        # Apply current cost-visibility on fresh header build
        self._apply_cost_columns_visible()

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

        # ── Excel-style fill-down ───────────────────────────────────────
        # Only offered when the user has multi-selected cells AND the
        # current (top-left anchor) cell is a fillable field.
        field = meta.get("field")
        sel_count = len(self.selectedIndexes())
        if field in ("stamm_zahl", "price", "cost_price") and sel_count > 1:
            menu.addSeparator()
            label_map = {
                "stamm_zahl": "Fill Down — Min-Stock",
                "price":      "Fill Down — Sell Price",
                "cost_price": "Fill Down — Cost Price",
            }
            act_fill = menu.addAction(f"⬇  {label_map[field]}  (Ctrl+D)")
            act_fill.triggered.connect(self._fill_down_from_selection)

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

    # ── Excel-style fill-down ─────────────────────────────────────────────────

    def _fill_down_from_selection(self) -> None:
        """Apply the top-left selected cell's value to every other selected
        cell of the same field type.

        Only the three fillable fields are honoured:
          · `stamm_zahl` → `ItemRepository.update_min_stock`
          · `price`      → `ItemRepository.update_price`      (sell price)
          · `cost_price` → `ItemRepository.update_cost_price`

        Cells that belong to a different field (STOCK, ORDER, TOTAL, …) or
        have no underlying item_id are skipped silently. Everything runs
        inside a single Undo Command so Ctrl+Z reverts the whole fill.
        Cost fills require COST_VIS.visible (PIN-unlocked) defensively.
        """
        sel = self.selectedIndexes()
        if not sel or len(sel) < 2:
            return

        # Anchor = top-most / left-most selected cell. Sort by (row, col)
        # so drag direction doesn't matter — Excel always fills from top-left.
        sel_sorted = sorted(sel, key=lambda idx: (idx.row(), idx.column()))
        src_idx = sel_sorted[0]
        src_item = self.item(src_idx.row(), src_idx.column())
        if src_item is None:
            return
        src_meta = src_item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(src_meta, dict):
            return

        field = src_meta.get("field")
        if field not in ("stamm_zahl", "price", "cost_price"):
            return  # not a fillable field

        # Extra safety: cost fills are gated by COST_VIS just like editing
        if field == "cost_price":
            try:
                from app.services.cost_visibility import COST_VIS
                if not COST_VIS.visible:
                    return
            except Exception:
                return

        # Resolve the source value straight from the DB (the cached meta
        # might be stale after a previous edit)
        src_id = src_meta.get("item_id")
        if src_id is None:
            return
        src_item_row = _item_repo.get_by_id(src_id)
        if src_item_row is None:
            return

        if field == "stamm_zahl":
            value = int(getattr(src_item_row, "min_stock", 0) or 0)
        elif field == "price":
            sp = getattr(src_item_row, "sell_price", None)
            value = float(sp) if sp is not None else None
        else:  # cost_price
            cp = getattr(src_item_row, "cost_price", None)
            value = float(cp) if cp is not None else None

        # Collect targets (selection minus source), keyed by field match
        targets: list[tuple[int, tuple]] = []   # (item_id, prev_tuple_for_undo)
        seen_ids: set[int] = set()
        for idx in sel_sorted[1:]:
            it = self.item(idx.row(), idx.column())
            if it is None:
                continue
            meta = it.data(Qt.ItemDataRole.UserRole)
            if not isinstance(meta, dict):
                continue
            if meta.get("field") != field:
                continue
            tgt_id = meta.get("item_id")
            if tgt_id is None or tgt_id in seen_ids or tgt_id == src_id:
                continue
            seen_ids.add(tgt_id)
            cur = _item_repo.get_by_id(tgt_id)
            if cur is None:
                continue
            if field == "stamm_zahl":
                prev = int(getattr(cur, "min_stock", 0) or 0)
            elif field == "price":
                prev = getattr(cur, "sell_price", None)
                prev = float(prev) if prev is not None else None
            else:
                prev = getattr(cur, "cost_price", None)
                prev = float(prev) if prev is not None else None
            targets.append((tgt_id, prev))

        if not targets:
            return

        # Pick the right repo-writer per field
        if field == "stamm_zahl":
            writer = _item_repo.update_min_stock
            field_lbl = "Min-Stock"
        elif field == "price":
            writer = _item_repo.update_price
            field_lbl = "Sell"
        else:
            writer = _item_repo.update_cost_price
            field_lbl = "Cost"

        # Apply in one sweep, then push ONE Undo Command so Ctrl+Z
        # reverts the entire fill.
        for tgt_id, _prev in targets:
            try:
                writer(tgt_id, value)
            except Exception:
                # Don't stall the whole fill on one bad row
                pass

        try:
            from app.services.undo_manager import UNDO, Command
            ids_values = list(targets)  # snapshot for closure
            new_value = value

            def _undo(ids_values=ids_values, writer=writer):
                for tgt_id, prev in ids_values:
                    try:
                        writer(tgt_id, prev)
                    except Exception:
                        pass

            def _redo(ids_values=ids_values, writer=writer, new_value=new_value):
                for tgt_id, _prev in ids_values:
                    try:
                        writer(tgt_id, new_value)
                    except Exception:
                        pass

            UNDO.push(Command(
                label=f"Fill Down {field_lbl} → {len(ids_values)} cell(s)",
                undo_fn=_undo,
                redo_fn=_redo,
            ))
        except Exception:
            pass

        # Trigger the container refresh
        self._refresh_cb()

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
            is_aggregate = meta.get("is_aggregate", False)
            target_item_id = item_id

            if is_aggregate:
                model_id = meta["model_id"]
                part_type_id = meta["part_type_id"]
                siblings = _item_repo.get_colored_siblings(model_id, part_type_id)
                if siblings:
                    color_names = [s.color for s in siblings]
                    from PyQt6.QtWidgets import QInputDialog
                    chosen, ok = QInputDialog.getItem(
                        self,
                        f"Choose Color — {model_name}",
                        "This model has color variants.\nChoose which color to update:",
                        color_names, 0, False,
                    )
                    if not ok:
                        return
                    for s in siblings:
                        if s.color == chosen:
                            target_item_id = s.id
                            break

            item = _item_repo.get_by_id(target_item_id)
            if not item:
                return
            dlg = StockOpDialog(item, dtype_lbl, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                op, qty = dlg.result_data()
                try:
                    iid, q = target_item_id, qty
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

        elif field == "price":
            from PyQt6.QtWidgets import QInputDialog
            is_aggregate = meta.get("is_aggregate", False)
            item_cur = _item_repo.get_by_id(item_id)
            prev_price = None
            if item_cur is not None and item_cur.sell_price is not None:
                prev_price = float(item_cur.sell_price)
            prev_txt = (
                f"{prev_price:.2f}" if prev_price is not None
                else f"(default {float(meta.get('pt_default_price') or 0.0):.2f})"
            )
            title_suffix = " (all colors)" if is_aggregate else ""
            new_val, ok = QInputDialog.getDouble(
                self,
                f"Sell Price — {model_name} · {dtype_lbl}{title_suffix}",
                f"Current: {prev_txt}\nNew unit sell price "
                f"(0 = clear override → use part-type default):"
                + ("\n\nThis will apply to ALL color variants." if is_aggregate else ""),
                0.0, 0.0, 999999.99, 2,
            )
            if not ok:
                return
            new_price = None if new_val <= 0 else float(new_val)

            if is_aggregate:
                model_id = meta["model_id"]
                part_type_id = meta["part_type_id"]
                siblings = _item_repo.get_colored_siblings(model_id, part_type_id)
                prev_prices = {}
                for s in siblings:
                    prev_prices[s.id] = float(s.sell_price) if s.sell_price is not None else None
                    _item_repo.update_price(s.id, new_price)
                saved_prev = dict(prev_prices)
                saved_new = new_price
                UNDO.push(Command(
                    label=f"Sell {model_name} · {dtype_lbl} all colors → {saved_new or '—'}",
                    undo_fn=lambda: [_item_repo.update_price(sid, sp) for sid, sp in saved_prev.items()],
                    redo_fn=lambda: [_item_repo.update_price(sid, saved_new) for sid in saved_prev],
                ))
            else:
                _item_repo.update_price(item_id, new_price)
                iid, prev, curr = item_id, prev_price, new_price
                UNDO.push(Command(
                    label=f"Sell {model_name} · {dtype_lbl} ({prev or '—'} → {curr or '—'})",
                    undo_fn=lambda: _item_repo.update_price(iid, prev),
                    redo_fn=lambda: _item_repo.update_price(iid, curr),
                ))

            # ── Instant local update of TOTAL (only when not in cost mode)
            from app.services.cost_visibility import COST_VIS
            if not COST_VIS.visible:
                tk = THEME.tokens
                base_col = col - _SUB_SELL
                # Also refresh this SELL cell's own text with currency symbol
                it.setText(_fmt_money(new_price) if new_price is not None
                           else (_fmt_money(meta.get("pt_default_price"))
                                 if meta.get("pt_default_price") is not None else "—"))
                total_item = self.item(row, base_col + _SUB_TOTAL)
                if total_item is not None:
                    effective = new_price if new_price is not None else meta.get("pt_default_price")
                    if effective is None:
                        total_item.setText("—")
                        total_item.setForeground(QColor(tk.t4))
                        total_item.setToolTip("")
                    else:
                        stk_int = int(stock or 0)
                        total_val = float(effective) * stk_int
                        total_item.setText(_fmt_money(total_val))
                        total_item.setForeground(QColor(tk.t1))
                        total_item.setToolTip(
                            f"Stock × sell = {stk_int} × {_fmt_money(effective)}"
                        )

            self._refresh_cb()

        elif field == "cost_price":
            from app.services.cost_visibility import COST_VIS
            if not COST_VIS.visible:
                return
            from PyQt6.QtWidgets import QInputDialog
            is_aggregate = meta.get("is_aggregate", False)
            item_cur = _item_repo.get_by_id(item_id)
            prev_cost = None
            if item_cur is not None and getattr(item_cur, "cost_price", None) is not None:
                prev_cost = float(item_cur.cost_price)
            prev_txt = f"{prev_cost:.2f}" if prev_cost is not None else "—"
            title_suffix = " (all colors)" if is_aggregate else ""
            new_val, ok = QInputDialog.getDouble(
                self,
                f"Cost Price — {model_name} · {dtype_lbl}{title_suffix}",
                f"Current: {prev_txt}\nNew unit cost / purchase price "
                f"(0 = clear):"
                + ("\n\nThis will apply to ALL color variants." if is_aggregate else ""),
                0.0, 0.0, 999999.99, 2,
            )
            if not ok:
                return
            new_cost = None if new_val <= 0 else float(new_val)

            if is_aggregate:
                model_id = meta["model_id"]
                part_type_id = meta["part_type_id"]
                siblings = _item_repo.get_colored_siblings(model_id, part_type_id)
                prev_costs = {}
                for s in siblings:
                    prev_costs[s.id] = float(s.cost_price) if getattr(s, "cost_price", None) is not None else None
                    _item_repo.update_cost_price(s.id, new_cost)
                saved_prev = dict(prev_costs)
                saved_new = new_cost
                UNDO.push(Command(
                    label=f"Cost {model_name} · {dtype_lbl} all colors → {saved_new or '—'}",
                    undo_fn=lambda: [_item_repo.update_cost_price(sid, sp) for sid, sp in saved_prev.items()],
                    redo_fn=lambda: [_item_repo.update_cost_price(sid, saved_new) for sid in saved_prev],
                ))
            else:
                _item_repo.update_cost_price(item_id, new_cost)
                iid, prev, curr = item_id, prev_cost, new_cost
                UNDO.push(Command(
                    label=f"Cost {model_name} · {dtype_lbl} ({prev or '—'} → {curr or '—'})",
                    undo_fn=lambda: _item_repo.update_cost_price(iid, prev),
                    redo_fn=lambda: _item_repo.update_cost_price(iid, curr),
                ))

            # ── Instant local updates — no DB round-trip wait ────────────
            # 1) Repaint THIS cell with the new cost text/colour
            tk = THEME.tokens
            if new_cost is None:
                it.setText("—")
                it.setForeground(QColor(tk.t4))
                it.setToolTip("Double-click to set cost price")
            else:
                it.setText(_fmt_money(new_cost))
                it.setForeground(QColor(tk.blue))
                it.setToolTip(f"Cost / purchase price: {_fmt_money(new_cost)}")
            # Keep meta fresh so further edits start from the new value
            new_meta = dict(meta)
            new_meta["cost_price"] = new_cost
            it.setData(Qt.ItemDataRole.UserRole, new_meta)

            # 2) Repaint the neighbouring TOTAL cell immediately
            base_col = col - _SUB_PRICE
            total_item = self.item(row, base_col + _SUB_TOTAL)
            if total_item is not None:
                if new_cost is None:
                    total_item.setText("—")
                    total_item.setForeground(QColor(tk.t4))
                    total_item.setToolTip("")
                else:
                    stk_int = int(stock or 0)
                    total_val = new_cost * stk_int
                    total_item.setText(_fmt_money(total_val))
                    total_item.setForeground(QColor(tk.t1))
                    total_item.setToolTip(
                        f"Stock × cost = {stk_int} × {_fmt_money(new_cost)}"
                    )

            # 3) Full refresh for DB-consistent state. refresh_cb is
            # MatrixTab.refresh which re-queries and calls _rebuild_cards —
            # so the top part-type cards pick up the new valuation too.
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
        self._item_map: dict = {}
        self._banner_labels: list[QWidget] = []

        # Listen for admin cost-visibility flips — re-apply hidden columns
        # and rebuild the banner so chip widths match visible columns again.
        from app.services.cost_visibility import COST_VIS
        COST_VIS.changed.connect(self._on_cost_visibility_changed)

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
        self._item_map = item_map or {}
        self._table.load(cat, models, item_map, brand_boundaries=brand_boundaries)

        # Hide column 0 in data table — shown by frozen side table
        self._table.setColumnHidden(0, True)

        self._sync_model_column()
        self._build_banner(cat)

    def _build_banner(self, cat):
        """Build slim per-part-type column-grouping chips above the table.

        Totals/value now live in the top-level cards strip (MatrixTab).
        This banner only handles column grouping, so it's intentionally slim:
        a name chip with gradient + 2px accent-coloured bottom border aligned
        with its 5 underlying data columns.
        """
        for w in self._banner_labels:
            w.deleteLater()
        self._banner_labels.clear()
        while self._banner_lay.count():
            self._banner_lay.takeAt(0)

        if not cat or not cat.part_types:
            self._banner_scroll.setFixedHeight(0)
            self._banner_spacer.setFixedHeight(0)
            return

        tk = THEME.tokens
        is_dark = tk.is_dark

        total_w = 0
        for ti, pt in enumerate(cat.part_types):
            hdr_bg = QColor(pt.accent_color)
            if is_dark:
                r = int(0.30 * hdr_bg.red()   + 0.70 * 15)
                g = int(0.30 * hdr_bg.green() + 0.70 * 15)
                b = int(0.30 * hdr_bg.blue()  + 0.70 * 15)
                r_t, g_t, b_t = min(r + 12, 255), min(g + 12, 255), min(b + 12, 255)
                r_b, g_b, b_b = max(r - 8, 0), max(g - 8, 0), max(b - 8, 0)
                hair = 22
            else:
                r = int(0.35 * hdr_bg.red()   + 0.65 * 245)
                g = int(0.35 * hdr_bg.green() + 0.65 * 245)
                b = int(0.35 * hdr_bg.blue()  + 0.65 * 245)
                r_t, g_t, b_t = min(r + 6, 255), min(g + 6, 255), min(b + 6, 255)
                r_b, g_b, b_b = max(r - 4, 0), max(g - 4, 0), max(b - 4, 0)
                hair = 60

            # Column-aligned width = sum of VISIBLE underlying columns
            w = _type_visible_width(self._table, ti)
            total_w += w

            lbl = QLabel(pt.name)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedHeight(30)
            lbl.setFixedWidth(w)

            chip_font = QFont("Segoe UI", 10, QFont.Weight.DemiBold)
            chip_font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 104)
            lbl.setFont(chip_font)

            lbl.setStyleSheet(
                "QLabel {"
                f"background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
                f"  stop:0 rgb({r_t},{g_t},{b_t}),"
                f"  stop:1 rgb({r_b},{g_b},{b_b}));"
                f"color: {pt.accent_color};"
                f"border: none;"
                f"border-top: 1px solid rgba(255,255,255,{hair});"
                f"border-bottom: 2px solid {pt.accent_color};"
                f"padding: 0 8px;"
                "}"
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

    def _on_cost_visibility_changed(self, _visible: bool) -> None:
        """Flip PRICE + TOTAL columns on the data table, then rebuild the
        banner so its chip widths match the now-visible column set."""
        try:
            self._table._apply_cost_columns_visible()
        except Exception:
            pass
        if self._cat:
            self._build_banner(self._cat)

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
                # Copy the BASE_PT_ROLE marker so the model-column items
                # scale correctly at every zoom level
                base_pt = src.data(BASE_PT_ROLE)
                if base_pt is not None:
                    clone.setData(BASE_PT_ROLE, base_pt)
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

    # ── Zoom ─────────────────────────────────────────────────────────────────
    def apply_zoom(self, factor: float) -> None:
        """Professional content-aware zoom.

        Column widths are the MAX of three candidates at the active font:
            1. Proportionally-scaled base width (the design target)
            2. Widest header label + padding (so headers are ALWAYS visible)
            3. Widest data cell text + padding (so numbers/names aren't clipped)

        This way at 50% the text is genuinely smaller, but every header and
        every cell stays fully readable — no characters are cut off.
        """
        from app.services.zoom_service import ZOOM
        from PyQt6.QtGui import QFont, QFontMetrics

        mtx = self._table
        model_tbl = self._model_table

        body_pt = ZOOM.scale(11, minimum=6)
        header_pt = ZOOM.scale(10, minimum=6)
        body_font = QFont("Segoe UI", body_pt)
        header_font = QFont("Segoe UI", header_pt, QFont.Weight.Bold)

        # Measurers — use the NEW fonts
        fm_header = QFontMetrics(header_font)
        fm_body = QFontMetrics(body_font)

        # Padding scales with font so small fonts don't get oversized gaps
        hdr_pad = max(6, int(round(header_pt * 1.4)))   # horizontal (each side)
        hdr_vpad = max(3, int(round(header_pt * 0.5)))  # vertical
        body_pad = max(4, int(round(body_pt * 1.0)))

        # CRITICAL: app-wide QSS forces QHeaderView::section font-size 11px
        # and padding 10px 16px — those override setFont(). Widget-level
        # inline stylesheet has higher specificity than app stylesheet.
        hdr_qss = (
            f"QHeaderView::section {{ "
            f"font-size: {header_pt}pt; "
            f"font-weight: 700; "
            f"padding: {hdr_vpad}px {hdr_pad}px; "
            f"}}"
        )
        body_qss = (
            f"QTableWidget::item {{ padding: 2px {body_pad}px; }}"
        )

        mtx.setUpdatesEnabled(False)
        model_tbl.setUpdatesEnabled(False)
        try:
            mtx.setFont(body_font)
            mtx.horizontalHeader().setFont(header_font)
            mtx.horizontalHeader().setStyleSheet(hdr_qss)
            mtx.setStyleSheet(mtx.styleSheet() + body_qss)
            model_tbl.setFont(body_font)
            model_tbl.horizontalHeader().setFont(header_font)
            model_tbl.horizontalHeader().setStyleSheet(hdr_qss)
            model_tbl.setStyleSheet(model_tbl.styleSheet() + body_qss)

            # ── Scale every item's font by its stored BASE_PT_ROLE ──
            # Cache by (family, weight, base_pt) — dramatically reduces QFont
            # allocations. A typical matrix has ~1000 items but only ~5
            # unique (family, weight, base_pt) combinations.
            font_cache: dict[tuple, QFont] = {}

            def _get_scaled_font(cur_font: QFont, base_pt: int) -> QFont:
                key = (cur_font.family(), int(cur_font.weight()), int(base_pt))
                cached = font_cache.get(key)
                if cached is not None:
                    return cached
                new_pt = ZOOM.scale(int(base_pt), minimum=6)
                new_font = QFont(cur_font)
                new_font.setPointSize(new_pt)
                font_cache[key] = new_font
                return new_font

            def _scale_table_items(tbl):
                for r in range(tbl.rowCount()):
                    for c in range(tbl.columnCount()):
                        it = tbl.item(r, c)
                        if it is None:
                            continue
                        base_pt = it.data(BASE_PT_ROLE)
                        if base_pt is None:
                            continue
                        it.setFont(_get_scaled_font(it.font(), base_pt))
            _scale_table_items(mtx)
            _scale_table_items(model_tbl)

            # Per-side pad buffers that MATCH the inline QSS padding plus a
            # small safety margin for anti-alias / sort indicator space.
            hdr_side_pad = hdr_pad + 4    # matches "padding: Xpx <hdr_pad>px"
            body_side_pad = body_pad + 4  # matches "padding: 2px <body_pad>px"

            # ── Model column: fit widest item using its OWN scaled font ──
            # Each item (brand 12pt, model 11pt DemiBold, color 9pt) has a
            # different rendered size — we must measure with each item's
            # actual font, not the widget default.
            longest_name_w = 0
            for r in range(model_tbl.rowCount()):
                it = model_tbl.item(r, 0)
                if it and it.text():
                    w = QFontMetrics(it.font()).horizontalAdvance(it.text())
                    if w > longest_name_w:
                        longest_name_w = w
            model_hdr_txt = t("disp_col_model")
            model_hdr_w = fm_header.horizontalAdvance(model_hdr_txt) + hdr_side_pad * 2
            model_w = max(
                ZOOM.scale(_COL_W["model"], minimum=60),
                longest_name_w + body_side_pad * 2,
                model_hdr_w,
            )
            mtx.setColumnWidth(0, model_w)
            model_tbl.setColumnWidth(0, model_w)
            model_tbl.setFixedWidth(model_w + 2)

            # ── Data columns: fit widest header label + widest cell text ──
            if mtx._cat:
                hdr_labels = {
                    _SUB_MIN:   t("col_stamm_zahl"),
                    _SUB_BB:    t("col_best_bung"),
                    _SUB_STOCK: t("disp_col_stock"),
                    _SUB_ORDER: t("col_inventur"),
                    _SUB_SELL:  "SELL",
                    _SUB_PRICE: "COST",
                    _SUB_TOTAL: "TOTAL",
                }
                base_widths = {
                    _SUB_MIN:   _COL_W["stamm"],
                    _SUB_BB:    _COL_W["bestbung"],
                    _SUB_STOCK: _COL_W["stock"],
                    _SUB_ORDER: _COL_W["inventur"],
                    _SUB_SELL:  _COL_W["sell"],
                    _SUB_PRICE: _COL_W["price"],
                    _SUB_TOTAL: _COL_W["total"],
                }
                min_widths = {_SUB_MIN: 44, _SUB_BB: 44, _SUB_STOCK: 34,
                              _SUB_ORDER: 36, _SUB_SELL: 38,
                              _SUB_PRICE: 38, _SUB_TOTAL: 50}

                for ti in range(len(mtx._cat.part_types)):
                    b = _base(ti)
                    for c in range(_COLS_PER_TYPE):
                        col = b + c
                        # Header text width at the ACTUAL rendered font
                        hdr_w = fm_header.horizontalAdvance(hdr_labels[c]) + hdr_side_pad * 2
                        # Widest data text — measure using each cell's own font
                        # (cells use _FONT_MONO or _FONT_DATA with different sizes)
                        data_w = 0
                        for r in range(mtx.rowCount()):
                            item = mtx.item(r, col)
                            if item and item.text():
                                iw = QFontMetrics(item.font()).horizontalAdvance(item.text())
                                if iw > data_w:
                                    data_w = iw
                        data_w += body_side_pad * 2
                        w = max(
                            ZOOM.scale(base_widths[c], minimum=min_widths[c]),
                            hdr_w,
                            data_w,
                        )
                        mtx.setColumnWidth(col, w)

            # ── Header height: must fit the header font + its vertical padding ──
            hdr_h = max(fm_header.height() + hdr_vpad * 2 + 4,
                        ZOOM.scale(30, minimum=18))
            mtx.horizontalHeader().setFixedHeight(hdr_h)
            model_tbl.horizontalHeader().setFixedHeight(hdr_h)

            # ── Row heights — must fit the body font ──
            min_row = fm_body.height() + 6
            model_row_h = max(min_row, ZOOM.scale(48, minimum=min_row))
            color_row_h = max(min_row, ZOOM.scale(36, minimum=min_row))
            brand_row_h = max(min_row, ZOOM.scale(32, minimum=min_row))
            for r in range(mtx.rowCount()):
                cur_h = mtx.rowHeight(r)
                if cur_h <= 5:
                    continue  # separator row
                if cur_h == 32:
                    mtx.setRowHeight(r, brand_row_h)
                    if r < model_tbl.rowCount():
                        model_tbl.setRowHeight(r, brand_row_h)
                    continue
                is_color_row = cur_h < 42
                h = color_row_h if is_color_row else model_row_h
                mtx.setRowHeight(r, h)
                if r < model_tbl.rowCount():
                    model_tbl.setRowHeight(r, h)

            # ── Banner (part-type labels above columns) ──
            banner_pt = ZOOM.scale(10, minimum=6)
            banner_h = max(QFontMetrics(QFont("Segoe UI", banner_pt)).height() + 8,
                           ZOOM.scale(30, minimum=16))
            if hasattr(self, "_banner_scroll"):
                self._banner_scroll.setFixedHeight(banner_h)
                self._banner_spacer.setFixedWidth(model_w + 2)
                self._banner_spacer.setFixedHeight(banner_h)
            if hasattr(self, "_banner_labels"):
                banner_total_w = 0
                for i, lbl in enumerate(self._banner_labels):
                    if not mtx._cat or i >= len(mtx._cat.part_types):
                        continue
                    w = _type_visible_width(mtx, i)
                    lbl.setFixedWidth(w)
                    lbl.setFixedHeight(banner_h)
                    banner_total_w += w
                    lbl.setFont(QFont("Segoe UI", banner_pt, QFont.Weight.Bold))
                if hasattr(self, "_banner_inner") and banner_total_w > 0:
                    self._banner_inner.setFixedWidth(banner_total_w)
                    self._banner_inner.setFixedHeight(banner_h)
        finally:
            mtx.setUpdatesEnabled(True)
            model_tbl.setUpdatesEnabled(True)

        mtx.viewport().update()
        model_tbl.viewport().update()
