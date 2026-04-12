"""app/services/audit_service.py — Inventory audit business logic."""
from __future__ import annotations

from typing import Optional

from app.models.audit import AuditLine, InventoryAudit
from app.repositories.audit_repo import AuditRepository
from app.services.stock_service import StockService
from app.core.logger import get_logger

_log = get_logger(__name__)


class AuditService:
    """Service layer for inventory audit operations."""

    def __init__(self) -> None:
        """Initialize with repository and stock service."""
        self._repo = AuditRepository()
        self._stock_svc = StockService()

    def get_all_audits(self) -> list[InventoryAudit]:
        """Fetch all audits."""
        return self._repo.get_all()

    def get_audit(self, audit_id: int) -> Optional[InventoryAudit]:
        """Fetch a single audit by ID."""
        return self._repo.get_by_id(audit_id)

    def create_audit(self, name: str, notes: str = "") -> int:
        """
        Create a new audit, populate it with all current inventory items.
        Returns audit ID.
        """
        if not name or not name.strip():
            raise ValueError("Audit name cannot be empty")

        # Create audit
        audit_id = self._repo.create(name.strip(), notes.strip())

        # Populate from current inventory
        self._repo.populate_from_inventory(audit_id)

        _log.info(f"Created audit: id={audit_id}, name={name}")
        return audit_id

    def get_audit_lines(self, audit_id: int) -> list[AuditLine]:
        """Fetch all lines for an audit."""
        audit = self.get_audit(audit_id)
        if not audit:
            raise ValueError(f"Audit {audit_id} not found")

        return self._repo.get_lines(audit_id)

    def record_count(self, line_id: int, counted_qty: int, note: str = "") -> None:
        """Record a count for a line."""
        if counted_qty < 0:
            raise ValueError("Counted qty cannot be negative")

        self._repo.update_line_count(line_id, counted_qty, note.strip())

    def complete_audit(self, audit_id: int) -> dict:
        """
        Complete an audit. Returns summary of discrepancies.
        Validates that at least one line has been counted.
        """
        audit = self.get_audit(audit_id)
        if not audit:
            raise ValueError(f"Audit {audit_id} not found")

        if audit.status != "IN_PROGRESS":
            raise ValueError(f"Cannot complete audit with status {audit.status}")

        if audit.counted_lines == 0:
            raise ValueError("Cannot complete audit with no counted items")

        # Mark as completed
        self._repo.update_status(audit_id, "COMPLETED")

        # Return updated audit with summary
        updated = self.get_audit(audit_id)
        if not updated:
            raise ValueError("Failed to fetch updated audit")

        result = {
            "total_lines": updated.total_lines,
            "counted_lines": updated.counted_lines,
            "discrepancies": updated.discrepancies,
        }
        _log.info(f"Completed audit: id={audit_id}, total_lines={updated.total_lines}, counted_lines={updated.counted_lines}, discrepancies={updated.discrepancies}")
        return result

    def cancel_audit(self, audit_id: int) -> None:
        """Cancel an audit."""
        audit = self.get_audit(audit_id)
        if not audit:
            raise ValueError(f"Audit {audit_id} not found")

        if audit.status not in ("IN_PROGRESS", "COMPLETED"):
            raise ValueError(f"Cannot cancel audit with status {audit.status}")

        self._repo.update_status(audit_id, "CANCELLED")
        _log.info(f"Cancelled audit: id={audit_id}")

    def apply_adjustments(self, audit_id: int) -> int:
        """
        Apply all discrepancies as stock adjustments.
        Only works if audit is COMPLETED.
        Returns count of adjustments applied.
        """
        audit = self.get_audit(audit_id)
        if not audit:
            raise ValueError(f"Audit {audit_id} not found")

        if audit.status != "COMPLETED":
            raise ValueError(f"Can only apply adjustments to COMPLETED audits, got {audit.status}")

        lines = self.get_audit_lines(audit_id)
        adjusted = 0

        for line in lines:
            if line.difference is not None and line.difference != 0:
                # If difference is negative, we need to reduce stock (stock_out)
                # If difference is positive, we need to increase stock (stock_in)
                note = f"Audit {audit_id}: {line.note}" if line.note else f"Audit {audit_id}"
                try:
                    if line.difference < 0:
                        # System has more than counted, so reduce
                        self._stock_svc.stock_out(
                            item_id=line.item_id,
                            quantity=abs(line.difference),
                            note=note,
                        )
                    else:
                        # System has less than counted, so increase
                        self._stock_svc.stock_in(
                            item_id=line.item_id,
                            quantity=line.difference,
                            note=note,
                        )
                    adjusted += 1
                except Exception as e:
                    # Log but continue with next line
                    _log.error(f"Failed to adjust item {line.item_id} in audit {audit_id}: {e}")
                    continue

        _log.info(f"Applied adjustments for audit: id={audit_id}, adjustments_applied={adjusted}")
        return adjusted

    def get_summary(self) -> dict:
        """Get global audit summary."""
        return self._repo.get_summary()
