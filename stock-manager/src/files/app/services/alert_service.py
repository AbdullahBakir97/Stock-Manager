"""app/services/alert_service.py — Low-stock alerts across all inventory."""
from __future__ import annotations
from app.repositories.item_repo import ItemRepository
from app.models.item import InventoryItem


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
            "low_count":       data.get("low_stock_count", 0) or 0,
            "out_count":       data.get("out_of_stock_count", 0) or 0,
            "inventory_value": data.get("inventory_value", 0.0) or 0.0,
        }

    def get_critical_entries(self) -> list[InventoryItem]:
        """Matrix items that need reordering (best_bung < 0)."""
        return [i for i in self.get_low_stock_items() if not i.is_product]

    # ── Expiry alerts ──────────────────────────────────────────────────────────

    def get_expiring_items(self, days: int = 30) -> list[InventoryItem]:
        """Items expiring within the next `days` days (not yet expired)."""
        return self._items.get_expiring(days=days)

    def get_expired_items(self) -> list[InventoryItem]:
        """Items whose expiry date has already passed."""
        return self._items.get_expired()

    def total_alert_count(self, expiry_days: int = 30) -> int:
        """Combined count of low-stock + expiring + expired items."""
        low = len(self.get_low_stock_items())
        expiring = len(self.get_expiring_items(days=expiry_days))
        expired = len(self.get_expired_items())
        return low + expiring + expired
