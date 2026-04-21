"""app/models/scan_session.py — Data classes for Quick Scan sessions."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from app.models.item import InventoryItem


class ScanEventType(Enum):
    MODE_CHANGED = "mode_changed"
    ITEM_ADDED = "item_added"
    ITEM_INCREMENTED = "item_incremented"
    BATCH_COMMITTED = "batch_committed"
    BATCH_EMPTY = "batch_empty"
    NOT_FOUND = "not_found"
    NO_MODE = "no_mode"
    INSUFFICIENT_STOCK = "insufficient_stock"
    SESSION_ACTIVE = "session_active"
    WAITING_COLOR = "waiting_color"        # item scanned, now scan color barcode
    COLOR_APPLIED = "color_applied"        # color barcode scanned, item resolved


@dataclass
class ScanEvent:
    event_type: ScanEventType
    message: str = ""
    mode: Optional[str] = None
    item: Optional[InventoryItem] = None
    results: list = field(default_factory=list)


@dataclass
class PendingScanItem:
    item: InventoryItem
    quantity: int = 1
    # Price snapshot at scan time: item.sell_price if set, else part_type.default_price
    unit_price: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))

    @property
    def predicted_after(self) -> int:
        """Stock after this operation (depends on session mode set externally)."""
        return self._predicted

    @predicted_after.setter
    def predicted_after(self, val: int):
        self._predicted = val

    @property
    def line_total(self) -> float:
        """Unit price × quantity for this line."""
        return float(self.unit_price) * int(self.quantity)

    def __post_init__(self):
        self._predicted = self.item.stock
