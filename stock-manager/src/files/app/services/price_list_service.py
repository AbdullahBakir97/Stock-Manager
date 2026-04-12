"""app/services/price_list_service.py — Price list business logic."""
from __future__ import annotations

from app.core.database import get_connection
from app.models.price_list import MarginAnalysis, PriceList, PriceListItem
from app.repositories.price_list_repo import PriceListRepository
from app.core.logger import get_logger

_log = get_logger(__name__)


class PriceListService:
    """Service for price list operations."""

    def __init__(self) -> None:
        """Initialize the service."""
        self._repo = PriceListRepository()

    def get_all_lists(self) -> list[PriceList]:
        """Get all price lists."""
        return self._repo.get_all()

    def get_list(self, list_id: int) -> PriceList | None:
        """Get a price list by ID."""
        return self._repo.get_by_id(list_id)

    def create_list(self, name: str, description: str = "") -> int:
        """Create a new price list."""
        if not name or not name.strip():
            raise ValueError("Price list name cannot be empty")
        list_id = self._repo.create(name.strip(), description.strip())
        _log.info(f"Created price list: id={list_id}, name={name}")
        return list_id

    def update_list(
        self, list_id: int, name: str, description: str, is_active: bool
    ) -> None:
        """Update a price list."""
        if not name or not name.strip():
            raise ValueError("Price list name cannot be empty")
        self._repo.update(list_id, name.strip(), description.strip(), is_active)

    def delete_list(self, list_id: int) -> None:
        """Delete a price list."""
        self._repo.delete(list_id)
        _log.info(f"Deleted price list: id={list_id}")

    def get_list_items(self, list_id: int) -> list[PriceListItem]:
        """Get all items in a price list."""
        return self._repo.get_items(list_id)

    def add_item(self, list_id: int, item_id: int, price: float) -> int:
        """Add an item to a price list."""
        if price < 0:
            raise ValueError("Price cannot be negative")
        return self._repo.add_item(list_id, item_id, price)

    def update_price(self, pli_id: int, price: float) -> None:
        """Update the price of an item in a price list."""
        if price < 0:
            raise ValueError("Price cannot be negative")
        self._repo.update_item_price(pli_id, price)

    def remove_item(self, pli_id: int) -> None:
        """Remove an item from a price list."""
        self._repo.remove_item(pli_id)

    def bulk_populate(self, list_id: int) -> int:
        """Add all inventory items to a price list."""
        return self._repo.bulk_add_all_items(list_id)

    def apply_price_list(self, list_id: int) -> int:
        """Apply a price list to inventory (update sell_price for all items)."""
        conn = get_connection()
        cursor = conn.cursor()

        # Update all items in inventory with prices from the list
        cursor.execute(
            """
            UPDATE inventory_items
            SET sell_price = (
                SELECT pli.price
                FROM price_list_items pli
                WHERE pli.item_id = inventory_items.id
                AND pli.price_list_id = ?
            )
            WHERE id IN (
                SELECT item_id FROM price_list_items WHERE price_list_id = ?
            )
            """,
            (list_id, list_id),
        )
        conn.commit()
        count = cursor.rowcount
        conn.close()
        _log.info(f"Applied price list: id={list_id}, items_updated={count}")
        return count

    def get_margin_analysis(self) -> list[MarginAnalysis]:
        """Get margin analysis for all inventory items."""
        return self._repo.get_margin_analysis()

    def bulk_markup(self, list_id: int, pct: float) -> int:
        """Increase all items in a price list by a percentage."""
        if pct < 0:
            raise ValueError("Markup percentage cannot be negative")

        conn = get_connection()
        cursor = conn.cursor()

        # Get all items in the list
        cursor.execute(
            """
            SELECT id, price FROM price_list_items WHERE price_list_id = ?
            """,
            (list_id,),
        )
        items = cursor.fetchall()

        # Update each item
        for item_id, current_price in items:
            new_price = current_price * (1 + pct / 100)
            cursor.execute(
                """
                UPDATE price_list_items SET price = ? WHERE id = ?
                """,
                (new_price, item_id),
            )

        conn.commit()
        count = cursor.rowcount
        conn.close()
        _log.info(f"Applied bulk markup: list_id={list_id}, markup_pct={pct}, items_updated={count}")
        return count

    def get_summary(self) -> dict:
        """Get summary statistics for price lists."""
        return self._repo.get_summary()
