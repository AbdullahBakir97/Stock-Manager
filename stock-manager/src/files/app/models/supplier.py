"""app/models/supplier.py — Supplier and supplier-item mapping."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class Supplier:
    id: int
    name: str
    contact_name: str
    phone: str
    email: str
    address: str
    notes: str
    is_active: bool
    created_at: str
    rating: int = 0
    updated_at: str = ""
    # Computed (set by repo)
    item_count: int = 0
    total_orders: int = 0

    @property
    def display_name(self) -> str:
        if self.contact_name:
            return f"{self.name} ({self.contact_name})"
        return self.name


@dataclass
class SupplierItem:
    """Links a supplier to an inventory item with pricing info."""
    id: int
    supplier_id: int
    item_id: int
    cost_price: float
    lead_days: int
    supplier_sku: str
    is_preferred: bool
    # Denormalized (populated by JOIN)
    supplier_name: str = ""
    item_name: str = ""

    @property
    def sku(self) -> str:
        """Alias for supplier_sku for compatibility."""
        return self.supplier_sku
