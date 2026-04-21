"""
app/ui/pages/inventory_page.py — Main inventory page (dashboard + table + detail bar).

Each top section has a slim collapse header.  When a section is hidden the
product table (stretch=1) automatically expands to fill the freed space.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal

from app.core.i18n import t
from app.core.theme import THEME, _rgba
from app.repositories.item_repo import ItemRepository
from app.models.item import InventoryItem
from app.ui.components.dashboard_widget import DashboardWidget
from app.ui.components.filter_bar import FilterBar
from app.ui.components.product_table import ProductTable
from app.ui.components.product_detail_bar import ProductDetailBar

_item_repo = ItemRepository()


# ── Section Header ─────────────────────────────────────────────────────────────

class _SectionHeader(QWidget):
    """
    Slim clickable row: label on left, chevron toggle on right.
    Click anywhere on the row to expand / collapse.
    Emits toggled(bool) → True = expanded, False = collapsed.
    """

    toggled = pyqtSignal(bool)

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._expanded = True
        self._title = title
        self.setFixedHeight(24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 0, 6, 0)
        lay.setSpacing(4)

        self._lbl = QLabel(title.upper())
        self._lbl.setObjectName("inv_section_lbl")
        lay.addWidget(self._lbl)
        lay.addStretch()

        self._btn = QPushButton("▾")
        self._btn.setObjectName("inv_section_btn")
        self._btn.setFixedSize(20, 20)
        self._btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._btn.clicked.connect(self._on_click)
        lay.addWidget(self._btn)

        self._apply_style()

    def _apply_style(self) -> None:
        tk = THEME.tokens
        self._lbl.setStyleSheet(
            f"font-size:10px; font-weight:700; color:{tk.t4}; letter-spacing:0.8px;"
        )
        self._btn.setStyleSheet(f"""
            QPushButton#inv_section_btn {{
                background: transparent;
                color: {tk.t4};
                border: none;
                font-size: 11px;
                border-radius: 4px;
            }}
            QPushButton#inv_section_btn:hover {{
                background: {tk.border};
                color: {tk.t1};
            }}
        """)

    def _on_click(self) -> None:
        self._expanded = not self._expanded
        self._btn.setText("▾" if self._expanded else "▸")
        self.toggled.emit(self._expanded)

    def mousePressEvent(self, _event) -> None:  # click anywhere on the row
        self._on_click()

    def set_title(self, title: str) -> None:
        self._title = title
        self._lbl.setText(title.upper())

    def is_expanded(self) -> bool:
        return self._expanded

    def apply_theme(self) -> None:
        self._apply_style()


# ── Inventory Page ─────────────────────────────────────────────────────────────

class InventoryPage(QWidget):
    """
    Page 0 — inventory dashboard, filter bar, detail bar, product table.

    Layout (single QVBoxLayout — no nested scroll areas):
    ┌─────────────────────────────────────────┐
    │  ▾ OVERVIEW        (collapse header)    │
    │  DashboardWidget   (5 KPI cards + btn)  │
    │  ▾ FILTERS & SEARCH                     │
    │  FilterBar         (search + dropdowns) │
    │  ▾ SELECTED ITEM   (shown on selection) │
    │  ProductDetailBar  (collapses to h=0)   │
    ├─ divider ───────────────────────────────┤
    │  ProductTable  (stretch=1)              │  ← expands as headers collapse
    └─────────────────────────────────────────┘

    The table has stretch=1 in the root VBoxLayout, so every pixel freed
    by collapsing a section above is immediately reclaimed by the table.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._detail_user_collapsed = False
        self._build()

    # ── Build ────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Summary / KPI cards ──────────────────────────────────
        self._hdr_dash = _SectionHeader(t("inv_section_overview"))
        lay.addWidget(self._hdr_dash)

        self.dashboard = DashboardWidget()
        lay.addWidget(self.dashboard)
        self._hdr_dash.toggled.connect(self.dashboard.setVisible)

        # ── Filter bar ───────────────────────────────────────────
        self._sep_filter = _HSep()
        lay.addWidget(self._sep_filter)

        self._hdr_filter = _SectionHeader(t("inv_section_filters"))
        lay.addWidget(self._hdr_filter)

        self.filter_bar = FilterBar()
        lay.addWidget(self.filter_bar)
        self._hdr_filter.toggled.connect(self._on_filter_toggle)

        # ── Detail bar (appears when item selected) ──────────────
        self._sep_detail = _HSep()
        self._sep_detail.setVisible(False)
        lay.addWidget(self._sep_detail)

        self._hdr_detail = _SectionHeader(t("inv_section_selected"))
        self._hdr_detail.setVisible(False)
        lay.addWidget(self._hdr_detail)

        self.detail = ProductDetailBar()
        lay.addWidget(self.detail)
        self._hdr_detail.toggled.connect(self._on_detail_toggle)

        # ── Divider before table ─────────────────────────────────
        lay.addWidget(_HSep())

        # ── Product table (fills all remaining space) ────────────
        self.table = ProductTable()
        self.table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        lay.addWidget(self.table, 1)   # stretch=1 → grabs freed space instantly

    # ── Toggle helpers ───────────────────────────────────────────────────────

    def _on_filter_toggle(self, expanded: bool) -> None:
        self.filter_bar.setVisible(expanded)
        self._sep_filter.setVisible(expanded)

    def _on_detail_toggle(self, expanded: bool) -> None:
        """User explicitly toggled the selected-item section."""
        self._detail_user_collapsed = not expanded
        if not expanded:
            self.detail.setFixedHeight(0)
        elif self.detail._item is not None:
            self.detail.setFixedHeight(64)

    # ── Public: select product ───────────────────────────────────────────────

    def select_product(self, item: InventoryItem | None) -> None:
        """
        Called by main_window whenever the table selection changes.
        Updates the detail bar and controls header visibility.
        """
        self.detail.set_product(item)

        if item is None:
            self._hdr_detail.setVisible(False)
            self._sep_detail.setVisible(False)
        else:
            self._hdr_detail.setVisible(True)
            self._sep_detail.setVisible(True)
            if self._detail_user_collapsed:
                # Keep bar collapsed per user choice
                self.detail.setFixedHeight(0)

    # ── Filtering / sorting ──────────────────────────────────────────────────

    def fetch_filtered(self, filters: dict) -> list[InventoryItem]:
        """Pure data fetch — safe to call on a background thread."""
        search    = filters.get("search", "")
        status    = filters.get("status", "all")
        sort_by   = filters.get("sort_by", "name_asc")
        category  = filters.get("category", "all")
        price_min = filters.get("price_min", 0)
        price_max = filters.get("price_max", 0)

        items = _item_repo.get_all_items(search=search if len(search) >= 2 else "")

        # ── Category ────────────────────────────────────────────
        if category == "products":
            items = [i for i in items if i.is_product]
        elif category and category.startswith("cat_"):
            cat_key = category[4:]
            from app.repositories.category_repo import CategoryRepository
            try:
                cat_repo = CategoryRepository()
                cats     = cat_repo.get_all_active()
                match    = next((c for c in cats if c.key == cat_key), None)
                if match:
                    pt_ids = {pt.id for pt in match.part_types}
                    items  = [i for i in items if i.part_type_id in pt_ids]
            except Exception:
                pass

        # ── Status ──────────────────────────────────────────────
        if status in ("ok", "in_stock"):
            items = [i for i in items if i.stock > i.min_stock]
        elif status in ("low", "low_stock"):
            items = [i for i in items if 0 < i.stock <= i.min_stock]
        elif status == "critical":
            items = [i for i in items if i.stock <= max(1, i.min_stock // 4)]
        elif status in ("out", "out_of_stock"):
            items = [i for i in items if i.stock == 0]

        # ── Price range ─────────────────────────────────────────
        if price_min > 0:
            items = [i for i in items if (i.sell_price or 0) >= price_min]
        if price_max > 0:
            items = [i for i in items if (i.sell_price or 0) <= price_max]

        # ── Sort ────────────────────────────────────────────────
        sort_map = {
            "name_asc":     lambda x: (x.display_name.lower(),),
            "name_desc":    lambda x: (x.display_name.lower(),),
            "stock_asc":    lambda x: (x.stock,),
            "stock_desc":   lambda x: (-x.stock,),
            "price_asc":    lambda x: (x.sell_price or 0,),
            "price_desc":   lambda x: (-(x.sell_price or 0),),
            "updated_desc": lambda x: (x.updated_at or "",),
        }
        key_fn  = sort_map.get(sort_by, sort_map["name_asc"])
        reverse = sort_by in ("name_desc", "updated_desc")
        items.sort(key=key_fn, reverse=reverse)
        return items

    def load_items(self, items: list[InventoryItem]) -> int:
        """Main-thread UI update. Returns item count."""
        self.table.load(items)
        return len(items)

    def apply_filters(self, filters: dict) -> list[InventoryItem]:
        """Synchronous path for startup / immediate use."""
        items = self.fetch_filtered(filters)
        self.load_items(items)
        return items

    # ── Retranslate ──────────────────────────────────────────────────────────

    def apply_theme(self) -> None:
        """Re-apply inline styles after a theme toggle."""
        self._hdr_dash.apply_theme()
        self._hdr_filter.apply_theme()
        self._hdr_detail.apply_theme()

    def retranslate(self) -> None:
        self.dashboard.retranslate()
        self.filter_bar.retranslate()
        self.table.retranslate()
        self.detail.retranslate()
        self._hdr_dash.set_title(t("inv_section_overview"))
        self._hdr_filter.set_title(t("inv_section_filters"))
        self._hdr_detail.set_title(t("inv_section_selected"))

    # ── Table zoom (footer slider) ───────────────────────────────────────
    def apply_zoom(self, factor: float) -> None:
        """Forward the footer-slider zoom to the products table ONLY.

        The dashboard, filter bar, and detail panel are NOT zoomed — zoom
        is a table-only feature per product spec. Whole-app sizing is
        controlled separately by the UI Scale admin setting at startup.
        """
        if hasattr(self.table, "apply_zoom"):
            try:
                self.table.apply_zoom(factor)
            except Exception:
                pass


# ── Tiny helper ───────────────────────────────────────────────────────────────

class _HSep(QFrame):
    """1 px horizontal separator line using the theme border color."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFixedHeight(1)
        self.setObjectName("inv_divider")
