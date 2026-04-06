"""app/models/return_item.py — Return model."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class ReturnItem:
    """A product return record."""
    id: int
    sale_id: Optional[int]
    item_id: int
    quantity: int
    reason: str
    action: str  # RESTOCK or WRITEOFF
    refund_amount: float
    created_at: str
    # Denormalized
    item_name: str = ""
    item_barcode: str = ""
