"""app/models/item.py — Unified inventory item (products + matrix entries)."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class InventoryItem:
    id: int
    brand: str
    name: str          # = product "type" for standalone items
    color: str
    sku: Optional[str]
    barcode: Optional[str]
    sell_price: Optional[float]
    stock: int
    min_stock: int     # = stamm_zahl for matrix, low_stock_threshold for products
    inventur: Optional[int]
    model_id: Optional[int]       # NULL  → standalone product
    part_type_id: Optional[int]   # NULL  → standalone product
    is_active: bool
    created_at: str
    updated_at: str
    # Denormalized (populated by JOIN in repository)
    model_name: str = ""
    model_brand: str = ""
    image_path: Optional[str] = None
    expiry_date: Optional[str] = None
    warranty_date: Optional[str] = None
    part_type_key: str = ""
    part_type_name: str = ""
    part_type_color: str = ""

    # ── Computed helpers ──────────────────────────────────────────────────────

    @property
    def is_product(self) -> bool:
        """True for standalone products; False for matrix (model × part type) items."""
        return self.model_id is None

    @property
    def best_bung(self) -> int:
        """Stock surplus above the minimum. Negative = needs ordering."""
        return self.stock - self.min_stock

    @property
    def needs_reorder(self) -> bool:
        return self.min_stock > 0 and self.stock < self.min_stock

    @property
    def is_low(self) -> bool:
        return 0 < self.stock <= self.min_stock

    @property
    def is_out(self) -> bool:
        return self.stock == 0

    @property
    def display_name(self) -> str:
        if not self.is_product:
            parts = [self.model_name, self.part_type_name]
            if self.color:
                parts.append(self.color)
            return "  ·  ".join(p for p in parts if p)
        parts = " ".join(p for p in (self.brand, self.name, self.color) if p)
        return parts or f"Item #{self.id}"
