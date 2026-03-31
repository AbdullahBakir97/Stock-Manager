"""app/services/scan_session_service.py — Manages Quick Scan sessions."""
from __future__ import annotations
from typing import Optional

from app.core.scan_config import ScanConfig
from app.repositories.item_repo import ItemRepository
from app.services.stock_service import StockService
from app.models.scan_session import PendingScanItem, ScanEvent, ScanEventType
from app.core.i18n import t

_item_repo = ItemRepository()
_stock_svc = StockService()


class ScanSessionService:
    """Stateful service managing a single Quick Scan session.

    Workflow:
    1. Scan command barcode → sets mode (TAKEOUT or INSERT)
    2. Scan item barcodes → adds to pending list
    3. Scan confirm barcode → commits all pending operations
    """

    def __init__(self):
        self._mode: Optional[str] = None  # "TAKEOUT" | "INSERT" | None
        self._pending: list[PendingScanItem] = []

    @property
    def mode(self) -> Optional[str]:
        return self._mode

    @property
    def pending_items(self) -> list[PendingScanItem]:
        return list(self._pending)

    @property
    def pending_count(self) -> int:
        return sum(p.quantity for p in self._pending)

    @property
    def pending_item_count(self) -> int:
        return len(self._pending)

    def process_barcode(self, barcode: str) -> ScanEvent:
        """Process a scanned barcode. Returns a ScanEvent describing what happened."""
        cfg = ScanConfig.get()
        cmd = cfg.command_type(barcode)

        if cmd == "TAKEOUT":
            if self._mode and self._pending:
                return ScanEvent(ScanEventType.SESSION_ACTIVE,
                                 t("qscan_session_active", mode=self._mode),
                                 mode=self._mode)
            self._mode = "TAKEOUT"
            self._pending.clear()
            return ScanEvent(ScanEventType.MODE_CHANGED,
                             t("qscan_mode_takeout"), mode="TAKEOUT")

        if cmd == "INSERT":
            if self._mode and self._pending:
                return ScanEvent(ScanEventType.SESSION_ACTIVE,
                                 t("qscan_session_active", mode=self._mode),
                                 mode=self._mode)
            self._mode = "INSERT"
            self._pending.clear()
            return ScanEvent(ScanEventType.MODE_CHANGED,
                             t("qscan_mode_insert"), mode="INSERT")

        if cmd == "CONFIRM":
            if not self._pending:
                return ScanEvent(ScanEventType.BATCH_EMPTY,
                                 t("qscan_pending_empty"))
            return self.commit()

        # Not a command — look up item
        if not self._mode:
            return ScanEvent(ScanEventType.NO_MODE, t("qscan_no_mode"))

        item = _item_repo.get_by_barcode(barcode)
        if not item:
            return ScanEvent(ScanEventType.NOT_FOUND,
                             t("qscan_not_found", bc=barcode))

        # Check stock for takeout
        if self._mode == "TAKEOUT" and item.stock <= 0:
            return ScanEvent(ScanEventType.INSUFFICIENT_STOCK,
                             t("qscan_out_of_stock", name=item.display_name),
                             item=item)

        # Check if already in pending — increment qty
        for p in self._pending:
            if p.item.id == item.id:
                p.quantity += 1
                self._recalc_predictions()
                return ScanEvent(ScanEventType.ITEM_INCREMENTED,
                                 t("qscan_item_incremented",
                                   name=item.display_name, qty=p.quantity),
                                 item=item)

        # New item
        pending = PendingScanItem(item=item)
        self._pending.append(pending)
        self._recalc_predictions()
        return ScanEvent(ScanEventType.ITEM_ADDED,
                         t("qscan_item_added",
                           name=item.display_name, qty=1),
                         item=item)

    def commit(self) -> ScanEvent:
        """Execute all pending operations and clear the session."""
        results = []
        ok_count = 0
        fail_count = 0

        for p in self._pending:
            try:
                if self._mode == "TAKEOUT":
                    res = _stock_svc.stock_out(p.item.id, p.quantity, "Quick Scan")
                else:
                    res = _stock_svc.stock_in(p.item.id, p.quantity, "Quick Scan")
                results.append({"item": p.item, "qty": p.quantity,
                                "before": res["before"], "after": res["after"],
                                "ok": True})
                ok_count += 1
            except (ValueError, Exception) as e:
                results.append({"item": p.item, "qty": p.quantity,
                                "error": str(e), "ok": False})
                fail_count += 1

        mode = self._mode
        self._mode = None
        self._pending.clear()

        if fail_count == 0:
            msg = t("qscan_committed", n=ok_count)
        else:
            msg = t("qscan_commit_partial", ok=ok_count, fail=fail_count)

        return ScanEvent(ScanEventType.BATCH_COMMITTED, msg,
                         mode=mode, results=results)

    def cancel(self) -> None:
        """Cancel current session without committing."""
        self._mode = None
        self._pending.clear()

    def remove_pending(self, index: int) -> None:
        """Remove one item from the pending list."""
        if 0 <= index < len(self._pending):
            self._pending.pop(index)
            self._recalc_predictions()

    def _recalc_predictions(self) -> None:
        """Recalculate predicted stock-after for all pending items."""
        # Group quantities by item ID
        qty_map: dict[int, int] = {}
        for p in self._pending:
            qty_map[p.item.id] = qty_map.get(p.item.id, 0) + p.quantity

        for p in self._pending:
            total_qty = qty_map.get(p.item.id, p.quantity)
            if self._mode == "TAKEOUT":
                p.predicted_after = p.item.stock - total_qty
            else:
                p.predicted_after = p.item.stock + total_qty
