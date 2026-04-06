"""app/services/sale_service.py — Sales / POS business logic."""
from __future__ import annotations

from typing import Optional

from app.core.database import get_connection
from app.repositories.sale_repo import SaleRepository
from app.repositories.item_repo import ItemRepository
from app.repositories.transaction_repo import TransactionRepository
from app.services.supplier_service import SupplierService
from app.models.sale import Sale
from app.core.logger import get_logger

_log = get_logger(__name__)


class SaleService:

    def __init__(self) -> None:
        self._sales = SaleRepository()
        self._items = ItemRepository()
        self._txn = TransactionRepository()
        self._suppliers = SupplierService()

    def create_sale(self, customer_name: str = "", discount: float = 0,
                    note: str = "",
                    items: list[dict] | None = None,
                    customer_id: int | None = None) -> int:
        """Process a sale: create record, deduct stock, log transactions.

        Each item dict: {item_id, quantity, unit_price}.
        cost_price is auto-looked-up from supplier if available.
        """
        if not items:
            raise ValueError("Sale must have at least one item")

        # Validate stock availability and populate cost prices
        enriched: list[dict] = []
        for line in items:
            item = self._items.get_by_id(line["item_id"])
            if not item:
                raise ValueError(f"Item {line['item_id']} not found")
            qty = line["quantity"]
            if qty <= 0:
                raise ValueError("Item quantity must be positive")
            if qty > item.stock:
                raise ValueError(
                    f"Insufficient stock for {item.display_name}: "
                    f"{item.stock} available, {qty} requested"
                )
            cost = line.get("cost_price")
            if cost is None:
                cost = self._suppliers.get_preferred_cost(item.id) or 0
            enriched.append({
                "item_id": item.id,
                "quantity": qty,
                "unit_price": line["unit_price"],
                "cost_price": cost,
            })

        # Create sale record
        sale_id = self._sales.create(
            customer_name=customer_name, discount=discount,
            note=note, items=enriched, customer_id=customer_id,
        )

        # Deduct stock and log transactions
        with get_connection() as conn:
            for line in enriched:
                item = self._items.get_by_id(line["item_id"])
                before, after = self._items.apply_delta(
                    conn, line["item_id"], -line["quantity"]
                )
                self._txn.log_op(
                    conn, line["item_id"], "OUT", line["quantity"],
                    before, after, f"Sale #{sale_id}",
                )

        _log.info(
            f"Sale created: id={sale_id}, items={len(enriched)}, "
            f"customer={customer_name}"
        )
        return sale_id

    def get_by_customer(self, customer_id: int, limit: int = 50) -> list[Sale]:
        """Return sales linked to a specific customer."""
        return self._sales.get_by_customer(customer_id, limit=limit)

    def get_sale(self, sale_id: int) -> Optional[Sale]:
        return self._sales.get_by_id(sale_id)

    def get_sales(self, limit: int = 200, offset: int = 0,
                  date_from: str = "", date_to: str = "") -> list[Sale]:
        return self._sales.get_all(
            limit=limit, offset=offset,
            date_from=date_from, date_to=date_to,
        )

    def delete_sale(self, sale_id: int) -> bool:
        return self._sales.delete(sale_id)

    def daily_totals(self, date: str) -> dict:
        return self._sales.daily_totals(date)

    def top_items(self, limit: int = 10, date_from: str = "",
                  date_to: str = "") -> list[dict]:
        return self._sales.top_items(
            limit=limit, date_from=date_from, date_to=date_to,
        )
