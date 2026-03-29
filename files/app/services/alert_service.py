"""app/services/alert_service.py — Low-stock alerts across all inventory."""
from __future__ import annotations
from app.repositories.item_repo import ItemRepository
from app.models.item import InventoryItem
from app.models.product import Product


class AlertService:

    def __init__(self) -> None:
        self._items = ItemRepository()

    # ── Unified alerts (all inventory_items) ──────────────────────────────────

    def get_low_stock_items(self) -> list[InventoryItem]:
        """All items (products + matrix) at or below their min_stock threshold."""
        return self._items.get_low_stock()

    def get_out_of_stock_items(self) -> list[InventoryItem]:
        """All items with stock == 0."""
        all_low = self._items.get_low_stock()
        return [i for i in all_low if i.is_out]

    def summary(self) -> dict:
        data = self._items.get_summary()
        return {
            "low_count":         data.get("low_stock_count", 0) or 0,
            "out_count":         data.get("out_of_stock_count", 0) or 0,
            "inventory_value":   data.get("inventory_value", 0.0) or 0.0,
            # legacy keys kept until Phase C
            "low_product_count": data.get("low_stock_count", 0) or 0,
            "out_product_count": data.get("out_of_stock_count", 0) or 0,
        }

    # ── Compat — used by products tab until Phase C ───────────────────────────

    def get_low_stock_products(self) -> list[Product]:
        """Returns Product objects for the LowStockDialog (Phase C removes this)."""
        items = self._items.get_all_products(filter_low_stock=True)
        return [self._item_to_product(i) for i in items]

    def get_critical_entries(self) -> list[InventoryItem]:
        """Matrix items that need reordering (best_bung < 0)."""
        return [i for i in self.get_low_stock_items() if not i.is_product]

    # ── Private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _item_to_product(item: InventoryItem) -> Product:
        return Product(
            id=item.id,
            brand=item.brand,
            type=item.name,
            color=item.color,
            stock=item.stock,
            barcode=item.barcode,
            low_stock_threshold=item.min_stock,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
