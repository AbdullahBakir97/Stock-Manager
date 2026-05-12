"""app/services/sale_service.py — Sales / POS business logic."""
from __future__ import annotations

from typing import Optional

from app.core.database import get_connection
from app.repositories.sale_repo import SaleRepository
from app.repositories.item_repo import ItemRepository
from app.repositories.transaction_repo import TransactionRepository
from app.services.supplier_service import SupplierService
from app.models.sale import Sale
from app.core.logger import get_logger

_log = get_logger(__name__)


class SaleService:

    def __init__(self) -> None:
        self._sales = SaleRepository()
        self._items = ItemRepository()
        self._txn = TransactionRepository()
        self._suppliers = SupplierService()

    def create_sale(self, customer_name: str = "", discount: float = 0,
                    note: str = "",
                    items: list[dict] | None = None,
                    customer_id: int | None = None) -> int:
        """Process a sale: create record, deduct stock, log transactions.

        Each item dict: {item_id, quantity, unit_price}.
        cost_price is auto-looked-up from supplier if available.
        """
        if not items:
            raise ValueError("Sale must have at least one item")

        # Validate stock availability and populate cost prices
        enriched: list[dict] = []
        for line in items:
            item = self._items.get_by_id(line["item_id"])
            if not item:
                raise ValueError(f"Item {line['item_id']} not found")
            qty = line["quantity"]
            if qty <= 0:
                raise ValueError("Item quantity must be positive")
            if qty > item.stock:
                raise ValueError(
                    f"Insufficient stock for {item.display_name}: "
                    f"{item.stock} available, {qty} requested"
                )
            cost = line.get("cost_price")
            if cost is None:
                cost = self._suppliers.get_preferred_cost(item.id) or 0
            enriched.append({
                "item_id": item.id,
                "quantity": qty,
                "unit_price": line["unit_price"],
                "cost_price": cost,
            })

        # Create sale record
        sale_id = self._sales.create(
            customer_name=customer_name, discount=discount,
            note=note, items=enriched, customer_id=customer_id,
        )

        # Deduct stock and log transactions
        with get_connection() as conn:
            for line in enriched:
                item = self._items.get_by_id(line["item_id"])
                before, after = self._items.apply_delta(
                    conn, line["item_id"], -line["quantity"]
                )
                self._txn.log_op(
                    conn, line["item_id"], "OUT", line["quantity"],
                    before, after, f"Sale #{sale_id}",
                )

        _log.info(
            f"Sale created: id={sale_id}, items={len(enriched)}, "
            f"customer={customer_name}"
        )
        return sale_id

    def get_by_customer(self, customer_id: int, limit: int = 50) -> list[Sale]:
        """Return sales linked to a specific customer."""
        return self._sales.get_by_customer(customer_id, limit=limit)

    def get_sale(self, sale_id: int) -> Optional[Sale]:
        return self._sales.get_by_id(sale_id)

    def get_sales(self, limit: int = 200, offset: int = 0,
                  date_from: str = "", date_to: str = "") -> list[Sale]:
        return self._sales.get_all(
            limit=limit, offset=offset,
            date_from=date_from, date_to=date_to,
        )

    def delete_sale(self, sale_id: int) -> bool:
        """Hard-delete a sale with NO stock restoration.

        Kept for internal/admin use. The user-facing "Delete" button on
        the Sales page should call ``void_sale`` instead — see below
        for the rationale.
        """
        return self._sales.delete(sale_id)

    def void_sale(self, sale_id: int) -> bool:
        """Cancel a sale by restoring stock for every line item and
        then deleting the sales row (sale_items cascade via FK).

        Why a separate method from ``delete_sale``: hard-deleting alone
        leaves stock permanently reduced — the items were "sold" in the
        inventory's view, but the sale record they came from no longer
        exists. ``void_sale`` returns every line's quantity back to the
        item's ``stock`` and logs a STOCK-IN transaction with note
        ``"Voided sale #N"`` so the inventory audit trail stays
        complete: original SALE-OUT and the reversal IN both visible
        in `inventory_transactions`.

        Raises ``ValueError`` if the sale doesn't exist.
        """
        sale = self._sales.get_by_id(sale_id)
        if sale is None:
            raise ValueError(f"Sale {sale_id} not found")

        with get_connection() as conn:
            for si in sale.items:
                before, after = self._items.apply_delta(
                    conn, si.item_id, si.quantity,
                )
                self._txn.log_op(
                    conn, si.item_id, "IN", si.quantity,
                    before, after, f"Voided sale #{sale_id}",
                )

        self._sales.delete(sale_id)
        _log.info(
            f"Sale voided: id={sale_id}, "
            f"items_restored={len(sale.items)}, "
            f"qty_restored={sum(si.quantity for si in sale.items)}"
        )
        return True

    def update_sale(self, sale_id: int, customer_name: str = "",
                    discount: float = 0, note: str = "",
                    items: list[dict] | None = None,
                    customer_id: int | None = None) -> int:
        """Edit an existing sale in place: stock-delta only the changed
        quantities, replace sale_items, update the sales row.

        ``items`` shape: ``[{"item_id", "quantity", "unit_price"}]``.
        Each item's quantity may differ from the original. The service
        computes ``delta = new_qty - old_qty`` per item and applies it
        as a single net stock movement:

          * delta > 0 — more was sold → ``apply_delta(-delta)`` (stock down) + OUT txn
          * delta < 0 — less was sold → ``apply_delta(+|delta|)`` (stock up) + IN txn
          * delta = 0 — no stock movement, no transaction logged

        Items that were on the OLD sale but not the NEW one get treated
        as ``new_qty = 0``, returning their full original qty to stock.
        New items in the NEW sale get full deduction.

        Validation: for each item on the new sale, the NEW qty must be
        <= (current stock + old qty). The ``+ old qty`` accounts for
        the fact that the old qty is currently OUT — once we restore it,
        the new qty has the full amount to draw from.

        Returns the same ``sale_id`` (in-place update). Raises
        ``ValueError`` on stock shortfall or missing sale.
        """
        if not items:
            raise ValueError("Sale must have at least one item")

        old_sale = self._sales.get_by_id(sale_id)
        if old_sale is None:
            raise ValueError(f"Sale {sale_id} not found")

        # Aggregate old and new qty per item_id. New items may appear,
        # old items may disappear, and shared items may have different
        # quantities — all three cases reduce to "qty delta per item".
        old_qty: dict[int, int] = {}
        for si in old_sale.items:
            old_qty[si.item_id] = old_qty.get(si.item_id, 0) + si.quantity
        new_qty: dict[int, int] = {}
        for ln in items:
            iid = ln["item_id"]
            q = int(ln["quantity"])
            if q <= 0:
                raise ValueError("Item quantity must be positive")
            new_qty[iid] = new_qty.get(iid, 0) + q

        # Stock validation BEFORE making any changes. Each new line's
        # qty must fit in (current stock + currently-allocated-to-this-sale).
        for iid, new_q in new_qty.items():
            item = self._items.get_by_id(iid)
            if item is None:
                raise ValueError(f"Item {iid} not found")
            available = item.stock + old_qty.get(iid, 0)
            if new_q > available:
                raise ValueError(
                    f"Insufficient stock for {item.display_name}: "
                    f"{available} available (current stock + old sale qty), "
                    f"{new_q} requested"
                )

        # Enrich with cost_price (use existing per-item lookup if the
        # caller didn't pass one).
        enriched: list[dict] = []
        for ln in items:
            cost = ln.get("cost_price")
            if cost is None:
                cost = self._suppliers.get_preferred_cost(ln["item_id"]) or 0
            enriched.append({
                "item_id": ln["item_id"],
                "quantity": int(ln["quantity"]),
                "unit_price": float(ln["unit_price"]),
                "cost_price": cost,
            })

        # Apply stock deltas + log transactions inside a single connection.
        with get_connection() as conn:
            all_ids = set(old_qty) | set(new_qty)
            for iid in all_ids:
                delta = new_qty.get(iid, 0) - old_qty.get(iid, 0)
                if delta == 0:
                    continue
                before, after = self._items.apply_delta(conn, iid, -delta)
                self._txn.log_op(
                    conn, iid,
                    "OUT" if delta > 0 else "IN",
                    abs(delta), before, after,
                    f"Updated sale #{sale_id}",
                )

            # Replace sale_items + update sales row in the same conn.
            total = sum(d["quantity"] * d["unit_price"] for d in enriched)
            conn.execute(
                """UPDATE sales
                      SET customer_name=?, total_amount=?,
                          discount=?, note=?, customer_id=?
                    WHERE id=?""",
                (customer_name.strip(), total, discount, note.strip(),
                 customer_id, sale_id),
            )
            conn.execute(
                "DELETE FROM sale_items WHERE sale_id=?", (sale_id,)
            )
            for d in enriched:
                line_total = d["quantity"] * d["unit_price"]
                conn.execute(
                    """INSERT INTO sale_items
                       (sale_id, item_id, quantity,
                        unit_price, cost_price, line_total)
                       VALUES (?,?,?,?,?,?)""",
                    (sale_id, d["item_id"], d["quantity"],
                     d["unit_price"], d["cost_price"], line_total),
                )

        _log.info(
            f"Sale updated: id={sale_id}, items={len(enriched)}, "
            f"customer={customer_name}"
        )
        return sale_id

    def daily_totals(self, date: str) -> dict:
        return self._sales.daily_totals(date)

    def top_items(self, limit: int = 10, date_from: str = "",
                  date_to: str = "") -> list[dict]:
        return self._sales.top_items(
            limit=limit, date_from=date_from, date_to=date_to,
        )
