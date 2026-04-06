"""app/models/price_list.py — Price list data models."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PriceList:
    """Represents a price list."""

    id: int = 0
    name: str = ""
    description: str = ""
    is_active: bool = True
    created_at: str = ""
    item_count: int = 0


@dataclass
class PriceListItem:
    """Represents an item in a price list."""

    id: int = 0
    price_list_id: int = 0
    item_id: int = 0
    item_name: str = ""
    barcode: str = ""
    current_price: float = 0.0
    list_price: float = 0.0
    cost_price: float = 0.0
    margin_pct: float = 0.0  # computed: (list_price - cost_price) / list_price * 100
    stock: int = 0


@dataclass
class MarginAnalysis:
    """Represents margin analysis for an inventory item."""

    item_id: int = 0
    item_name: str = ""
    barcode: str = ""
    sell_price: float = 0.0
    cost_price: float = 0.0
    margin_amount: float = 0.0
    margin_pct: float = 0.0
    stock: int = 0
    potential_profit: float = 0.0  # margin_amount * stock
