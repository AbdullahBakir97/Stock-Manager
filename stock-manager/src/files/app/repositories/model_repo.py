"""app/repositories/model_repo.py — Phone model queries."""
from __future__ import annotations
import re
from typing import Optional
from app.repositories.base import BaseRepository
from app.models.phone_model import PhoneModel


def _natural_sort_key(name: str):
    """Sort key: A5 < A12 < A22, Note10 < Note20."""
    parts = re.split(r'(\d+)', name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


# Apple models that come before numbered models — given low numeric prefix
_APPLE_PREFIX = {"X": "00", "XS": "01", "XS max": "02", "XR": "03"}

# Brand sort priority
_BRAND_ORDER = {"Apple": 0, "Samsung": 1, "Xiaomi": 2}


def _brand_sort_key(brand: str, name: str):
    """Sort key: brand priority, then natural sort.
    Apple X/XS/XR get numeric prefix 00-03 so they sort before '11'."""
    brand_idx = _BRAND_ORDER.get(brand, 99)
    sort_name = _APPLE_PREFIX.get(name, name) if brand == "Apple" else name
    return (brand_idx, _natural_sort_key(sort_name))


class ModelRepository(BaseRepository):

    def get_all(self, brand: Optional[str] = None) -> list[PhoneModel]:
        with self._conn() as conn:
            if brand:
                rows = conn.execute(
                    "SELECT * FROM phone_models WHERE brand=?",
                    (brand,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM phone_models"
                ).fetchall()
            models = [self._build(r) for r in rows]
            # Sort by sort_order (set by admin reorder or initial natural sort)
            models.sort(key=lambda m: m.sort_order)
            return models

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
            # Insert with temporary high sort_order
            max_order = conn.execute(
                "SELECT COALESCE(MAX(sort_order),0) FROM phone_models"
            ).fetchone()[0]
            cur = conn.execute(
                "INSERT INTO phone_models (brand, name, sort_order) VALUES (?,?,?)",
                (brand, name, max_order + 1),
            )
            mid = cur.lastrowid
            # Re-sort all models of this brand naturally
            self._resort_brand(conn, brand)
            return mid

    def _resort_brand(self, conn, brand: str) -> None:
        """Re-sort all models of a brand using natural sort order."""
        rows = conn.execute(
            "SELECT id, name FROM phone_models WHERE brand=?", (brand,)
        ).fetchall()

        if brand == "Apple":
            # X/XS/XR come first, then numbered models
            special = {"X": 0, "XS": 1, "XS max": 2, "XR": 3}
            first = sorted(
                [r for r in rows if r["name"] in special],
                key=lambda r: special[r["name"]]
            )
            rest = sorted(
                [r for r in rows if r["name"] not in special],
                key=lambda r: _natural_sort_key(r["name"])
            )
            sorted_rows = first + rest
        else:
            sorted_rows = sorted(rows, key=lambda r: _natural_sort_key(r["name"]))

        bases = {"Apple": 1, "Samsung": 100, "Xiaomi": 300}
        base = bases.get(brand, 400)
        for i, r in enumerate(sorted_rows):
            conn.execute(
                "UPDATE phone_models SET sort_order=? WHERE id=?",
                (base + i, r["id"]),
            )

    def exists(self, name: str) -> bool:
        with self._conn() as conn:
            return bool(
                conn.execute(
                    "SELECT 1 FROM phone_models WHERE name=?", (name,)
                ).fetchone()
            )

    def delete(self, model_id: int) -> bool:
        """Delete model. Returns False if any inventory_items have stock > 0."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM inventory_items WHERE model_id=? AND stock > 0",
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
        """Update sort_order for models of a brand based on provided id order.
        Preserves brand-specific base offset so brands don't interleave."""
        bases = {"Apple": 1, "Samsung": 100, "Xiaomi": 300}
        base = bases.get(brand, 400)
        with self._conn() as conn:
            for i, mid in enumerate(ordered_ids):
                conn.execute(
                    "UPDATE phone_models SET sort_order=? WHERE id=? AND brand=?",
                    (base + i, mid, brand),
                )

    def _build(self, row) -> PhoneModel:
        return PhoneModel(
            id=row["id"], brand=row["brand"],
            name=row["name"], sort_order=row["sort_order"],
        )
