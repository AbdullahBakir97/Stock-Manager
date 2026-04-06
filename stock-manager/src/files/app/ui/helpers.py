"""
app/ui/helpers.py — Shared UI helper functions.
"""
from __future__ import annotations

from PyQt6.QtGui import QColor

from app.core.theme import THEME
from app.models.item import InventoryItem


def _sc(s: int, thr: int) -> QColor:
    """Stock color based on level vs threshold."""
    tk = THEME.tokens
    if s == 0:              return QColor(tk.red)
    if s <= max(1, thr//2): return QColor(tk.orange)
    if s <= thr:            return QColor(tk.yellow)
    return QColor(tk.green)


def _sl(s: int, thr: int) -> str:
    """Stock level label string."""
    if s == 0:              return "OUT"
    if s <= max(1, thr//2): return "CRITICAL"
    if s <= thr:            return "LOW"
    return "OK"


def _to_op_dict(item: InventoryItem) -> dict:
    """Build a StockOpDialog-compatible dict from any InventoryItem."""
    return {
        "id":                  item.id,
        "brand":               item.model_brand or item.brand,
        "type":                item.part_type_name or item.name,
        "color":               "" if not item.is_product else item.color,
        "stock":               item.stock,
        "low_stock_threshold": item.min_stock,
        "barcode":             item.barcode,
        "sell_price":          item.sell_price,
        "updated_at":          item.updated_at,
    }


def _to_edit_dict(item: InventoryItem) -> dict:
    """Build a ProductDialog-compatible dict from a standalone InventoryItem."""
    return {
        "brand":               item.brand,
        "type":                item.name,
        "color":               item.color,
        "barcode":             item.barcode,
        "low_stock_threshold": item.min_stock,
        "sell_price":          item.sell_price,
        "image_path":          item.image_path,
        "expiry_date":         item.expiry_date,
        "warranty_date":       item.warranty_date,
    }
