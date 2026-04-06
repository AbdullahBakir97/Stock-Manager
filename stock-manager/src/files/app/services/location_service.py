"""app/services/location_service.py — Location and transfer business logic."""
from __future__ import annotations

from typing import Optional

from app.repositories.location_repo import LocationRepository
from app.models.location import Location, LocationStock, StockTransfer
from app.core.logger import get_logger

_log = get_logger(__name__)


class LocationService:

    def __init__(self) -> None:
        self._repo = LocationRepository()

    # ── Location CRUD ────────────────────────────────────────────────────────

    def get_all(self, active_only: bool = False) -> list[Location]:
        return self._repo.get_all(active_only=active_only)

    def get_by_id(self, location_id: int) -> Optional[Location]:
        return self._repo.get_by_id(location_id)

    def get_default(self) -> Optional[Location]:
        return self._repo.get_default()

    def add(self, name: str, description: str = "",
            is_default: bool = False) -> int:
        name = name.strip()
        if not name:
            raise ValueError("Location name is required")
        lid = self._repo.add(name, description, is_default)
        _log.info(f"Added location: id={lid}, name={name}")
        return lid

    def update(self, location_id: int, name: str, description: str = "",
               is_default: bool = False, is_active: bool = True) -> None:
        name = name.strip()
        if not name:
            raise ValueError("Location name is required")
        self._repo.update(location_id, name, description, is_default, is_active)
        _log.info(f"Updated location: id={location_id}, name={name}")

    def delete(self, location_id: int) -> bool:
        result = self._repo.delete(location_id)
        if result:
            _log.info(f"Deleted location: id={location_id}")
        else:
            _log.warning(f"Cannot delete location {location_id}: has stock or is default")
        return result

    # ── Stock queries ────────────────────────────────────────────────────────

    def get_stock_breakdown(self, item_id: int) -> list[LocationStock]:
        return self._repo.get_stock(item_id)

    def get_location_items(self, location_id: int) -> list[LocationStock]:
        return self._repo.get_location_items(location_id)

    # ── Transfers ────────────────────────────────────────────────────────────

    def transfer(self, item_id: int, from_id: int, to_id: int,
                 quantity: int, note: str = "") -> int:
        if quantity <= 0:
            raise ValueError("Transfer quantity must be positive")
        if from_id == to_id:
            raise ValueError("Source and destination must be different")
        # Check source has enough
        stock = self._repo.get_stock(item_id)
        from_stock = next((s for s in stock if s.location_id == from_id), None)
        available = from_stock.quantity if from_stock else 0
        if quantity > available:
            raise ValueError(
                f"Insufficient stock at source ({available} available, "
                f"{quantity} requested)"
            )
        tid = self._repo.transfer(item_id, from_id, to_id, quantity, note)
        _log.info(
            f"Transfer: item={item_id}, from={from_id}, to={to_id}, "
            f"qty={quantity}"
        )
        return tid

    def get_transfers(self, item_id: Optional[int] = None,
                      limit: int = 100) -> list[StockTransfer]:
        return self._repo.get_transfers(item_id=item_id, limit=limit)
