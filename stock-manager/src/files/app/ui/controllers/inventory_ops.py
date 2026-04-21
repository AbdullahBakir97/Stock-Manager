"""
app/ui/controllers/inventory_ops.py — Product CRUD operations.

Extracted from MainWindow to reduce file size.
All functions accept `win` (the MainWindow instance) as first argument.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMessageBox, QDialog

from app.core.theme import THEME
from app.core.i18n import t
from app.ui.dialogs.product_dialogs import ProductDialog
from app.ui.helpers import _to_edit_dict

if TYPE_CHECKING:
    from app.ui.main_window import MainWindow

from app.repositories.item_repo import ItemRepository
from app.services.undo_manager import UNDO, Command
_item_repo = ItemRepository()


# ── Add Product ─────────────────────────────────────────────────────────────

def add_product(win: MainWindow, checked: bool = False, preset_barcode: str = "") -> None:
    """Open ProductDialog and create a new product."""
    dlg = ProductDialog(win)
    if preset_barcode:
        dlg.barcode_edit.setText(preset_barcode)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return
    data = dlg.get_data()
    try:
        pid = _item_repo.add_product(
            brand=data["brand"], name=data["type_"], color=data["color"],
            stock=data.get("stock", 0), barcode=data["barcode"],
            min_stock=data["low_stock_threshold"], sell_price=data.get("sell_price"),
            expiry_date=data.get("expiry_date"), warranty_date=data.get("warranty_date"),
        )
        # Handle product image
        img_src = data.get("image_source")
        if img_src:
            from app.services.image_service import ImageService
            stored = ImageService().save_image(img_src, pid)
            _item_repo.update_image(pid, stored)
        win._refresh_products()
        win._refresh_summary()
        win._inv_page.table.select_by_id(pid)
        win._show_status(t("status_product_added", pid=pid), 4000, level="ok")

        # Push undo: undo deletes the product, redo recreates it
        name = data["type_"]
        # Undo commands run on worker thread — keep DB-only, no UI calls
        def _redo(d=data):
            _item_repo.add_product(
                brand=d["brand"], name=d["type_"], color=d["color"],
                stock=d.get("stock", 0), barcode=d["barcode"],
                min_stock=d["low_stock_threshold"], sell_price=d.get("sell_price"),
                expiry_date=d.get("expiry_date"), warranty_date=d.get("warranty_date"),
            )
        UNDO.push(Command(
            label=f"Add product: {name}",
            undo_fn=lambda p=pid: _item_repo.delete(p),
            redo_fn=_redo,
        ))
    except Exception as e:
        QMessageBox.critical(win, t("msg_error"), str(e))


# ── Edit Product ────────────────────────────────────────────────────────────

def edit_product(win: MainWindow) -> None:
    """Open ProductDialog to edit the currently selected product."""
    if not win._cp:
        return
    if not win._cp.is_product:
        QMessageBox.information(
            win, t("btn_edit"),
            "Matrix items are edited through the category matrix view.\n"
            "Use the category tab to modify this item.",
        )
        return
    # Snapshot previous values for undo
    prev = win._cp
    prev_data = {
        "id": prev.id, "brand": prev.brand, "name": prev.name, "color": prev.color,
        "barcode": prev.barcode, "min_stock": prev.min_stock,
        "sell_price": prev.sell_price, "image_path": prev.image_path,
        "expiry_date": getattr(prev, "expiry_date", None),
        "warranty_date": getattr(prev, "warranty_date", None),
    }
    dlg = ProductDialog(win, product=_to_edit_dict(win._cp))
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return
    data = dlg.get_data()
    try:
        # Handle image change
        img_src = data.get("image_source")
        img_path = win._cp.image_path  # keep current by default
        if img_src == "":
            # User removed the image
            from app.services.image_service import ImageService
            ImageService().delete_image(win._cp.image_path or "")
            img_path = None
        elif img_src:
            # User picked a new image
            from app.services.image_service import ImageService
            img_svc = ImageService()
            img_svc.delete_image(win._cp.image_path or "")
            img_path = img_svc.save_image(img_src, win._cp.id)

        _item_repo.update_product(
            item_id=win._cp.id, brand=data["brand"], name=data["type_"],
            color=data["color"], barcode=data["barcode"],
            min_stock=data["low_stock_threshold"], sell_price=data.get("sell_price"),
            image_path=img_path,
            expiry_date=data.get("expiry_date"), warranty_date=data.get("warranty_date"),
        )
        win._refresh_all()
        win._show_status(t("status_product_updated"), 3000, level="ok")

        # Push undo: snapshot prev + current values (DB ops only, no UI calls)
        new_data = dict(data)
        new_data["id"] = prev.id
        def _restore(vals):
            _item_repo.update_product(
                item_id=vals["id"], brand=vals["brand"], name=vals.get("name") or vals.get("type_"),
                color=vals["color"], barcode=vals["barcode"],
                min_stock=vals.get("min_stock") or vals.get("low_stock_threshold"),
                sell_price=vals.get("sell_price"),
                image_path=vals.get("image_path"),
                expiry_date=vals.get("expiry_date"),
                warranty_date=vals.get("warranty_date"),
            )
        UNDO.push(Command(
            label=f"Edit product: {prev.display_name}",
            undo_fn=lambda p=prev_data: _restore(p),
            redo_fn=lambda n=new_data: _restore(n),
        ))
    except Exception as e:
        QMessageBox.critical(win, t("msg_error"), str(e))


# ── Delete Product ──────────────────────────────────────────────────────────

def delete_product(win: MainWindow) -> None:
    """Confirm and delete the currently selected product."""
    if not win._cp:
        return
    if not win._cp.is_product:
        QMessageBox.information(
            win, t("ctx_delete"),
            "Matrix items are managed through the category matrix view.\n"
            "Use the category tab to remove this item.",
        )
        return
    item = win._cp
    tk = THEME.tokens
    ans = QMessageBox.question(
        win, t("msg_delete_title"),
        t("msg_delete_body", brand=item.brand, type=item.name, color=item.color, red=tk.red),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if ans != QMessageBox.StandardButton.Yes:
        return
    try:
        _item_repo.delete(item.id)
        win._cp = None
        win._inv_page.detail.set_product(None)
        win._refresh_all()
        win._show_status(t("status_product_deleted"), 3000, level="ok")
    except Exception as e:
        QMessageBox.critical(win, t("msg_error"), str(e))
