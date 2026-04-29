"""app/services/scan_session_service.py — Manages Quick Scan sessions.

Two-step color scanning:
  1. Scan item barcode → if item has colored variants, enters "waiting for color"
  2. Scan color barcode (CLR-BLACK, CLR-BLUE, etc.) → resolves to exact colored item
  3. If item has NO colors, adds directly to pending (single step)
"""
from __future__ import annotations
from typing import Optional

from app.core.scan_config import ScanConfig
from app.repositories.item_repo import ItemRepository
from app.repositories.category_repo import CategoryRepository
from app.repositories.invoice_repo import InvoiceRepository
from app.services.stock_service import StockService
from app.models.scan_session import PendingScanItem, ScanEvent, ScanEventType
from app.models.item import InventoryItem
from app.core.i18n import t

_item_repo = ItemRepository()
_cat_repo = CategoryRepository()
_invoice_repo = InvoiceRepository()
_stock_svc = StockService()


def _resolve_unit_price(item: InventoryItem) -> float:
    """Return the unit price for an item.

    Priority: per-item sell_price (if set) > part_type.default_price > 0.
    """
    sp = getattr(item, "sell_price", None)
    if sp is not None:
        try:
            return float(sp)
        except (TypeError, ValueError):
            pass
    pt_id = getattr(item, "part_type_id", None)
    if pt_id:
        try:
            from app.core.database import get_connection
            with get_connection() as conn:
                row = conn.execute(
                    "SELECT default_price FROM part_types WHERE id=?", (pt_id,),
                ).fetchone()
            if row and row["default_price"] is not None:
                return float(row["default_price"])
        except Exception:
            pass
    return 0.0


