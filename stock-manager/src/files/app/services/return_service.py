"""app/services/return_service.py — Business logic for returns."""
from __future__ import annotations
from typing import Optional

from app.core.logger import get_logger
from app.repositories.return_repo import ReturnRepository
from app.services.stock_service import StockService

_log = get_logger(__name__)


class ReturnService:
    """Processes product returns — restocking or writing off."""

    def __init__(self) -> None:
        self._ret_repo = ReturnRepository()
        self._stock = StockService()

    def process_return(self, *, item_id: int, quantity: int,
                       reason: str = "", action: str = "RESTOCK",
                       refund_amount: float = 0,
                       sale_id: Optional[int] = None) -> int:
        """Process a return. If action is RESTOCK, adds stock back.

        Returns the return record ID.
        """
        if quantity <= 0:
            raise ValueError("Return quantity must be positive")

        # Create the return record
        ret_id = self._ret_repo.create(
            item_id=item_id, quantity=quantity, reason=reason,
            action=action, refund_amount=refund_amount, sale_id=sale_id,
        )

        # Restock if applicable
        if action == "RESTOCK":
            self._stock.stock_in(item_id, quantity, f"Return #{ret_id}: {reason}")
            _log.info(f"Return #{ret_id}: restocked {quantity} units of item {item_id}")
        else:
            _log.info(f"Return #{ret_id}: wrote off {quantity} units of item {item_id}")

        return ret_id
