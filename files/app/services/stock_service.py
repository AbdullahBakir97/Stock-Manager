"""
app/services/stock_service.py — All stock business logic.

Unified service for all inventory_items (products and matrix items alike).
product_stock_* methods are compat aliases until Phase C updates the products tab.
"""
from __future__ import annotations
from app.core.database import get_connection
from app.repositories.item_repo import ItemRepository
from app.repositories.transaction_repo import TransactionRepository
from app.core.i18n import t


class StockService:

    def __init__(self) -> None:
        self._items = ItemRepository()
        self._txn   = TransactionRepository()

    # ── Unified operations (all inventory_items) ──────────────────────────────

    def stock_in(self, item_id: int, quantity: int, note: str = "") -> dict:
        if quantity <= 0:
            raise ValueError(t("err_qty_positive"))
        with get_connection() as conn:
            item = self._items.get_by_id(item_id)
            if not item:
                raise ValueError(t("err_entry_not_found"))
            before, after = self._items.apply_delta(conn, item_id, quantity)
            self._txn.log_op(conn, item_id, "IN", quantity, before, after, note)
        return {"before": before, "after": after, "delta": quantity}

    def stock_out(self, item_id: int, quantity: int, note: str = "") -> dict:
        if quantity <= 0:
            raise ValueError(t("err_qty_positive"))
        with get_connection() as conn:
            item = self._items.get_by_id(item_id)
            if not item:
                raise ValueError(t("err_entry_not_found"))
            if quantity > item.stock:
                raise ValueError(
                    t("err_insufficient_stock",
                      available=item.stock, requested=quantity)
                )
            before, after = self._items.apply_delta(conn, item_id, -quantity)
            self._txn.log_op(conn, item_id, "OUT", quantity, before, after, note)
        return {"before": before, "after": after, "delta": -quantity}

    def stock_adjust(self, item_id: int, new_stock: int, note: str = "") -> dict:
        if new_stock < 0:
            raise ValueError(t("err_stock_negative"))
        with get_connection() as conn:
            item = self._items.get_by_id(item_id)
            if not item:
                raise ValueError(t("err_entry_not_found"))
            before, after = self._items.set_exact(conn, item_id, new_stock)
            qty = abs(after - before)
            self._txn.log_op(conn, item_id, "ADJUST", qty, before, after, note)
        return {"before": before, "after": after, "delta": after - before}

    # ── Compat aliases — used by products tab until Phase C ───────────────────

    def product_stock_in(self, product_id: int, quantity: int,
                         note: str = "") -> dict:
        return self.stock_in(product_id, quantity, note)

    def product_stock_out(self, product_id: int, quantity: int,
                          note: str = "") -> dict:
        return self.stock_out(product_id, quantity, note)

    def product_adjust(self, product_id: int, new_stock: int,
                       note: str = "") -> dict:
        return self.stock_adjust(product_id, new_stock, note)
