"""app/models/customer.py — Customer dataclass for CRM-lite."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Customer:
    """A registered customer with purchase history summary."""
    id: int
    name: str
    phone: str = ""
    email: str = ""
    address: str = ""
    notes: str = ""
    is_active: bool = True
    created_at: str = ""
    # ── Computed summary (populated by repo joins) ──
    total_purchases: int = 0
    total_spent: float = 0.0
    last_purchase: str = ""

    @property
    def display_name(self) -> str:
        return self.name or "—"

    @property
    def avg_order(self) -> float:
        if self.total_purchases == 0:
            return 0.0
        return self.total_spent / self.total_purchases
