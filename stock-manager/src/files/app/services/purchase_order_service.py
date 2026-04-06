"""app/services/purchase_order_service.py — Business logic for purchase orders."""
from __future__ import annotations
from typing import Optional

from app.core.database import get_connection
from app.core.i18n import t
from app.core.logger import get_logger
from app.repositories.purchase_order_repo import PurchaseOrderRepository
from app.repositories.item_repo import ItemRepository
from app.services.stock_service import StockService
from app.models.purchase_order import PurchaseOrder

_log = get_logger(__name__)


class PurchaseOrderService:
    """Orchestrates PO workflows: create, send, receive, close."""

    def __init__(self) -> None:
        self._po_repo = PurchaseOrderRepository()
        self._items = ItemRepository()
        self._stock = StockService()

    def create_order(self, supplier_id: Optional[int] = None,
                     notes: str = "") -> int:
        """Create a new draft PO and return its ID."""
        po_id = self._po_repo.create(supplier_id=supplier_id, notes=notes)
        _log.info(f"Created PO id={po_id}")
        return po_id

    def add_item(self, po_id: int, item_id: int,
                 quantity: int = 1, cost_price: float = 0) -> int:
        """Add an inventory item to a PO. Returns line ID."""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        line_id = self._po_repo.add_line(po_id, item_id, quantity, cost_price)
        _log.info(f"Added line to PO {po_id}: item={item_id}, qty={quantity}")
        return line_id

    def send_order(self, po_id: int) -> None:
        """Mark PO as sent to supplier."""
        po = self._po_repo.get_by_id(po_id)
        if not po:
            raise ValueError("Purchase order not found")
        if po.status != "DRAFT":
            raise ValueError(f"Cannot send PO in status '{po.status}'")
        if po.line_count == 0:
            raise ValueError("Cannot send an empty purchase order")
        self._po_repo.set_status(po_id, "SENT")
        _log.info(f"PO {po.po_number} sent")

    def receive_order(self, po_id: int,
                      received: dict[int, int] | None = None) -> dict:
        """Receive items from a PO.

        Args:
            po_id: The purchase order ID
            received: Optional dict of {line_id: quantity_received}.
                     If None, receives all lines fully.
        Returns:
            Summary dict with counts.
        """
        po = self._po_repo.get_by_id(po_id)
        if not po:
            raise ValueError("Purchase order not found")
        if po.status not in ("SENT", "PARTIAL"):
            raise ValueError(f"Cannot receive PO in status '{po.status}'")

        lines = self._po_repo.get_lines(po_id)
        items_received = 0
        units_received = 0

        for line in lines:
            if received:
                qty = received.get(line.id, 0)
            else:
                qty = line.quantity - line.received_qty

            if qty <= 0:
                continue

            # Stock in the received quantity
            self._stock.stock_in(
                line.item_id, qty,
                f"PO {po.po_number} received"
            )
            # Update received count on line
            new_received = line.received_qty + qty
            self._po_repo.receive_line(line.id, new_received)
            items_received += 1
            units_received += qty

        # Determine new PO status
        updated_lines = self._po_repo.get_lines(po_id)
        all_received = all(l.received_qty >= l.quantity for l in updated_lines)
        any_received = any(l.received_qty > 0 for l in updated_lines)

        if all_received:
            self._po_repo.set_status(po_id, "RECEIVED")
        elif any_received:
            self._po_repo.set_status(po_id, "PARTIAL")

        _log.info(f"PO {po.po_number}: received {units_received} units across {items_received} items")
        return {"items": items_received, "units": units_received}

    def close_order(self, po_id: int) -> None:
        """Close a PO (after receiving or to archive)."""
        po = self._po_repo.get_by_id(po_id)
        if not po:
            raise ValueError("Purchase order not found")
        self._po_repo.set_status(po_id, "CLOSED")
        _log.info(f"PO {po.po_number} closed")

    def cancel_order(self, po_id: int) -> None:
        """Cancel a PO (only DRAFT or SENT)."""
        po = self._po_repo.get_by_id(po_id)
        if not po:
            raise ValueError("Purchase order not found")
        if po.status not in ("DRAFT", "SENT"):
            raise ValueError(f"Cannot cancel PO in status '{po.status}'")
        self._po_repo.set_status(po_id, "CANCELLED")
        _log.info(f"PO {po.po_number} cancelled")
