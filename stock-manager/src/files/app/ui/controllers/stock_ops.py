"""
app/ui/controllers/stock_ops.py — Stock in/out/adjust operations.

Extracted from MainWindow to reduce file size.
All functions accept `win` (the MainWindow instance) as first argument.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMessageBox, QDialog

from app.core.i18n import t
from app.ui.dialogs.product_dialogs import StockOpDialog
from app.ui.helpers import _to_op_dict

if TYPE_CHECKING:
    from app.ui.main_window import MainWindow
    from app.models.item import InventoryItem

from app.repositories.item_repo import ItemRepository
from app.services.stock_service import StockService
from app.services.undo_service import UndoService
from app.services.undo_manager import UNDO, Command

_item_repo = ItemRepository()
_stock_svc = StockService()
_undo_svc = UndoService()


def _push_stock_undo(item_id: int, op: str, qty: int, item_label: str) -> None:
    """Push a stock operation onto the global undo stack.

    For IN → undo is stock_out, redo is stock_in.
    For OUT → undo is stock_in, redo is stock_out.
    For ADJUST → undo sets the previous value, redo sets the new value.
    """
    if op == "IN":
        UNDO.push(Command(
            label=f"Stock IN {item_label} (+{qty})",
            undo_fn=lambda: _stock_svc.stock_out(item_id, qty, "undo"),
            redo_fn=lambda: _stock_svc.stock_in(item_id, qty, "redo"),
        ))
    elif op == "OUT":
        UNDO.push(Command(
            label=f"Stock OUT {item_label} (-{qty})",
            undo_fn=lambda: _stock_svc.stock_in(item_id, qty, "undo"),
            redo_fn=lambda: _stock_svc.stock_out(item_id, qty, "redo"),
        ))


# ── Stock Dialog Operation ──────────────────────────────────────────────────

def stock_op(win: MainWindow, op: str) -> None:
    """Open StockOpDialog for IN/OUT/ADJUST on the current product."""
    if not win._cp:
        return
    item = _item_repo.get_by_id(win._cp.id)
    if item is None:
        QMessageBox.warning(win, t("msg_not_found_title"), t("msg_not_found_body"))
        return
    dlg = StockOpDialog(win, product=_to_op_dict(item), operation=op)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return
    data = dlg.get_data()
    try:
        qty = data["quantity"]
        before_stock = item.stock
        if op == "IN":
            res = _stock_svc.stock_in(item.id, qty, data["note"])
            _push_stock_undo(item.id, "IN", qty, item.display_name)
        elif op == "OUT":
            res = _stock_svc.stock_out(item.id, qty, data["note"])
            _push_stock_undo(item.id, "OUT", qty, item.display_name)
        else:
            res = _stock_svc.stock_adjust(item.id, qty, data["note"])
            # ADJUST: undo restores the previous stock value, redo sets the new
            iid, name, prev_st, new_st = item.id, item.display_name, before_stock, qty
            UNDO.push(Command(
                label=f"Adjust {name} ({prev_st} → {new_st})",
                undo_fn=lambda: _stock_svc.stock_adjust(iid, prev_st, "undo"),
                redo_fn=lambda: _stock_svc.stock_adjust(iid, new_st, "redo"),
            ))

        # ── Targeted UI update (much faster than _refresh_all) ────────────
        updated = _item_repo.get_by_id(item.id)
        if updated:
            # Update only the affected table row; fall back to full redraw
            # only if the row wasn't found (e.g. filter hid it).
            if not win._inv_page.table.update_row_by_id(updated):
                win._refresh_products()
            # Sync detail panel and current-product pointer
            win._cp = updated
            win._inv_page.detail.set_product(updated)
        win._refresh_summary()   # update dashboard KPI cards
        win._alert_ctrl.refresh()
        # ─────────────────────────────────────────────────────────────────

        win._show_status(
            t("status_stock_op", op=op, before=res["before"], after=res["after"]),
            4000, level="ok",
        )
        _offer_undo_toast(win, item.id, op, res)

        if updated and updated.stock <= updated.min_stock:
            level = t("msg_level_out") if updated.stock == 0 else t("msg_level_low")
            QMessageBox.warning(
                win, t("msg_low_title", level=level),
                t("msg_low_body", brand=updated.display_name, type="", color="",
                  stock=updated.stock, thr=updated.min_stock),
            )
    except ValueError as e:
        QMessageBox.warning(win, t("msg_op_failed"), str(e))
    except Exception as e:
        QMessageBox.critical(win, t("msg_error"), str(e))


# ── Context Menu Handlers ───────────────────────────────────────────────────

def ctx_stock_op(win: MainWindow, item: InventoryItem, op: str) -> None:
    """Handle context-menu stock operation on a specific item."""
    win._cp = item
    win._inv_page.detail.set_product(item)
    stock_op(win, op)


def ctx_edit(win: MainWindow, item: InventoryItem) -> None:
    """Handle context-menu edit on a specific item."""
    from app.ui.controllers.inventory_ops import edit_product
    win._cp = item
    win._inv_page.detail.set_product(item)
    edit_product(win)


def ctx_delete(win: MainWindow, item: InventoryItem) -> None:
    """Handle context-menu delete on a specific item."""
    from app.ui.controllers.inventory_ops import delete_product
    win._cp = item
    win._inv_page.detail.set_product(item)
    delete_product(win)


def ctx_view_txns(win: MainWindow, item: InventoryItem) -> None:
    """Navigate to transactions filtered by item."""
    win._nav_ctrl.go("nav_transactions")
    win._txn_page._search.setText(item.display_name)


# ── Quick Inline Stock +1 / -1 ─────────────────────────────────────────────

def quick_stock_in(win: MainWindow, item_id: int) -> None:
    """Increment stock by 1 with lightweight row update."""
    try:
        res = _stock_svc.stock_in(item_id, 1, "Quick +1")
        updated_item = _item_repo.get_by_id(item_id)
        if updated_item:
            win._inv_page.table.update_row_by_id(updated_item)
            if win._cp and win._cp.id == item_id:
                win._cp = updated_item
                win._inv_page.detail.set_product(updated_item)
            _push_stock_undo(item_id, "IN", 1, updated_item.display_name)
        win._refresh_summary()
        win._show_status(t("status_quick_in"), 2000, level="ok")
    except Exception as e:
        QMessageBox.warning(win, t("msg_error"), str(e))


def quick_stock_out(win: MainWindow, item_id: int) -> None:
    """Decrement stock by 1 with lightweight row update."""
    try:
        res = _stock_svc.stock_out(item_id, 1, "Quick -1")
        updated_item = _item_repo.get_by_id(item_id)
        if updated_item:
            win._inv_page.table.update_row_by_id(updated_item)
            if win._cp and win._cp.id == item_id:
                win._cp = updated_item
                win._inv_page.detail.set_product(updated_item)
            _push_stock_undo(item_id, "OUT", 1, updated_item.display_name)
        win._refresh_summary()
        win._show_status(t("status_quick_out"), 2000, level="ok")
    except Exception as e:
        QMessageBox.warning(win, t("msg_error"), str(e))


# ── Undo Support ────────────────────────────────────────────────────────────

def _offer_undo_toast(win: MainWindow, item_id: int, op: str, res: dict) -> None:
    """Show a toast with an Undo button after a stock operation."""
    if not hasattr(win, '_toasts') or win._toasts is None:
        return
    # Find the latest transaction for this item to get its ID
    recent = _undo_svc.get_recent_undoable(limit=1)
    if not recent:
        return
    txn_id = recent[0]["id"]

    msg = t("status_stock_op", op=op, before=res["before"], after=res["after"])
    win._toasts.success(
        msg, duration=8000,
        action_text=t("undo_btn"),
        action_callback=lambda: _do_undo(win, txn_id),
    )


def _do_undo(win: MainWindow, txn_id: int) -> None:
    """Execute undo for a transaction and refresh the UI."""
    try:
        result = _undo_svc.undo_transaction(txn_id)
        item_id = result.get("item_id")
        if item_id:
            updated = _item_repo.get_by_id(item_id)
            if updated:
                if not win._inv_page.table.update_row_by_id(updated):
                    win._refresh_products()
                win._cp = updated
                win._inv_page.detail.set_product(updated)
        win._refresh_summary()
        win._alert_ctrl.refresh()
        win._show_status(
            t("undo_success", before=result["before"], after=result["after"]),
            4000, level="ok",
        )
    except ValueError as e:
        QMessageBox.warning(win, t("msg_op_failed"), str(e))
