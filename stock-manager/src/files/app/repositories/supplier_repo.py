"""app/repositories/supplier_repo.py — Supplier CRUD and supplier-item mapping."""
from __future__ import annotations

from typing import Optional

from app.repositories.base import BaseRepository
from app.models.supplier import Supplier, SupplierItem


class SupplierRepository(BaseRepository):

    # ── Supplier CRUD ────────────────────────────────────────────────────────

    def get_all(self, search: str = "", active_only: bool = True) -> list[Supplier]:
        with self._conn() as conn:
            sql = """
                SELECT s.*,
                       COUNT(DISTINCT si.id) AS item_count
                FROM suppliers s
                LEFT JOIN supplier_items si ON si.supplier_id = s.id
            """
            filters = []
            params = []

            if active_only:
                filters.append("s.is_active = 1")

            if search.strip():
                search_term = f"%{search.strip()}%"
                filters.append(
                    "(s.name LIKE ? OR s.contact_name LIKE ? OR "
                    "s.email LIKE ? OR s.phone LIKE ?)"
                )
                params.extend([search_term, search_term, search_term, search_term])

            if filters:
                sql += " WHERE " + " AND ".join(filters)

            sql += " GROUP BY s.id ORDER BY s.name"

            return [self._build(r) for r in conn.execute(sql, params).fetchall()]

    def get_by_id(self, supplier_id: int) -> Optional[Supplier]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM suppliers WHERE id=?", (supplier_id,)
            ).fetchone()
            return self._build(row) if row else None

    def add(self, name: str, contact_name: str = "", phone: str = "",
            email: str = "", address: str = "", notes: str = "") -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO suppliers (name, contact_name, phone, email, address, notes)
                   VALUES (?,?,?,?,?,?)""",
                (name.strip(), contact_name.strip(), phone.strip(),
                 email.strip(), address.strip(), notes.strip()),
            )
            return cur.lastrowid

    def update(self, supplier_id: int, name: str, contact_name: str = "",
               phone: str = "", email: str = "", address: str = "",
               notes: str = "", is_active: bool = True, rating: int = 0) -> None:
        with self._conn() as conn:
            # Check if rating column exists and add it if missing
            cols = {r[1] for r in conn.execute("PRAGMA table_info(suppliers)").fetchall()}
            if 'rating' not in cols:
                conn.execute("ALTER TABLE suppliers ADD COLUMN rating INTEGER DEFAULT 0")
            
            conn.execute(
                """UPDATE suppliers
                   SET name=?, contact_name=?, phone=?, email=?,
                       address=?, notes=?, is_active=?, rating=?
                   WHERE id=?""",
                (name.strip(), contact_name.strip(), phone.strip(),
                 email.strip(), address.strip(), notes.strip(),
                 int(is_active), int(rating), supplier_id),
            )

    def delete(self, supplier_id: int) -> bool:
        """Delete supplier. Returns False if linked to items with stock > 0."""
        with self._conn() as conn:
            row = conn.execute(
                """SELECT COUNT(*) FROM supplier_items si
                   JOIN inventory_items ii ON ii.id = si.item_id
                   WHERE si.supplier_id=? AND ii.stock > 0""",
                (supplier_id,),
            ).fetchone()
            if row and row[0] > 0:
                return False
            conn.execute("DELETE FROM suppliers WHERE id=?", (supplier_id,))
            return True

    def set_active(self, supplier_id: int, active: bool) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE suppliers SET is_active=? WHERE id=?",
                (int(active), supplier_id),
            )

    def get_summary(self) -> dict:
        """Get summary statistics for suppliers."""
        conn = self._conn()
        # Check if rating column exists and add it if missing
        cols = {r[1] for r in conn.execute("PRAGMA table_info(suppliers)").fetchall()}
        has_rating = 'rating' in cols
        if not has_rating:
            conn.execute("ALTER TABLE suppliers ADD COLUMN rating INTEGER DEFAULT 0")
            conn.commit()

        row = conn.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active,
                SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) AS inactive,
                COALESCE(AVG(CASE WHEN rating > 0 THEN rating ELSE NULL END), 0) AS avg_rating
            FROM suppliers
        """).fetchone()
        conn.close()
        return dict(row) if row else {
            "total": 0, "active": 0, "inactive": 0, "avg_rating": 0
        }

    # ── Supplier-Item mapping ────────────────────────────────────────────────

    def get_items(self, supplier_id: int) -> list[SupplierItem]:
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT si.*, s.name AS supplier_name,
                          COALESCE(ii.name, pm.name, '') AS item_name
                   FROM supplier_items si
                   JOIN suppliers s ON s.id = si.supplier_id
                   JOIN inventory_items ii ON ii.id = si.item_id
                   LEFT JOIN phone_models pm ON pm.id = ii.model_id
                   WHERE si.supplier_id=?
                   ORDER BY item_name""",
                (supplier_id,),
            ).fetchall()
            return [self._build_si(r) for r in rows]

    def get_suppliers_for_item(self, item_id: int) -> list[SupplierItem]:
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT si.*, s.name AS supplier_name,
                          COALESCE(ii.name, pm.name, '') AS item_name
                   FROM supplier_items si
                   JOIN suppliers s ON s.id = si.supplier_id
                   JOIN inventory_items ii ON ii.id = si.item_id
                   LEFT JOIN phone_models pm ON pm.id = ii.model_id
                   WHERE si.item_id=?
                   ORDER BY si.is_preferred DESC, s.name""",
                (item_id,),
            ).fetchall()
            return [self._build_si(r) for r in rows]

    def link_item(self, supplier_id: int, item_id: int,
                  cost_price: float = 0, lead_days: int = 0,
                  supplier_sku: str = "", is_preferred: bool = False) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT OR REPLACE INTO supplier_items
                   (supplier_id, item_id, cost_price, lead_days, supplier_sku, is_preferred)
                   VALUES (?,?,?,?,?,?)""",
                (supplier_id, item_id, cost_price, lead_days,
                 supplier_sku.strip(), int(is_preferred)),
            )
            return cur.lastrowid

    def unlink_item(self, supplier_id: int, item_id: int) -> None:
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM supplier_items WHERE supplier_id=? AND item_id=?",
                (supplier_id, item_id),
            )

    # ── Builders ─────────────────────────────────────────────────────────────

    def _build(self, row) -> Supplier:
        keys = row.keys()
        return Supplier(
            id=row["id"], name=row["name"],
            contact_name=row["contact_name"], phone=row["phone"],
            email=row["email"], address=row["address"],
            notes=row["notes"], is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            rating=row["rating"] if "rating" in keys else 0,
            updated_at=row["updated_at"] if "updated_at" in keys else "",
            item_count=row["item_count"] if "item_count" in keys else 0,
            total_orders=row["total_orders"] if "total_orders" in keys else 0,
        )

    def _build_si(self, row) -> SupplierItem:
        return SupplierItem(
            id=row["id"],
            supplier_id=row["supplier_id"],
            item_id=row["item_id"],
            cost_price=row["cost_price"] or 0.0,
            lead_days=row["lead_days"] if "lead_days" in row.keys() else 0,
            supplier_sku=row["supplier_sku"] if "supplier_sku" in row.keys() else "",
            is_preferred=bool(row["is_preferred"]) if "is_preferred" in row.keys() else False,
            supplier_name=row["supplier_name"] if "supplier_name" in row.keys() else "",
            item_name=row["item_name"] if "item_name" in row.keys() else "",
        )