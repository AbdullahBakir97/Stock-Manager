"""app/models/product.py — Product value object."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class Product:
    id: int
    brand: str
    type: str
    color: str
    stock: int
    barcode: Optional[str]
    low_stock_threshold: int
    created_at: str
    updated_at: str
    sell_price: Optional[float] = None

    @property
    def is_low(self) -> bool:
        return self.stock <= self.low_stock_threshold

    @property
    def is_out(self) -> bool:
        return self.stock == 0
