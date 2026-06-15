"""app/models/phone_transaction.py — Audit log entry for a phone unit."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class PhoneTransaction:
    id:            int
    phone_id:      int
    operation:     str   # CREATE | EDIT | SOLD | RESERVED | IN_STOCK | DELETE
    status_before: str
    status_after:  str
    imei:          str
    model_brand:   str
    model_name:    str
    storage:       str
    sell_price:    Optional[float]
    note:          str
    timestamp:     str

    @property
    def display_name(self) -> str:
        parts = [self.model_brand, self.model_name]
        if self.storage:
            parts.append(self.storage)
        name = " ".join(p for p in parts if p)
        return name or f"Phone #{self.phone_id}"

    @property
    def operation_label(self) -> str:
        from app.core.i18n import t
        return {
            "CREATE":   t("pht_op_create"),
            "EDIT":     t("pht_op_edit"),
            "SOLD":     t("pht_op_sold"),
            "RESERVED": t("pht_op_reserved"),
            "IN_STOCK": t("pht_op_in_stock"),
            "DELETE":   t("pht_op_delete"),
        }.get(self.operation, self.operation.title())
