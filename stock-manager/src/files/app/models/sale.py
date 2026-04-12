"""app/models/sale.py — Sale and sale-item models."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SaleItem:
    """Single line item in a sale."""
    id: int
    sale_id: int
    item_id: int
    quantity: int
    unit_price: float
    cost_price: float
    line_total: float
    # Denormalized
    item_name: str = ""
    item_barcode: str = ""

    @property
    def profit(self) -> float:
        return self.line_total - (self.cost_price * self.quantity)


@dataclass
class Sale:
    id: int
    customer_name: str
    total_amount: float
    discount: float
    note: str
    timestamp: str
    customer_id: Optional[int] = None
    items: list[SaleItem] = field(default_factory=list)

    @property
    def net_total(self) -> float:
        return self.total_amount - self.discount

    @property
    def item_count(self) -> int:
        return sum(i.quantity for i in self.items)

    @property
    def total_profit(self) -> float:
        return sum(i.profit for i in self.items)
