"""app/services/customer_service.py — Customer business logic."""
from __future__ import annotations
from app.repositories.customer_repo import CustomerRepository
from app.models.customer import Customer


class CustomerService:
    """Business logic for customer management."""

    def __init__(self) -> None:
        self._repo = CustomerRepository()

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def get_all(self, active_only: bool = False) -> list[Customer]:
        return self._repo.get_all(active_only=active_only)

    def get_by_id(self, customer_id: int) -> Customer | None:
        return self._repo.get_by_id(customer_id)

    def search(self, term: str) -> list[Customer]:
        return self._repo.search(term)

    def add_customer(self, name: str, phone: str = "", email: str = "",
                     address: str = "", notes: str = "") -> int:
        if not name.strip():
            raise ValueError("Customer name is required")
        return self._repo.add(name.strip(), phone.strip(), email.strip(),
                              address.strip(), notes.strip())

    def update_customer(self, customer_id: int, name: str, phone: str = "",
                        email: str = "", address: str = "",
                        notes: str = "") -> None:
        if not name.strip():
            raise ValueError("Customer name is required")
        self._repo.update(customer_id, name.strip(), phone.strip(),
                          email.strip(), address.strip(), notes.strip())

    def toggle_active(self, customer_id: int) -> None:
        cust = self._repo.get_by_id(customer_id)
        if cust:
            self._repo.set_active(customer_id, not cust.is_active)

    def delete_customer(self, customer_id: int) -> bool:
        return self._repo.delete(customer_id)

    # ── Summary ──────────────────────────────────────────────────────────────

    def get_summary(self) -> dict:
        return self._repo.count()
