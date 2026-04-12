"""app/models/purchase_order.py — Purchase order and line item models."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PurchaseOrderLine:
    """A single line item on a purchase order."""
    id: int
    po_id: int
    item_id: int
    quantity: int
    cost_price: float
    received_qty: int = 0
    # Denormalized
    item_name: str = ""
    item_barcode: str = ""

    @property
    def line_total(self) -> float:
        return self.quantity * self.cost_price

    @property
    def is_fully_received(self) -> bool:
        return self.received_qty >= self.quantity


@dataclass
class PurchaseOrder:
    """A purchase order header."""
    id: int
    po_number: str
    supplier_id: Optional[int]
    status: str  # DRAFT, SENT, PARTIAL, RECEIVED, CLOSED, CANCELLED
    notes: str
    created_at: str
    updated_at: str
    # Denormalized
    supplier_name: str = ""
    line_count: int = 0
    total_value: float = 0.0
    lines: list[PurchaseOrderLine] = field(default_factory=list)

    @property
    def is_editable(self) -> bool:
        return self.status in ("DRAFT", "SENT")

    @property
    def status_label(self) -> str:
        return {
            "DRAFT": "Draft",
            "SENT": "Sent",
            "PARTIAL": "Partially Received",
            "RECEIVED": "Received",
            "CLOSED": "Closed",
            "CANCELLED": "Cancelled",
        }.get(self.status, self.status)
