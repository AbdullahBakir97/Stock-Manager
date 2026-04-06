"""app/models — Domain model dataclasses."""
from .category import CategoryConfig, PartTypeConfig
from .phone_model import PhoneModel
from .item import InventoryItem
from .transaction import InventoryTransaction
from .supplier import Supplier, SupplierItem
from .location import Location, LocationStock, StockTransfer
from .sale import Sale, SaleItem

__all__ = [
    "CategoryConfig", "PartTypeConfig",
    "PhoneModel",
    "InventoryItem",
    "InventoryTransaction",
    "Supplier", "SupplierItem",
    "Location", "LocationStock", "StockTransfer",
    "Sale", "SaleItem",
]