class ScanSessionService:
    """Stateful service managing a Quick Scan session with color support.

    Workflow:
    1. Scan command barcode → sets mode (TAKEOUT or INSERT)
    2. Scan item barcode:
       a) If item has colored variants → enters WAITING_COLOR state
       b) If no colors → adds directly to pending
    3. Scan color barcode → resolves waiting item + color → adds to pending
    4. Scan confirm barcode → commits all pending operations
    """

    def __init__(self):
        self._mode: Optional[str] = None
        self._pending: list[PendingScanItem] = []
        # Two-step color scan state
        self._waiting_item: Optional[InventoryItem] = None  # the scanned item waiting for color
        self._waiting_colors: list[str] = []  # available colors for the waiting item

    @property
    def mode(self) -> Optional[str]:
        return self._mode

    @property
    def waiting_for_color(self) -> bool:
        return self._waiting_item is not None

    @property
    def waiting_item_name(self) -> str:
        return self._waiting_item.display_name if self._waiting_item else ""

    @property
    def available_colors(self) -> list[str]:
        return list(self._waiting_colors)

    @property
    def pending_items(self) -> list[PendingScanItem]:
        return list(self._pending)

    @property
    def pending_count(self) -> int:
        return sum(p.quantity for p in self._pending)

    @property
    def pending_item_count(self) -> int:
        return len(self._pending)

    @property
    def subtotal(self) -> float:
        """Sum of all line totals in the pending list."""
        return sum(p.line_total for p in self._pending)

    @property
    def total(self) -> float:
        """Grand total (same as subtotal for now — no tax/discount)."""
        return self.subtotal

    def process_barcode(self, barcode: str) -> ScanEvent:
        """Process a scanned barcode."""
        cfg = ScanConfig.get()
        cmd = cfg.command_type(barcode)

        # ── Command barcodes ──
        if cmd == "TAKEOUT":
            if self._mode and self._pending:
                return ScanEvent(ScanEventType.SESSION_ACTIVE,
                                 t("qscan_session_active", mode=self._mode),
                                 mode=self._mode)
            self._mode = "TAKEOUT"
            self._pending.clear()
            self._clear_waiting()
            return ScanEvent(ScanEventType.MODE_CHANGED,
                             t("qscan_mode_takeout"), mode="TAKEOUT")

        if cmd == "INSERT":
            if self._mode and self._pending:
                return ScanEvent(ScanEventType.SESSION_ACTIVE,
                                 t("qscan_session_active", mode=self._mode),
                                 mode=self._mode)
            self._mode = "INSERT"
            self._pending.clear()
            self._clear_waiting()
            return ScanEvent(ScanEventType.MODE_CHANGED,
                             t("qscan_mode_insert"), mode="INSERT")

        if cmd == "CONFIRM":
            self._clear_waiting()
            if not self._pending:
                return ScanEvent(ScanEventType.BATCH_EMPTY,
                                 t("qscan_pending_empty"))
            return self.commit()

        # ── No active mode ──
        if not self._mode:
            return ScanEvent(ScanEventType.NO_MODE, t("qscan_no_mode"))

        # ── Check if this is a color barcode while waiting ──
        if self._waiting_item:
            color = cfg.color_name(barcode)
            if color:
                return self._resolve_color(color)
            else:
                # Not a color barcode — cancel waiting and try as new item
                self._clear_waiting()

        # ── Look up item by barcode ──
        item = _item_repo.get_by_barcode(barcode)
        if not item:
            return ScanEvent(ScanEventType.NOT_FOUND,
                             t("qscan_not_found", bc=barcode))

        # Direct-colour barcode: the scan resolved straight to a coloured
        # variant (e.g. "S-S22-DSP-BK"), so we skip the two-step "scan model
        # → scan colour" wait state and add the exact item immediately.
        # The two-step flow still works for users who scan the colourless
        # parent — that path falls through to the colored-siblings check
        # below.
        if item.color:
            return self._add_item(item)

        # ── Check if item has colored variants ──
        if item.model_id and item.part_type_id:
            colored = _item_repo.get_colored_siblings(item.model_id, item.part_type_id)
            if colored:
                # This item has colored variants — enter waiting state
                self._waiting_item = item
                self._waiting_colors = [c.color for c in colored]
                colors_str = ", ".join(self._waiting_colors)
                return ScanEvent(ScanEventType.WAITING_COLOR,
                                 t("qscan_scan_color", name=item.display_name,
                                   colors=colors_str),
                                 item=item)

        # ── No colors — add directly ──
        return self._add_item(item)

    def _resolve_color(self, color: str) -> ScanEvent:
        """Resolve a color barcode to the exact colored item."""
        if not self._waiting_item:
            return ScanEvent(ScanEventType.NOT_FOUND, "No item waiting for color")

        # Find the colored variant
        colored_item = _item_repo.get_by_model_parttype_color(
            self._waiting_item.model_id,
            self._waiting_item.part_type_id,
            color,
        )
        self._clear_waiting()

        if not colored_item:
            return ScanEvent(ScanEventType.NOT_FOUND,
                             t("qscan_color_not_found", color=color))

        return self._add_item(colored_item)

    def _add_item(self, item: InventoryItem) -> ScanEvent:
        """Add an item to the pending list."""
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

        # New item — snapshot price at scan time
        unit_price = _resolve_unit_price(item)
        pending = PendingScanItem(item=item, unit_price=unit_price)
        self._pending.append(pending)
        self._recalc_predictions()
        return ScanEvent(ScanEventType.ITEM_ADDED,
                         t("qscan_item_added",
                           name=item.display_name, qty=1),
                         item=item)

    def _clear_waiting(self):
        self._waiting_item = None
        self._waiting_colors.clear()

    def commit(self, *, layout: str = "a4", customer_name: str = "") -> ScanEvent:
        """Execute all pending operations AND write an invoice record.

        The `layout` hint ('a4' | 'thermal') is stored on the invoice and
        read later by ScanInvoiceService to render the PDF. The invoice id
        is returned via ScanEvent.results[0]['invoice_id'] when any line
        committed successfully (and via the top-level invoice_id attr).
        """
        results = []
        ok_count = 0
        fail_count = 0

        # Snapshot pending rows BEFORE mutating stock (we need the original
        # prices & descriptions for the invoice record).
        invoice_items: list[dict] = []
        from app.core.config import ShopConfig
        currency = ShopConfig.get().currency or "€"

        for p in self._pending:
            try:
                if self._mode == "TAKEOUT":
                    res = _stock_svc.stock_out(p.item.id, p.quantity, "Quick Scan")
                else:
                    res = _stock_svc.stock_in(p.item.id, p.quantity, "Quick Scan")
                results.append({"item": p.item, "qty": p.quantity,
                                "before": res["before"], "after": res["after"],
                                "unit_price": p.unit_price,
                                "line_total": p.line_total,
                                "ok": True})
                invoice_items.append({
                    "item_id": p.item.id,
                    "item_snapshot": p.item.display_name,
                    "barcode": getattr(p.item, "barcode", "") or "",
                    "quantity": p.quantity,
                    "unit_price": p.unit_price,
                    "line_total": p.line_total,
                })
                ok_count += 1
            except (ValueError, Exception) as e:
                results.append({"item": p.item, "qty": p.quantity,
                                "error": str(e), "ok": False})
                fail_count += 1

        mode = self._mode

        # Persist the invoice if anything committed successfully
        invoice_id: Optional[int] = None
        if invoice_items:
            try:
                invoice_id = _invoice_repo.create_invoice(
                    operation=mode or "OUT",
                    layout=(layout or "a4").lower(),
                    customer_name=customer_name or "",
                    currency=currency,
                    items=invoice_items,
                    note="Quick Scan",
                )
            except Exception:
                # Stock already moved; failing invoice storage shouldn't block
                invoice_id = None

        self._mode = None
        self._pending.clear()
        self._clear_waiting()

        if fail_count == 0:
            msg = t("qscan_committed", n=ok_count)
        else:
            msg = t("qscan_commit_partial", ok=ok_count, fail=fail_count)

        ev = ScanEvent(ScanEventType.BATCH_COMMITTED, msg,
                       mode=mode, results=results)
        # Expose invoice id for the UI without changing ScanEvent schema
        setattr(ev, "invoice_id", invoice_id)
        return ev

    def cancel(self) -> None:
        self._mode = None
        self._pending.clear()
        self._clear_waiting()

    def remove_pending(self, index: int) -> None:
        if 0 <= index < len(self._pending):
            self._pending.pop(index)
            self._recalc_predictions()

    def _recalc_predictions(self) -> None:
        qty_map: dict[int, int] = {}
        for p in self._pending:
            qty_map[p.item.id] = qty_map.get(p.item.id, 0) + p.quantity
        for p in self._pending:
            total_qty = qty_map.get(p.item.id, p.quantity)
            if self._mode == "TAKEOUT":
                p.predicted_after = p.item.stock - total_qty
            else:
                p.predicted_after = p.item.stock + total_qty
