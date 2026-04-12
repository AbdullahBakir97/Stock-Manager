"""app/repositories/customer_repo.py — Customer CRUD with purchase summaries."""
from __future__ import annotations
from app.repositories.base import BaseRepository
from app.models.customer import Customer


class CustomerRepository(BaseRepository):
    """Data access for customers table with sales summary joins."""

    # ── Read ─────────────────────────────────────────────────────────────────

    def get_all(self, active_only: bool = False) -> list[Customer]:
        with self._conn() as conn:
            where = "WHERE c.is_active = 1" if active_only else ""
            rows = conn.execute(f"""
                SELECT c.*,
                       COALESCE(s.cnt, 0)  AS total_purchases,
                       COALESCE(s.tot, 0)  AS total_spent,
                       COALESCE(s.last_dt, '') AS last_purchase
                FROM customers c
                LEFT JOIN (
                    SELECT customer_id,
                           COUNT(*)       AS cnt,
                           SUM(total_amount - discount) AS tot,
                           MAX(timestamp) AS last_dt
                    FROM sales
                    WHERE customer_id IS NOT NULL
                    GROUP BY customer_id
                ) s ON s.customer_id = c.id
                {where}
                ORDER BY c.name COLLATE NOCASE
            """).fetchall()
        return [self._row_to_customer(r) for r in rows]

    def get_by_id(self, customer_id: int) -> Customer | None:
        with self._conn() as conn:
            row = conn.execute("""
                SELECT c.*,
                       COALESCE(s.cnt, 0)  AS total_purchases,
                       COALESCE(s.tot, 0)  AS total_spent,
                       COALESCE(s.last_dt, '') AS last_purchase
                FROM customers c
                LEFT JOIN (
                    SELECT customer_id,
                           COUNT(*)       AS cnt,
                           SUM(total_amount - discount) AS tot,
                           MAX(timestamp) AS last_dt
                    FROM sales
                    WHERE customer_id IS NOT NULL
                    GROUP BY customer_id
                ) s ON s.customer_id = c.id
                WHERE c.id = ?
            """, (customer_id,)).fetchone()
        return self._row_to_customer(row) if row else None

    def search(self, term: str, limit: int = 50) -> list[Customer]:
        with self._conn() as conn:
            like = f"%{term}%"
            rows = conn.execute("""
                SELECT c.*,
                       COALESCE(s.cnt, 0)  AS total_purchases,
                       COALESCE(s.tot, 0)  AS total_spent,
                       COALESCE(s.last_dt, '') AS last_purchase
                FROM customers c
                LEFT JOIN (
                    SELECT customer_id,
                           COUNT(*)       AS cnt,
                           SUM(total_amount - discount) AS tot,
                           MAX(timestamp) AS last_dt
                    FROM sales
                    WHERE customer_id IS NOT NULL
                    GROUP BY customer_id
                ) s ON s.customer_id = c.id
                WHERE c.name LIKE ? OR c.phone LIKE ? OR c.email LIKE ?
                ORDER BY c.name COLLATE NOCASE
                LIMIT ?
            """, (like, like, like, limit)).fetchall()
        return [self._row_to_customer(r) for r in rows]

    # ── Write ────────────────────────────────────────────────────────────────

    def add(self, name: str, phone: str = "", email: str = "",
            address: str = "", notes: str = "") -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO customers (name, phone, email, address, notes)
                   VALUES (?, ?, ?, ?, ?)""",
                (name, phone, email, address, notes),
            )
            conn.commit()
            return cur.lastrowid

    def update(self, customer_id: int, name: str, phone: str = "",
               email: str = "", address: str = "", notes: str = "") -> None:
        with self._conn() as conn:
            conn.execute(
                """UPDATE customers
                   SET name = ?, phone = ?, email = ?, address = ?, notes = ?
                   WHERE id = ?""",
                (name, phone, email, address, notes, customer_id),
            )
            conn.commit()

    def set_active(self, customer_id: int, active: bool) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE customers SET is_active = ? WHERE id = ?",
                (1 if active else 0, customer_id),
            )
            conn.commit()

    def delete(self, customer_id: int) -> bool:
        """Delete customer. Returns False if they have sales."""
        with self._conn() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM sales WHERE customer_id = ?",
                (customer_id,),
            ).fetchone()[0]
            if count > 0:
                return False
            conn.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
            conn.commit()
            return True

    # ── Summary ──────────────────────────────────────────────────────────────

    def count(self) -> dict:
        """Return {total, active, with_purchases}."""
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
            active = conn.execute(
                "SELECT COUNT(*) FROM customers WHERE is_active = 1"
            ).fetchone()[0]
            with_purchases = conn.execute("""
                SELECT COUNT(DISTINCT customer_id)
                FROM sales WHERE customer_id IS NOT NULL
            """).fetchone()[0]
        return {"total": total, "active": active, "with_purchases": with_purchases}

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_customer(row) -> Customer:
        return Customer(
            id=row["id"],
            name=row["name"],
            phone=row["phone"] or "",
            email=row["email"] or "",
            address=row["address"] or "",
            notes=row["notes"] or "",
            is_active=bool(row["is_active"]),
            created_at=row["created_at"] or "",
            total_purchases=row["total_purchases"],
            total_spent=row["total_spent"],
            last_purchase=row["last_purchase"],
        )
