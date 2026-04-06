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
