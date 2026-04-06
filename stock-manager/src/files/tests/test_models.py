"""
tests/test_models.py — Tests for data model computed properties.

Tests cover InventoryItem, Product, and Transaction dataclass behavior.
"""
from __future__ import annotations

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.item import InventoryItem


def _item(**overrides) -> InventoryItem:
    """Factory for creating test InventoryItems with sensible defaults."""
    defaults = dict(
        id=1, brand="Apple", name="Screen", color="Clear", sku=None,
        barcode="BC-001", sell_price=9.99, stock=50, min_stock=10,
        inventur=None, model_id=None, part_type_id=None, is_active=True,
        created_at="2025-01-01", updated_at="2025-01-01",
    )
    defaults.update(overrides)
    return InventoryItem(**defaults)


class TestInventoryItemProperties(unittest.TestCase):
    """Test computed properties on InventoryItem."""

    def test_is_product_standalone(self):
        item = _item(model_id=None)
        self.assertTrue(item.is_product)

    def test_is_product_matrix(self):
        item = _item(model_id=1, part_type_id=2)
        self.assertFalse(item.is_product)

    def test_best_bung_positive(self):
        item = _item(stock=50, min_stock=10)
        self.assertEqual(item.best_bung, 40)

    def test_best_bung_negative(self):
        item = _item(stock=3, min_stock=10)
        self.assertEqual(item.best_bung, -7)

    def test_best_bung_zero(self):
        item = _item(stock=10, min_stock=10)
        self.assertEqual(item.best_bung, 0)

    def test_needs_reorder_true(self):
        item = _item(stock=5, min_stock=10)
        self.assertTrue(item.needs_reorder)

    def test_needs_reorder_false(self):
        item = _item(stock=50, min_stock=10)
        self.assertFalse(item.needs_reorder)

    def test_needs_reorder_zero_threshold(self):
        item = _item(stock=0, min_stock=0)
        self.assertFalse(item.needs_reorder)

    def test_is_low_true(self):
        item = _item(stock=5, min_stock=10)
        self.assertTrue(item.is_low)

    def test_is_low_false_above(self):
        item = _item(stock=50, min_stock=10)
        self.assertFalse(item.is_low)

    def test_is_low_false_zero(self):
        item = _item(stock=0, min_stock=10)
        self.assertFalse(item.is_low)

    def test_is_out_true(self):
        item = _item(stock=0)
        self.assertTrue(item.is_out)

    def test_is_out_false(self):
        item = _item(stock=1)
        self.assertFalse(item.is_out)

    def test_display_name_product(self):
        item = _item(brand="Apple", name="Screen", color="Clear")
        self.assertEqual(item.display_name, "Apple Screen Clear")

    def test_display_name_product_no_color(self):
        item = _item(brand="Apple", name="Screen", color="")
        self.assertEqual(item.display_name, "Apple Screen")

    def test_display_name_matrix(self):
        item = _item(
            model_id=1, part_type_id=2,
            model_name="iPhone 15", part_type_name="Display", color="Black"
        )
        self.assertEqual(item.display_name, "iPhone 15  ·  Display  ·  Black")

    def test_display_name_fallback(self):
        item = _item(id=42, brand="", name="", color="")
        self.assertEqual(item.display_name, "Item #42")


class TestInventoryItemEdgeCases(unittest.TestCase):
    """Test edge cases for InventoryItem."""

    def test_very_large_stock(self):
        item = _item(stock=999999, min_stock=100)
        self.assertEqual(item.best_bung, 999899)
        self.assertFalse(item.needs_reorder)

    def test_zero_stock_zero_threshold(self):
        item = _item(stock=0, min_stock=0)
        self.assertFalse(item.needs_reorder)
        self.assertFalse(item.is_low)
        self.assertTrue(item.is_out)

    def test_sell_price_none(self):
        item = _item(sell_price=None)
        self.assertIsNone(item.sell_price)

    def test_barcode_none(self):
        item = _item(barcode=None)
        self.assertIsNone(item.barcode)


if __name__ == "__main__":
    unittest.main()
