"""
app/ui/controllers/bulk_ops.py — Bulk inventory operations.

Extracted from MainWindow to reduce file size.
All functions accept `win` (the MainWindow instance) as first argument.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMessageBox, QDialog

from app.core.i18n import t
from app.ui.dialogs.bulk_price_dialog import BulkPriceDialog

if TYPE_CHECKING:
    from app.ui.main_window import MainWindow

from app.repositories.item_repo import ItemRepository
from app.services.stock_service import StockService

_item_repo = ItemRepository()
_stock_svc = StockService()


# ── Bulk Stock In/Out ───────────────────────────────────────────────────────

def bulk_op(win: MainWindow, items: list, op: str) -> None:
    """Apply stock IN or OUT to multiple items at once."""
    if not items:
        return
    from PyQt6.QtWidgets import QInputDialog
    qty, ok = QInputDialog.getInt(
        win, t("bulk_confirm_title"),
        t("bulk_qty_prompt"), value=1, min=1, max=9999,
    )
    if not ok:
        return
    confirm_key = "bulk_confirm_in" if op == "IN" else "bulk_confirm_out"
    ans = QMessageBox.question(
        win, t("bulk_confirm_title"), t(confirm_key, qty=qty, n=len(items)),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if ans != QMessageBox.StandardButton.Yes:
        return
    note = t("bulk_note", op=op)
    errors = 0
    for item in items:
        try:
            if op == "IN":
                _stock_svc.stock_in(item.id, qty, note)
            else:
                _stock_svc.stock_out(item.id, qty, note)
        except Exception:
            errors += 1
    win._refresh_all()
    win._show_status(
        t("bulk_success", n=len(items) - errors), 4000,
        level="ok" if errors == 0 else "warn",
    )


# ── Bulk Delete ─────────────────────────────────────────────────────────────

def bulk_delete(win: MainWindow, items: list) -> None:
    """Delete multiple items at once after confirmation."""
    if not items:
        return
    ans = QMessageBox.question(
        win, t("bulk_confirm_title"), t("bulk_confirm_delete", n=len(items)),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if ans != QMessageBox.StandardButton.Yes:
        return
    errors = 0
    for item in items:
        try:
            _item_repo.delete(item.id)
        except Exception:
            errors += 1
    win._cp = None
    win._inv_page.detail.set_product(None)
    win._refresh_all()
    win._show_status(
        t("bulk_success", n=len(items) - errors), 4000,
        level="ok" if errors == 0 else "warn",
    )


# ── Bulk Price Update ───────────────────────────────────────────────────────

def bulk_price(win: MainWindow, items: list) -> None:
    """Update prices for multiple items using set/markup/discount modes."""
    if not items:
        return
    dlg = BulkPriceDialog(win, count=len(items))
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return
    result = dlg.get_result()
    if not result:
        return
    mode, val = result["mode"], result["value"]
    errors = 0
    for item in items:
        try:
            if mode == 0:
                new_price = val
            elif mode == 1:
                new_price = round((item.sell_price or 0) * (1 + val / 100), 2)
            else:
                new_price = round(max(0, (item.sell_price or 0) * (1 - val / 100)), 2)
            _item_repo.update_price(item.id, new_price)
        except Exception:
            errors += 1
    win._refresh_all()
    win._show_status(
        t("bulk_price_done", n=len(items) - errors), 4000,
        level="ok" if errors == 0 else "warn",
    )
