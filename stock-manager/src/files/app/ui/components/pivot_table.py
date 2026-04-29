"""app/ui/components/pivot_table.py — Professional brand-separated valuation.

Layout stack:
    1. Filter bar        — Brand combo · Category combo · Clear filters
    2. Brand chip row    — 3 per row summary
    3. Brand cards       — one card per brand with:
                            · banner (brand name + totals)
                            · per-category sub-section with header bar
                            · part-type rows with share bar
                            · category subtotal row
                            · brand subtotal strip
    4. Grand total strip — emerald gradient
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QSizePolicy, QComboBox, QToolButton,
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QFont, QColor, QPainter

from app.core.theme import THEME
from app.core.config import ShopConfig


_BRAND_PALETTE = [
    "#10B981", "#3B82F6", "#F59E0B", "#8B5CF6", "#EF4444",
    "#06B6D4", "#EC4899", "#84CC16", "#F97316", "#14B8A6",
]


# ── Helpers ────────────────────────────────────────────────────────────────

def _rgba(hex6: str, alpha: int) -> str:
    h = hex6.lstrip("#")
    return (f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},"
            f"{int(h[4:6], 16)},{alpha})")


class _ShareBar(QWidget):
    """Thin rounded fill bar for showing a 0-100 % share."""

    def __init__(self, parent=None, *, color: str = "#10B981") -> None:
        super().__init__(parent)
        self._pct = 0.0
        self._color = color
        self.setFixedHeight(6)
        self.setMinimumWidth(60)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_pct(self, pct: float, color: str = "") -> None:
        self._pct = max(0.0, min(100.0, float(pct)))
        if color:
            self._color = color
        self.update()

    def paintEvent(self, _evt) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w, h = self.width(), self.height()
        r = h / 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(THEME.tokens.border))
        p.drawRoundedRect(QRectF(0, 0, w, h), r, r)
        if self._pct > 0:
            fw = max(r * 2, w * (self._pct / 100.0))
            p.setBrush(QColor(self._color))
            p.drawRoundedRect(QRectF(0, 0, fw, h), r, r)
        p.end()


# ── Filter bar ─────────────────────────────────────────────────────────────

class _FilterBar(QFrame):
    """Professional filter row — brand + category combos + clear button."""

    changed = pyqtSignal(str, str)       # brand, category (either "All")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("valuation_filter_bar")
        self.setFixedHeight(52)

        tk = THEME.tokens
        self.setStyleSheet(
            f"QFrame#valuation_filter_bar {{"
            f"  background: {tk.card};"
            f"  border: 1px solid {tk.border};"
            f"  border-radius: 10px;"
            f"}}"
            f"QLabel.flt_lbl {{"
            f"  color: {tk.t4}; font-size: 10px; font-weight: 800;"
            f"  letter-spacing: 0.08em;"
            f"}}"
            f"QComboBox.flt_combo {{"
            f"  background: {tk.card2}; color: {tk.t1};"
            f"  border: 1px solid {tk.border}; border-radius: 6px;"
            f"  padding: 4px 10px; min-height: 28px; min-width: 160px;"
            f"  font-size: 11px; font-weight: 600;"
            f"}}"
            f"QComboBox.flt_combo:hover {{"
            f"  border-color: {tk.green};"
            f"}}"
            f"QComboBox.flt_combo::drop-down {{"
            f"  border: none; width: 22px;"
            f"}}"
            f"QToolButton#flt_clear {{"
            f"  background: transparent; color: {tk.t3};"
            f"  border: 1px dashed {tk.border2};"
            f"  border-radius: 6px; padding: 4px 12px;"
            f"  font-size: 11px; font-weight: 600;"
            f"}}"
            f"QToolButton#flt_clear:hover {{"
            f"  background: {tk.card2}; color: {tk.t1};"
            f"  border-color: {tk.t3};"
            f"}}"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(10)

        # Brand picker
        b_lbl = QLabel("BRAND"); b_lbl.setProperty("class", "flt_lbl")
        b_lbl.setStyleSheet(f"color: {tk.t4}; font-size: 10px;"
                              f" font-weight: 800; letter-spacing: 0.08em;")
        self._brand_combo = QComboBox()
        self._brand_combo.setProperty("class", "flt_combo")
        self._brand_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self._brand_combo.currentIndexChanged.connect(self._emit)
        lay.addWidget(b_lbl)
        lay.addWidget(self._brand_combo)

        # Small divider
        divider = QFrame(); divider.setFixedSize(1, 20)
        divider.setStyleSheet(f"background: {tk.border};")
        lay.addSpacing(6); lay.addWidget(divider); lay.addSpacing(6)

        # Category picker
        c_lbl = QLabel("CATEGORY"); c_lbl.setProperty("class", "flt_lbl")
        c_lbl.setStyleSheet(f"color: {tk.t4}; font-size: 10px;"
                              f" font-weight: 800; letter-spacing: 0.08em;")
        self._cat_combo = QComboBox()
        self._cat_combo.setProperty("class", "flt_combo")
        self._cat_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cat_combo.currentIndexChanged.connect(self._emit)
        lay.addWidget(c_lbl)
        lay.addWidget(self._cat_combo)

        lay.addStretch()

        # Active filter indicator + clear
        self._active_badge = QLabel("")
        self._active_badge.setStyleSheet(
            f"color: {tk.green}; font-size: 10px; font-weight: 700;"
        )
        lay.addWidget(self._active_badge)

        self._clear_btn = QToolButton()
        self._clear_btn.setObjectName("flt_clear")
        self._clear_btn.setText("✕  Clear filters")
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.clicked.connect(self._clear)
        lay.addWidget(self._clear_btn)

    def populate(self, brands: list[str], categories: list[str]) -> None:
        # Remember selections to restore after rebuild
        prev_b = self._brand_combo.currentText()
        prev_c = self._cat_combo.currentText()
        self._brand_combo.blockSignals(True)
        self._cat_combo.blockSignals(True)
        self._brand_combo.clear()
        self._cat_combo.clear()
        self._brand_combo.addItem("All brands")
        for b in brands:
            self._brand_combo.addItem(b)
        self._cat_combo.addItem("All categories")
        for c in categories:
            self._cat_combo.addItem(c)
        # Restore if still valid
        if prev_b:
            i = self._brand_combo.findText(prev_b)
            if i >= 0:
                self._brand_combo.setCurrentIndex(i)
        if prev_c:
            i = self._cat_combo.findText(prev_c)
            if i >= 0:
                self._cat_combo.setCurrentIndex(i)
        self._brand_combo.blockSignals(False)
        self._cat_combo.blockSignals(False)
        self._update_badge()

    def _emit(self) -> None:
        self._update_badge()
        brand = (self._brand_combo.currentText()
                 if self._brand_combo.currentIndex() > 0 else "All")
        cat = (self._cat_combo.currentText()
               if self._cat_combo.currentIndex() > 0 else "All")
        self.changed.emit(brand, cat)

    def _clear(self) -> None:
        self._brand_combo.blockSignals(True)
        self._cat_combo.blockSignals(True)
        self._brand_combo.setCurrentIndex(0)
        self._cat_combo.setCurrentIndex(0)
        self._brand_combo.blockSignals(False)
        self._cat_combo.blockSignals(False)
        self._update_badge()
        self.changed.emit("All", "All")

    def _update_badge(self) -> None:
        active = 0
        if self._brand_combo.currentIndex() > 0:
            active += 1
        if self._cat_combo.currentIndex() > 0:
            active += 1
        if active:
            self._active_badge.setText(
                f"● {active} filter{'s' if active != 1 else ''} active"
            )
        else:
            self._active_badge.setText("")


# ── Brand summary chip ─────────────────────────────────────────────────────

class _BrandChip(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, brand: str, units: int, value: float,
                 pct: float, color: str, parent=None) -> None:
        super().__init__(parent)
        self._brand = brand
        self.setObjectName("valuation_brand_chip")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                            QSizePolicy.Policy.Fixed)
        self.setFixedHeight(88)

        tk = THEME.tokens
        cfg = ShopConfig.get()
        self.setStyleSheet(
            f"QFrame#valuation_brand_chip {{"
            f"  background: {tk.card};"
            f"  border: 1px solid {tk.border};"
            f"  border-left: 4px solid {color};"
            f"  border-radius: 8px;"
            f"}}"
            f"QFrame#valuation_brand_chip:hover {{"
            f"  border-color: {color};"
            f"  background: {_rgba(color, 16)};"
            f"}}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(3)

        top = QHBoxLayout(); top.setSpacing(6)
        name = QLabel(brand.upper())
        name.setStyleSheet(
            f"color: {color}; font-size: 11px; font-weight: 800;"
            f" letter-spacing: 0.10em;"
        )
        top.addWidget(name); top.addStretch()
        units_lbl = QLabel(f"{units:,} units")
        units_lbl.setStyleSheet(
            f"color: {tk.t3}; font-size: 10px; font-weight: 600;"
        )
        top.addWidget(units_lbl)
        lay.addLayout(top)

        val_lbl = QLabel(cfg.format_currency(f"{value:,.2f}"))
        val_lbl.setStyleSheet(
            f"color: {tk.t1}; font-size: 20px; font-weight: 800;"
        )
        lay.addWidget(val_lbl)

        bar_row = QHBoxLayout(); bar_row.setSpacing(8)
        bar = _ShareBar(color=color); bar.set_pct(pct)
        bar_row.addWidget(bar, 1)
        pct_lbl = QLabel(f"{pct:.1f}%")
        pct_lbl.setStyleSheet(
            f"color: {tk.t4}; font-size: 10px; font-weight: 700;"
            f" font-family: 'JetBrains Mono', monospace;"
        )
        pct_lbl.setFixedWidth(44)
        pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight
                              | Qt.AlignmentFlag.AlignVCenter)
        bar_row.addWidget(pct_lbl)
        lay.addLayout(bar_row)

    def mousePressEvent(self, evt):
        if evt.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._brand)
        super().mousePressEvent(evt)


# ── Part-type row inside a category group ──────────────────────────────────

class _PartTypeRow(QFrame):
    clicked = pyqtSignal(int)

    def __init__(self, pt_id: int, pt_name: str,
                 units: int, value: float, share: float, color: str,
                 parent=None) -> None:
        super().__init__(parent)
        self._pt_id = pt_id
        self.setObjectName("valuation_pt_row")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(32)

        tk = THEME.tokens
        cfg = ShopConfig.get()
        self.setStyleSheet(
            f"QFrame#valuation_pt_row {{ background: transparent; }}"
            f"QFrame#valuation_pt_row:hover {{"
            f"  background: {_rgba(color, 22)};"
            f"}}"
        )

        lay = QHBoxLayout(self)
        lay.setContentsMargins(26, 3, 16, 3)
        lay.setSpacing(10)

        # Name
        name = QLabel(pt_name)
        name.setStyleSheet(
            f"color: {tk.t1}; font-size: 11px; font-weight: 600;"
        )
        lay.addWidget(name, 3)

        # Units
        units_lbl = QLabel(f"{units:,}")
        units_lbl.setFixedWidth(56)
        units_lbl.setStyleSheet(
            f"color: {tk.t2}; font-size: 11px; font-weight: 700;"
            f" font-family: 'JetBrains Mono', monospace;"
        )
        units_lbl.setAlignment(Qt.AlignmentFlag.AlignRight
                                | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(units_lbl)

        # Avg price
        avg = (value / units) if units else 0
        avg_lbl = QLabel(cfg.format_currency(f"{avg:,.2f}") if units else "—")
        avg_lbl.setFixedWidth(82)
        avg_lbl.setStyleSheet(
            f"color: {tk.t3}; font-size: 10px; font-weight: 500;"
        )
        avg_lbl.setAlignment(Qt.AlignmentFlag.AlignRight
                              | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(avg_lbl)

        # Value
        val_lbl = QLabel(cfg.format_currency(f"{value:,.2f}"))
        val_lbl.setFixedWidth(100)
        val_lbl.setStyleSheet(
            f"color: {tk.t1}; font-size: 11px; font-weight: 700;"
        )
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight
                              | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(val_lbl)

        # Share bar
        bar = _ShareBar(color=color); bar.set_pct(share)
        bar.setFixedWidth(90)
        lay.addWidget(bar)

        # Share %
        pct_lbl = QLabel(f"{share:.0f}%")
        pct_lbl.setFixedWidth(36)
        pct_lbl.setStyleSheet(
            f"color: {tk.t4}; font-size: 10px; font-weight: 600;"
            f" font-family: 'JetBrains Mono', monospace;"
        )
        pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight
                              | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(pct_lbl)

    def mousePressEvent(self, evt):
        if evt.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._pt_id)
        super().mousePressEvent(evt)


# ── Brand card ─────────────────────────────────────────────────────────────

class _BrandCard(QFrame):
    row_clicked = pyqtSignal(str, int)

    def __init__(self, brand: str,
                 grouped_rows: list[tuple[str, list[dict]]],
                 brand_units: int, brand_value: float,
                 grand_value: float, color: str, parent=None) -> None:
        super().__init__(parent)
        self._brand = brand
        self.setObjectName("valuation_brand_card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                            QSizePolicy.Policy.Fixed)

        tk = THEME.tokens
        cfg = ShopConfig.get()
        self.setStyleSheet(
            f"QFrame#valuation_brand_card {{"
            f"  background: {tk.card};"
            f"  border: 1px solid {tk.border};"
            f"  border-radius: 10px;"
            f"}}"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Brand banner ──
        banner = QFrame(); banner.setFixedHeight(60)
        banner.setStyleSheet(
            f"background: {_rgba(color, 28)};"
            f" border-top-left-radius: 10px;"
            f" border-top-right-radius: 10px;"
            f" border-bottom: 1px solid {tk.border};"
        )
        bl = QHBoxLayout(banner)
        bl.setContentsMargins(16, 10, 16, 10)
        bl.setSpacing(12)

        dot = QFrame(); dot.setFixedSize(8, 28)
        dot.setStyleSheet(f"background: {color}; border-radius: 4px;")
        bl.addWidget(dot)

        # Name stack — use a parented QFrame so the QVBoxLayout actually
        # computes geometry. Plain QWidget().setLayout() was leaving the
        # inner labels at (0,0) which caused the overlap bug.
        name_container = QFrame()
        name_stack = QVBoxLayout(name_container)
        name_stack.setContentsMargins(0, 0, 0, 0)
        name_stack.setSpacing(2)
        brand_lbl = QLabel(brand.upper())
        brand_lbl.setStyleSheet(
            f"color: {tk.t1}; font-size: 16px; font-weight: 800;"
            f" letter-spacing: 0.06em; background: transparent;"
        )
        name_stack.addWidget(brand_lbl)
        n_pts = sum(len(rows) for _, rows in grouped_rows)
        n_cats = len(grouped_rows)
        sub_lbl = QLabel(
            f"{n_cats} categor{'y' if n_cats == 1 else 'ies'}  ·  "
            f"{n_pts} part type{'' if n_pts == 1 else 's'}  ·  "
            f"{brand_units:,} units"
        )
        sub_lbl.setStyleSheet(
            f"color: {tk.t3}; font-size: 10px; background: transparent;"
        )
        name_stack.addWidget(sub_lbl)
        bl.addWidget(name_container)

        bl.addStretch()

        pct = (brand_value / grand_value * 100) if grand_value else 0
        total_container = QFrame()
        total_stack = QVBoxLayout(total_container)
        total_stack.setContentsMargins(0, 0, 0, 0)
        total_stack.setSpacing(2)
        total_lbl = QLabel(cfg.format_currency(f"{brand_value:,.2f}"))
        total_lbl.setStyleSheet(
            f"color: {color}; font-size: 19px; font-weight: 800;"
            f" background: transparent;"
        )
        total_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        total_stack.addWidget(total_lbl)
        total_sub = QLabel(f"{pct:.1f}% of total stock value")
        total_sub.setStyleSheet(
            f"color: {tk.t4}; font-size: 10px; background: transparent;"
        )
        total_sub.setAlignment(Qt.AlignmentFlag.AlignRight)
        total_stack.addWidget(total_sub)
        bl.addWidget(total_container)
        root.addWidget(banner)

        # ── Column header row ──
        col_hdr = QFrame(); col_hdr.setFixedHeight(24)
        col_hdr.setStyleSheet(
            f"background: {tk.card2};"
            f" border-bottom: 1px solid {tk.border};"
        )
        hl = QHBoxLayout(col_hdr)
        hl.setContentsMargins(26, 0, 16, 0)
        hl.setSpacing(10)

        def _col(text: str, w_px: int | None, right: bool = False,
                 stretch: int = 0):
            l = QLabel(text)
            l.setStyleSheet(
                f"color: {tk.t4}; font-size: 9px; font-weight: 800;"
                f" letter-spacing: 0.10em;"
            )
            if w_px is not None:
                l.setFixedWidth(w_px)
            l.setAlignment(Qt.AlignmentFlag.AlignRight if right
                            else Qt.AlignmentFlag.AlignLeft)
            return l, stretch

        for (text, w_px, right, stretch) in [
            ("PART TYPE", None, False, 3),
            ("UNITS", 56, True, 0),
            ("AVG PRICE", 82, True, 0),
            ("STOCK VALUE", 100, True, 0),
            ("SHARE", 90, False, 0),
            ("%", 36, True, 0),
        ]:
            lab, st = _col(text, w_px, right, stretch)
            if st:
                hl.addWidget(lab, st)
            else:
                hl.addWidget(lab)
        root.addWidget(col_hdr)

        # ── Grouped rows: one sub-section per category ──
        brand_total_for_share = brand_value or 1
        for gi, (cat_name, rows) in enumerate(grouped_rows):
            # Category header (uppercase, thin emerald underline)
            cat_units = sum(int(r.get("units") or 0) for r in rows)
            cat_value = sum(float(r.get("value") or 0) for r in rows)

            cat_hdr = QFrame(); cat_hdr.setFixedHeight(28)
            cat_hdr.setStyleSheet(
                f"background: {_rgba(color, 10)};"
                f" border-top: {'1px solid ' + tk.border if gi > 0 else 'none'};"
            )
            chl = QHBoxLayout(cat_hdr)
            chl.setContentsMargins(16, 0, 16, 0)
            chl.setSpacing(8)
            # Accent bar + label
            accent = QFrame(); accent.setFixedSize(3, 14)
            accent.setStyleSheet(f"background: {color}; border-radius: 2px;")
            chl.addWidget(accent)
            cname = QLabel(cat_name.upper())
            cname.setStyleSheet(
                f"color: {tk.t2}; font-size: 10px; font-weight: 800;"
                f" letter-spacing: 0.12em;"
            )
            chl.addWidget(cname)
            chl.addStretch()
            cmeta = QLabel(
                f"{len(rows)} · {cat_units:,} units · "
                f"{cfg.format_currency(f'{cat_value:,.2f}')}"
            )
            cmeta.setStyleSheet(
                f"color: {tk.t4}; font-size: 10px; font-weight: 600;"
                f" font-family: 'JetBrains Mono', monospace;"
            )
            chl.addWidget(cmeta)
            root.addWidget(cat_hdr)

            # Rows
            sorted_rows = sorted(rows,
                                  key=lambda r: float(r.get("value") or 0),
                                  reverse=True)
            for ri, row in enumerate(sorted_rows):
                share = (float(row.get("value") or 0)
                         / brand_total_for_share * 100)
                r = _PartTypeRow(
                    pt_id=int(row["pt_id"]),
                    pt_name=str(row.get("pt_name") or "—"),
                    units=int(row.get("units") or 0),
                    value=float(row.get("value") or 0),
                    share=share,
                    color=color,
                )
                r.clicked.connect(
                    lambda pt_id, b=brand: self.row_clicked.emit(b, int(pt_id))
                )
                root.addWidget(r)
                if ri < len(sorted_rows) - 1:
                    sep = QFrame(); sep.setFixedHeight(1)
                    sep.setStyleSheet(f"background: {tk.border};")
                    root.addWidget(sep)

            # Category subtotal strip (narrow, right-aligned)
            cat_sub = QFrame(); cat_sub.setFixedHeight(26)
            cat_sub.setStyleSheet(
                f"background: {_rgba(color, 8)};"
                f" border-top: 1px dashed {tk.border};"
            )
            csl = QHBoxLayout(cat_sub)
            csl.setContentsMargins(26, 0, 16, 0)
            csl.setSpacing(10)
            csl_lbl = QLabel(f"Subtotal · {cat_name}")
            csl_lbl.setStyleSheet(
                f"color: {tk.t3}; font-size: 10px; font-weight: 700;"
                f" font-style: italic;"
            )
            csl.addWidget(csl_lbl)
            csl.addStretch()
            csub_val = QLabel(
                f"{cat_units:,} units  ·  "
                f"{cfg.format_currency(f'{cat_value:,.2f}')}"
            )
            csub_val.setStyleSheet(
                f"color: {tk.t1}; font-size: 10px; font-weight: 800;"
                f" font-family: 'JetBrains Mono', monospace;"
            )
            csl.addWidget(csub_val)
            root.addWidget(cat_sub)

        # ── Brand subtotal strip (main) ──
        footer = QFrame(); footer.setFixedHeight(40)
        footer.setStyleSheet(
            f"background: {_rgba(color, 22)};"
            f" border-top: 1px solid {tk.border};"
            f" border-bottom-left-radius: 10px;"
            f" border-bottom-right-radius: 10px;"
        )
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(16, 0, 16, 0)
        fl.setSpacing(10)
        total_title = QLabel(f"SUBTOTAL · {brand.upper()}")
        total_title.setStyleSheet(
            f"color: {color}; font-size: 11px; font-weight: 800;"
            f" letter-spacing: 0.10em;"
        )
        fl.addWidget(total_title)
        fl.addStretch()
        total_val = QLabel(
            f"{brand_units:,} units  ·  "
            f"{cfg.format_currency(f'{brand_value:,.2f}')}"
        )
        total_val.setStyleSheet(
            f"color: {tk.t1}; font-size: 13px; font-weight: 800;"
            f" font-family: 'JetBrains Mono', monospace;"
        )
        fl.addWidget(total_val)
        root.addWidget(footer)


# ── Main widget ────────────────────────────────────────────────────────────

class PivotTable(QWidget):
    """Brand-separated valuation with filters and per-category grouping."""

    cell_clicked_drilldown = pyqtSignal(str, int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("valuation_root")
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                            QSizePolicy.Policy.Preferred)

        self._data: dict | None = None
        self._filter_brand = "All"
        self._filter_category = "All"

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(14)

        # Filter bar is persistent — lives outside the dynamic section
        self._filter_bar = _FilterBar()
        self._filter_bar.changed.connect(self._on_filter_changed)
        self._root.addWidget(self._filter_bar)

        # Dynamic content goes into this container; easy to clear/rebuild
        self._body = QWidget()
        self._body_lay = QVBoxLayout(self._body)
        self._body_lay.setContentsMargins(0, 0, 0, 0)
        self._body_lay.setSpacing(14)
        self._root.addWidget(self._body)

        self._placeholder()

    # ── Public API ─────────────────────────────────────────────────────────

    def set_data(self, data: dict) -> None:
        self._data = data
        brands = list(data.get("brands", []))
        # Extract unique category names in declared order
        cat_seen = set(); cats = []
        for (cat_id, cat_name, pt_id, pt_name) in data.get("part_types", []):
            if cat_id not in cat_seen:
                cat_seen.add(cat_id); cats.append(cat_name)
        self._filter_bar.populate(brands, cats)
        self._render()

    def apply_theme(self) -> None:
        """Re-render the pivot view on theme switch.

        ``_BrandChip`` / ``_BrandCard`` / ``_PartTypeRow`` / ``_FilterBar``
        all bake ``tk.X`` colours into inline ``setStyleSheet(f"...")``
        strings during construction (46 inline-style call sites total
        across the module). Rather than threading an ``apply_theme`` into
        each subclass, we just re-run ``_render()`` against the cached
        ``self._data`` — identical to the data-cached re-render approach
        used by ``MatrixTab.apply_theme`` (see 2.5.8). No DB query, no
        network call, no async worker — just widget rebuilding from
        already-loaded data with the new ``THEME.tokens``.
        """
        if self._data is None:
            return  # never populated yet — nothing to render
        try:
            self._render()
        except Exception:
            import logging as _lg
            _lg.getLogger(__name__).exception(
                "PivotTable.apply_theme re-render failed"
            )

    # ── Filtering ──────────────────────────────────────────────────────────

    def _on_filter_changed(self, brand: str, category: str) -> None:
        self._filter_brand = brand
        self._filter_category = category
        self._render()

    # ── Render ─────────────────────────────────────────────────────────────

    def _render(self) -> None:
        self._clear_body()
        if not self._data:
            self._placeholder()
            return

        brands = list(self._data.get("brands", []))
        part_types = list(self._data.get("part_types", []))
        cells = self._data.get("cells", {})

        # Apply brand + category filters
        active_brands = (brands if self._filter_brand == "All"
                         else [self._filter_brand])
        active_cat_ids = None
        if self._filter_category != "All":
            active_cat_ids = {cat_id
                              for (cat_id, cat_name, _pt, _nm) in part_types
                              if cat_name == self._filter_category}

        # Build pt lookup
        pt_meta: dict[int, tuple] = {}    # pt_id -> (cat_id, cat_name, pt_name)
        for (cat_id, cat_name, pt_id, pt_name) in part_types:
            if active_cat_ids is not None and cat_id not in active_cat_ids:
                continue
            pt_meta[pt_id] = (cat_id, cat_name, pt_name)

        # Aggregate per-brand totals after filter. Include zero-stock
        # (brand, part_type) entries so the full inventory scope is
        # visible — the user wants to see brands and categories that
        # exist in the system even when their stock is currently 0.
        per_brand: dict[str, dict] = {}
        for brand in active_brands:
            b_units = 0; b_value = 0.0
            rows: list[dict] = []
            for pt_id, meta in pt_meta.items():
                cell = cells.get((brand, pt_id))
                if cell is None:
                    continue   # brand simply has no row for this pt
                u = int(cell.get("units") or 0)
                v = float(cell.get("value") or 0)
                cat_id, cat_name, pt_name = meta
                b_units += u; b_value += v
                rows.append({
                    "pt_id": pt_id, "pt_name": pt_name,
                    "cat_id": cat_id, "cat_name": cat_name,
                    "units": u, "value": v,
                })
            if rows:
                per_brand[brand] = {"units": b_units, "value": b_value,
                                    "rows": rows}

        if not per_brand:
            self._empty_filter_message()
            return

        # Order brands by value desc
        ordered = sorted(per_brand.items(),
                          key=lambda kv: kv[1]["value"], reverse=True)
        total_value = sum(v["value"] for _, v in ordered)
        total_units = sum(v["units"] for _, v in ordered)
        brand_color = {b: _BRAND_PALETTE[i % len(_BRAND_PALETTE)]
                       for i, (b, _) in enumerate(ordered)}

        # ── Top chips row ──
        chips = QFrame()
        gl = QGridLayout(chips)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.setHorizontalSpacing(10); gl.setVerticalSpacing(10)
        cols = 3 if len(ordered) >= 3 else max(1, len(ordered))
        for i, (brand, bt) in enumerate(ordered):
            pct = (bt["value"] / total_value * 100) if total_value else 0
            chip = _BrandChip(brand, bt["units"], bt["value"], pct,
                                brand_color[brand])
            chip.clicked.connect(self._on_chip_clicked)
            gl.addWidget(chip, i // cols, i % cols)
        self._body_lay.addWidget(chips)

        # ── Per-brand cards ──
        for brand, bt in ordered:
            # Group rows by category
            groups: dict[tuple[int, str], list[dict]] = {}
            order_key: dict[tuple[int, str], int] = {}
            for row in bt["rows"]:
                key = (row["cat_id"], row["cat_name"])
                groups.setdefault(key, []).append(row)
                order_key.setdefault(key, len(order_key))
            grouped = sorted(groups.items(), key=lambda kv: order_key[kv[0]])
            grouped_for_card = [(cat_name, rows)
                                for (cat_id, cat_name), rows in grouped]

            card = _BrandCard(
                brand=brand,
                grouped_rows=grouped_for_card,
                brand_units=bt["units"],
                brand_value=bt["value"],
                grand_value=total_value,
                color=brand_color[brand],
            )
            card.row_clicked.connect(self._on_row_clicked)
            self._body_lay.addWidget(card)

        # ── Grand total strip ──
        self._body_lay.addWidget(
            self._grand_total_strip(total_units, total_value, len(ordered))
        )
        self._body_lay.addStretch(1)

    # ── Section builders ───────────────────────────────────────────────────

    def _grand_total_strip(self, units: int, value: float,
                             brand_count: int) -> QFrame:
        tk = THEME.tokens
        cfg = ShopConfig.get()
        strip = QFrame()
        strip.setObjectName("valuation_grand_total")
        strip.setFixedHeight(68)
        strip.setStyleSheet(
            f"QFrame#valuation_grand_total {{"
            f"  background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            f"                              stop:0 {tk.green},"
            f"                              stop:1 {_rgba(tk.green, 180)});"
            f"  border-radius: 10px;"
            f"}}"
        )
        lay = QHBoxLayout(strip)
        lay.setContentsMargins(20, 10, 20, 10)
        lay.setSpacing(12)

        left_container = QFrame()
        left_container.setStyleSheet("background: transparent;")
        left = QVBoxLayout(left_container)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(2)
        lab = QLabel("GRAND TOTAL")
        lab.setStyleSheet(
            "color: rgba(255,255,255,0.92); font-size: 11px;"
            " font-weight: 800; letter-spacing: 0.12em;"
            " background: transparent;"
        )
        left.addWidget(lab)
        filter_note = ""
        if self._filter_brand != "All" or self._filter_category != "All":
            parts = []
            if self._filter_brand != "All":
                parts.append(f"brand: {self._filter_brand}")
            if self._filter_category != "All":
                parts.append(f"category: {self._filter_category}")
            filter_note = "  ·  filtered (" + ", ".join(parts) + ")"
        sub = QLabel(
            f"{brand_count} brand{'s' if brand_count != 1 else ''}  ·  "
            f"{units:,} units in stock{filter_note}"
        )
        sub.setStyleSheet(
            "color: rgba(255,255,255,0.78); font-size: 10px;"
            " background: transparent;"
        )
        left.addWidget(sub)
        lay.addWidget(left_container)
        lay.addStretch()

        val = QLabel(cfg.format_currency(f"{value:,.2f}"))
        val.setStyleSheet(
            "color: white; font-size: 30px; font-weight: 900;"
            " background: transparent;"
        )
        lay.addWidget(val)
        return strip

    def _empty_filter_message(self) -> None:
        tk = THEME.tokens
        empty = QLabel(
            "No stock matches the current filters.\n"
            "Clear filters to see all brands and categories."
        )
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.setStyleSheet(
            f"color: {tk.t4}; font-size: 12px;"
            f" background: {tk.card2}; border: 1px dashed {tk.border2};"
            f" border-radius: 10px; padding: 24px;"
        )
        self._body_lay.addWidget(empty)

    def _placeholder(self) -> None:
        tk = THEME.tokens
        empty = QLabel("Valuation data appears once stock with prices is added.")
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.setStyleSheet(
            f"color: {tk.t4}; font-size: 12px;"
            f" background: {tk.card2}; border: 1px dashed {tk.border2};"
            f" border-radius: 10px; padding: 24px;"
        )
        empty.setMinimumHeight(120)
        self._body_lay.addWidget(empty)

    # ── Helpers ────────────────────────────────────────────────────────────

    def _clear_body(self) -> None:
        while self._body_lay.count():
            it = self._body_lay.takeAt(0)
            w = it.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def _on_chip_clicked(self, brand: str) -> None:
        self.cell_clicked_drilldown.emit(brand, 0)

    def _on_row_clicked(self, brand: str, pt_id: int) -> None:
        self.cell_clicked_drilldown.emit(brand, pt_id)
