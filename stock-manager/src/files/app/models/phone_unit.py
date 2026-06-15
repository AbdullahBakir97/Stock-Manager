"""app/models/phone_unit.py — Individual phone unit (whole device, tracked by IMEI)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class PhoneUnit:
    id:          int
    model_id:    int
    imei:        str
    storage:     str       # '64GB' | '128GB' | '256GB' | '512GB' | '1TB' | ''
    condition:   str       # 'new' | 'used' | 'refurbished'
    battery_pct: Optional[int]    # 0-100, None = unknown
    buy_price:   Optional[float]
    sell_price:  Optional[float]
    status:      str       # 'in_stock' | 'sold' | 'reserved'
    notes:       str
    created_at:  str

    # Denormalized from JOIN
    model_name:  str = ""
    model_brand: str = ""

    @property
    def is_in_stock(self) -> bool:
        return self.status == "in_stock"

    @property
    def condition_label(self) -> str:
        from app.core.i18n import t
        return {
            "new": t("ph_cond_new"),
            "used": t("ph_cond_used"),
            "refurbished": t("ph_cond_refurb_short"),
        }.get(self.condition, self.condition.title())

    @property
    def storage_label(self) -> str:
        return self.storage if self.storage else "—"

    @property
    def battery_label(self) -> str:
        return f"{self.battery_pct}%" if self.battery_pct is not None else "—"

    @property
    def display_name(self) -> str:
        parts = [self.model_brand, self.model_name]
        if self.storage:
            parts.append(self.storage)
        return " ".join(p for p in parts if p)
