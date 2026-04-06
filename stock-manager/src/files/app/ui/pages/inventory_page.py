"""
app/ui/pages/inventory_page.py — Main inventory page (dashboard + table + detail bar).
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QSizePolicy,
)
from PyQt6.QtCore import Qt

from app.core.i18n import t
from app.repositories.item_repo import ItemRepository
from app.models.item import InventoryItem
from app.ui.components.dashboard_widget import DashboardWidget
from app.ui.components.filter_bar import FilterBar
from app.ui.components.product_table import ProductTable
from app.ui.components.product_detail_bar import ProductDetailBar

_item_repo = ItemRepository()


class InventoryPage(QWidget):
    """Page 0 — inventory dashboard, filter bar, detail bar, product table."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._build()

    # ── Build ────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self.dashboard = DashboardWidget()
        lay.addWidget(self.dashboard)

        self.filter_bar = FilterBar()
        lay.addWidget(self.filter_bar)

        # Horizontal detail bar (hidden until a product is selected)
        self.detail = ProductDetailBar()
        lay.addWidget(self.detail)

        # Table takes all remaining space
        self.table = ProductTable()
        self.table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        lay.addWidget(self.table, 1)

    # ── Filtering / sorting ──────────────────────────────────────────────────

    def fetch_filtered(self, filters: dict) -> list[InventoryItem]:
        """
        Pure data fetch — safe to call on a background thread.
        Runs the DB query + in-process filtering/sorting and returns the list.
        Does NOT touch any Qt widgets.
        """
        search    = filters.get("search", "")
        status    = filters.get("status", "all")
        sort_by   = filters.get("sort_by", "name_asc")
        category  = filters.get("category", "all")
        price_min = filters.get("price_min", 0)
        price_max = filters.get("price_max", 0)

        items = _item_repo.get_all_items(search=search if len(search) >= 2 else "")

        # ── Category filter ─────────────────────────────────────────
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

        # ── Status filter ───────────────────────────────────────────
        if status in ("ok", "in_stock"):
            items = [i for i in items if i.stock > i.min_stock]
        elif status in ("low", "low_stock"):
            items = [i for i in items if 0 < i.stock <= i.min_stock]
        elif status == "critical":
            items = [i for i in items if i.stock <= max(1, i.min_stock // 4)]
        elif status in ("out", "out_of_stock"):
            items = [i for i in items if i.stock == 0]

        # ── Price range filter ──────────────────────────────────────
        if price_min > 0:
            items = [i for i in items if (i.sell_price or 0) >= price_min]
        if price_max > 0:
            items = [i for i in items if (i.sell_price or 0) <= price_max]

        # ── Sort ────────────────────────────────────────────────────
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
        """
        Main-thread UI update — populate the table with pre-fetched items.
        Returns the item count so callers can update the status bar.
        Must be called on the main thread.
        """
        self.table.load(items)
        return len(items)

    def apply_filters(self, filters: dict) -> list[InventoryItem]:
        """Synchronous path kept for callers that still need an immediate result
        (e.g. startup loading overlay). Prefer fetch_filtered + load_items."""
        items = self.fetch_filtered(filters)
        self.load_items(items)
        return items

    # ── Retranslate ──────────────────────────────────────────────────────────

    def retranslate(self) -> None:
        self.dashboard.retranslate()
        self.filter_bar.retranslate()
        self.table.retranslate()
        self.detail.retranslate()
