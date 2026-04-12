"""app/models/audit.py — Inventory audit data models."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class InventoryAudit:
    """Represents a single inventory audit session."""

    id: int = 0
    name: str = ""
    status: str = "IN_PROGRESS"  # IN_PROGRESS, COMPLETED, CANCELLED
    notes: str = ""
    started_at: str = ""
    completed_at: str | None = None
    # Computed properties (populated by repository)
    total_lines: int = 0
    counted_lines: int = 0
    discrepancies: int = 0

    @property
    def progress_percent(self) -> float:
        """Calculate progress as percentage of items counted."""
        if self.total_lines == 0:
            return 0.0
        return (self.counted_lines / self.total_lines) * 100

    @property
    def is_complete(self) -> bool:
        """Check if all lines have been counted."""
        return self.total_lines > 0 and self.counted_lines == self.total_lines


@dataclass
class AuditLine:
    """Represents a single line item in an audit."""

    id: int = 0
    audit_id: int = 0
    item_id: int = 0
    item_name: str = ""
    barcode: str = ""
    system_qty: int = 0
    counted_qty: int | None = None
    difference: int | None = None
    note: str = ""

    @property
    def is_counted(self) -> bool:
        """Check if this line has been counted."""
        return self.counted_qty is not None

    @property
    def has_discrepancy(self) -> bool:
        """Check if counted qty differs from system qty."""
        if self.difference is None:
            return False
        return self.difference != 0
