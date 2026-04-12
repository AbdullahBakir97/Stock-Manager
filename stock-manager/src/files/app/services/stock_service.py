"""
app/services/stock_service.py — All stock business logic.

Unified service for all inventory_items (products and matrix items alike).
"""
from __future__ import annotations
from app.core.database import get_connection
from app.repositories.item_repo import ItemRepository
from app.repositories.transaction_repo import TransactionRepository
from app.core.i18n import t
from app.core.logger import get_logger

_log = get_logger(__name__)


class StockService:

    def __init__(self) -> None:
        self._items = ItemRepository()
        self._txn   = TransactionRepository()

    # ── Unified operations (all inventory_items) ──────────────────────────────

    def stock_in(self, item_id: int, quantity: int, note: str = "") -> dict:
        if quantity <= 0:
            err_msg = t("err_qty_positive")
            _log.error(f"Stock In failed: item_id={item_id}, qty={quantity}, reason=invalid_quantity")
            raise ValueError(err_msg)
        try:
            with get_connection() as conn:
                item = self._items.get_by_id(item_id)
                if not item:
                    err_msg = t("err_entry_not_found")
                    _log.error(f"Stock In failed: item_id={item_id}, qty={quantity}, reason=item_not_found")
                    raise ValueError(err_msg)
                before, after = self._items.apply_delta(conn, item_id, quantity)
                self._txn.log_op(conn, item_id, "IN", quantity, before, after, note)
                _log.info(f"Stock In: item_id={item_id}, qty={quantity}, before={before}, after={after}, note={note}")
            return {"before": before, "after": after, "delta": quantity}
        except ValueError as e:
            _log.error(f"Stock In error: {str(e)}")
            raise

    def stock_out(self, item_id: int, quantity: int, note: str = "") -> dict:
        if quantity <= 0:
            err_msg = t("err_qty_positive")
            _log.error(f"Stock Out failed: item_id={item_id}, qty={quantity}, reason=invalid_quantity")
            raise ValueError(err_msg)
        try:
            with get_connection() as conn:
                item = self._items.get_by_id(item_id)
                if not item:
                    err_msg = t("err_entry_not_found")
                    _log.error(f"Stock Out failed: item_id={item_id}, qty={quantity}, reason=item_not_found")
                    raise ValueError(err_msg)
                if quantity > item.stock:
                    err_msg = t("err_insufficient_stock",
                                available=item.stock, requested=quantity)
                    _log.warning(f"Stock Out failed: item_id={item_id}, qty={quantity}, available={item.stock}, reason=insufficient_stock")
                    raise ValueError(err_msg)
                before, after = self._items.apply_delta(conn, item_id, -quantity)
                self._txn.log_op(conn, item_id, "OUT", quantity, before, after, note)
                _log.info(f"Stock Out: item_id={item_id}, qty={quantity}, before={before}, after={after}, note={note}")
            return {"before": before, "after": after, "delta": -quantity}
        except ValueError as e:
            _log.error(f"Stock Out error: {str(e)}")
            raise

    def stock_adjust(self, item_id: int, new_stock: int, note: str = "") -> dict:
        if new_stock < 0:
            err_msg = t("err_stock_negative")
            _log.error(f"Stock Adjust failed: item_id={item_id}, new_stock={new_stock}, reason=negative_stock")
            raise ValueError(err_msg)
        try:
            with get_connection() as conn:
                item = self._items.get_by_id(item_id)
                if not item:
                    err_msg = t("err_entry_not_found")
                    _log.error(f"Stock Adjust failed: item_id={item_id}, new_stock={new_stock}, reason=item_not_found")
                    raise ValueError(err_msg)
                before, after = self._items.set_exact(conn, item_id, new_stock)
                qty = abs(after - before)
                self._txn.log_op(conn, item_id, "ADJUST", qty, before, after, note)
                _log.info(f"Stock Adjust: item_id={item_id}, before={before}, after={after}, delta={after - before}, note={note}")
            return {"before": before, "after": after, "delta": after - before}
        except ValueError as e:
            _log.error(f"Stock Adjust error: {str(e)}")
            raise

