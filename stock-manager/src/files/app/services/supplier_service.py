"""app/services/supplier_service.py — Supplier business logic."""
from __future__ import annotations

from typing import Optional

from app.repositories.supplier_repo import SupplierRepository
from app.models.supplier import Supplier, SupplierItem
from app.core.logger import get_logger

_log = get_logger(__name__)


class SupplierService:

    def __init__(self) -> None:
        self._repo = SupplierRepository()

    # ── Supplier CRUD ────────────────────────────────────────────────────────

    def get_all(self, search: str = "", active_only: bool = True) -> list[Supplier]:
        return self._repo.get_all(search=search, active_only=active_only)

    def get_by_id(self, supplier_id: int) -> Optional[Supplier]:
        return self._repo.get_by_id(supplier_id)

    def add(self, name: str, **kwargs) -> int:
        name = name.strip()
        if not name:
            raise ValueError("Supplier name is required")
        sid = self._repo.add(name, **kwargs)
        _log.info(f"Added supplier: id={sid}, name={name}")
        return sid

    def update(self, supplier_id: int, name: str, **kwargs) -> None:
        name = name.strip()
        if not name:
            raise ValueError("Supplier name is required")
        self._repo.update(supplier_id, name, **kwargs)
        _log.info(f"Updated supplier: id={supplier_id}, name={name}")

    def delete(self, supplier_id: int) -> bool:
        result = self._repo.delete(supplier_id)
        if result:
            _log.info(f"Deleted supplier: id={supplier_id}")
        else:
            _log.warning(f"Cannot delete supplier {supplier_id}: linked to items with stock")
        return result

    def set_active(self, supplier_id: int, active: bool) -> None:
        self._repo.set_active(supplier_id, active)

    # ── Supplier-Item links ──────────────────────────────────────────────────

    def get_items(self, supplier_id: int) -> list[SupplierItem]:
        return self._repo.get_items(supplier_id)

    def get_suppliers_for_item(self, item_id: int) -> list[SupplierItem]:
        return self._repo.get_suppliers_for_item(item_id)

    def link_item(self, supplier_id: int, item_id: int,
                  cost_price: float = 0, lead_days: int = 0,
                  supplier_sku: str = "", is_preferred: bool = False) -> int:
        sid = self._repo.link_item(
            supplier_id, item_id, cost_price, lead_days,
            supplier_sku, is_preferred,
        )
        _log.info(f"Linked supplier {supplier_id} -> item {item_id}, cost={cost_price}")
        return sid

    def unlink_item(self, supplier_id: int, item_id: int) -> None:
        self._repo.unlink_item(supplier_id, item_id)
        _log.info(f"Unlinked supplier {supplier_id} -> item {item_id}")

    def get_preferred_cost(self, item_id: int) -> Optional[float]:
        """Return cost price from the preferred supplier, or None."""
        suppliers = self._repo.get_suppliers_for_item(item_id)
        for s in suppliers:
            if s.is_preferred:
                return s.cost_price
        return suppliers[0].cost_price if suppliers else None

    def get_summary(self) -> dict:
        """Get summary statistics for suppliers."""
        return self._repo.get_summary()
