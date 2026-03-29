"""app/models/transaction.py — Transaction value objects."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class InventoryTransaction:
    """Single audit record for any inventory_items operation."""
    id: int
    item_id: int
    operation: str        # IN | OUT | ADJUST | CREATE
    quantity: int
    stock_before: int
    stock_after: int
    note: Optional[str]
    timestamp: str
    # Denormalized (populated by JOIN)
    brand: str = ""
    name: str = ""
    color: str = ""
    model_name: str = ""
    part_type_name: str = ""

    @property
    def display_name(self) -> str:
        if self.model_name:
            return f"{self.model_name}  ·  {self.part_type_name}"
        parts = " ".join(p for p in (self.brand, self.name, self.color) if p)
        return parts or f"Item #{self.item_id}"


# ── Legacy compat (used by products tab until Phase C) ────────────────────────

@dataclass
class ProductTransaction:
    """Compatibility alias — maps to InventoryTransaction for product items."""
    id: int
    product_id: int
    operation: str
    quantity: int
    stock_before: int
    stock_after: int
    note: Optional[str]
    timestamp: str
    brand: str = ""
    type: str = ""
    color: str = ""
    barcode: Optional[str] = None
