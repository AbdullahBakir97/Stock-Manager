"""app/repositories/model_repo.py — Phone model queries."""
from __future__ import annotations
from typing import Optional
from app.repositories.base import BaseRepository
from app.models.phone_model import PhoneModel


class ModelRepository(BaseRepository):

    def get_all(self, brand: Optional[str] = None) -> list[PhoneModel]:
        with self._conn() as conn:
            if brand:
                rows = conn.execute(
                    "SELECT * FROM phone_models WHERE brand=? ORDER BY sort_order",
                    (brand,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM phone_models ORDER BY brand, sort_order"
                ).fetchall()
            return [self._build(r) for r in rows]

    def get_brands(self) -> list[str]:
        with self._conn() as conn:
            return [
                r["brand"]
                for r in conn.execute(
                    "SELECT DISTINCT brand FROM phone_models ORDER BY brand"
                ).fetchall()
            ]

    def get_by_id(self, model_id: int) -> Optional[PhoneModel]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM phone_models WHERE id=?", (model_id,)
            ).fetchone()
            return self._build(row) if row else None

    def add(self, brand: str, name: str) -> int:
        brand = brand.strip(); name = name.strip()
        with self._conn() as conn:
            max_order = conn.execute(
                "SELECT COALESCE(MAX(sort_order),0) FROM phone_models WHERE brand=?",
                (brand,),
            ).fetchone()[0]
            cur = conn.execute(
                "INSERT INTO phone_models (brand, name, sort_order) VALUES (?,?,?)",
                (brand, name, max_order + 1),
            )
            mid = cur.lastrowid
            # Auto-create stock_entries for every part_type so the matrix is always complete
            for pt in conn.execute("SELECT id FROM part_types").fetchall():
                conn.execute(
                    "INSERT OR IGNORE INTO stock_entries (model_id, part_type_id) VALUES (?,?)",
                    (mid, pt["id"]),
                )
            return mid

    def exists(self, name: str) -> bool:
        with self._conn() as conn:
            return bool(
                conn.execute(
                    "SELECT 1 FROM phone_models WHERE name=?", (name,)
                ).fetchone()
            )

    def delete(self, model_id: int) -> bool:
        """Delete model. Returns False if any stock_entries have stock > 0."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM stock_entries WHERE model_id=? AND stock > 0",
                (model_id,),
            ).fetchone()
            if row and row[0] > 0:
                return False
            conn.execute("DELETE FROM phone_models WHERE id=?", (model_id,))
            return True

    def rename(self, model_id: int, new_name: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE phone_models SET name=? WHERE id=?",
                (new_name.strip(), model_id),
            )

    def reorder(self, brand: str, ordered_ids: list[int]) -> None:
        """Update sort_order for models of a brand based on provided id order."""
        with self._conn() as conn:
            for i, mid in enumerate(ordered_ids, start=1):
                conn.execute(
                    "UPDATE phone_models SET sort_order=? WHERE id=? AND brand=?",
                    (i, mid, brand),
                )

    def _build(self, row) -> PhoneModel:
        return PhoneModel(
            id=row["id"], brand=row["brand"],
            name=row["name"], sort_order=row["sort_order"],
        )
