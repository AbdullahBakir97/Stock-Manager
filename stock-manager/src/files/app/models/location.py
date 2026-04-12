"""app/models/location.py — Location and location stock models."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class Location:
    id: int
    name: str
    description: str
    is_default: bool
    is_active: bool
    created_at: str


@dataclass
class LocationStock:
    """Stock quantity of a specific item at a specific location."""
    id: int
    item_id: int
    location_id: int
    quantity: int
    # Denormalized
    location_name: str = ""
    item_name: str = ""


@dataclass
class StockTransfer:
    """Record of a stock transfer between locations."""
    id: int
    item_id: int
    from_location_id: int
    to_location_id: int
    quantity: int
    note: Optional[str]
    timestamp: str
    # Denormalized
    item_name: str = ""
    from_location_name: str = ""
    to_location_name: str = ""
