"""app/repositories/category_repo.py — Category and PartType queries."""
from __future__ import annotations
from typing import Optional
from app.repositories.base import BaseRepository
from app.models.category import CategoryConfig, PartTypeConfig


class CategoryRepository(BaseRepository):

    def get_all_active(self) -> list[CategoryConfig]:
        with self._conn() as conn:
            cats = conn.execute(
                "SELECT * FROM categories WHERE is_active=1 ORDER BY sort_order"
            ).fetchall()
            return [self._build(conn, r) for r in cats]

    def get_all(self) -> list[CategoryConfig]:
        with self._conn() as conn:
            cats = conn.execute("SELECT * FROM categories ORDER BY sort_order").fetchall()
            return [self._build(conn, r) for r in cats]

    def get_by_id(self, category_id: int) -> Optional[CategoryConfig]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM categories WHERE id=?", (category_id,)
            ).fetchone()
            return self._build(conn, row) if row else None

    def get_by_key(self, key: str) -> Optional[CategoryConfig]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM categories WHERE key=?", (key,)
            ).fetchone()
            return self._build(conn, row) if row else None

    def get_part_types(self, category_id: int) -> list[PartTypeConfig]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM part_types WHERE category_id=? ORDER BY sort_order",
                (category_id,),
            ).fetchall()
            return [self._pt(r) for r in rows]

    def add_category(self, key: str, name_en: str, name_de: str = "",
                     name_ar: str = "", icon: str = "") -> int:
        with self._conn() as conn:
            max_order = conn.execute(
                "SELECT COALESCE(MAX(sort_order),0) FROM categories"
            ).fetchone()[0]
            cur = conn.execute(
                """INSERT INTO categories (key, name_en, name_de, name_ar, sort_order, icon)
                   VALUES (?,?,?,?,?,?)""",
                (key, name_en, name_de, name_ar, max_order + 1, icon),
            )
            return cur.lastrowid

    def add_part_type(self, category_id: int, key: str, name: str,
                      accent_color: str = "#4A9EFF") -> int:
        with self._conn() as conn:
            max_order = conn.execute(
                "SELECT COALESCE(MAX(sort_order),0) FROM part_types WHERE category_id=?",
                (category_id,),
            ).fetchone()[0]
            cur = conn.execute(
                """INSERT INTO part_types (category_id, key, name, accent_color, sort_order)
                   VALUES (?,?,?,?,?)""",
                (category_id, key, name, accent_color, max_order + 1),
            )
            return cur.lastrowid

    def update_category(self, category_id: int, name_en: str, name_de: str,
                        name_ar: str, icon: str, is_active: bool) -> None:
        with self._conn() as conn:
            conn.execute(
                """UPDATE categories SET name_en=?, name_de=?, name_ar=?,
                   icon=?, is_active=? WHERE id=?""",
                (name_en, name_de, name_ar, icon, int(is_active), category_id),
            )

    def set_active(self, category_id: int, active: bool) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE categories SET is_active=? WHERE id=?",
                (int(active), category_id),
            )

    def delete_category(self, category_id: int) -> bool:
        """Delete category and its part types. Returns False if any stock > 0 exists."""
        with self._conn() as conn:
            row = conn.execute(
                """SELECT COUNT(*) FROM stock_entries se
                   JOIN part_types pt ON pt.id = se.part_type_id
                   WHERE pt.category_id=? AND se.stock > 0""",
                (category_id,),
            ).fetchone()
            if row and row[0] > 0:
                return False
            conn.execute("DELETE FROM categories WHERE id=?", (category_id,))
            return True

    def reorder(self, ordered_ids: list[int]) -> None:
        """Update sort_order for categories based on provided id order."""
        with self._conn() as conn:
            for i, cat_id in enumerate(ordered_ids, start=1):
                conn.execute(
                    "UPDATE categories SET sort_order=? WHERE id=?", (i, cat_id)
                )

    def update_part_type(self, part_type_id: int, key: str,
                         name: str, accent_color: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE part_types SET key=?, name=?, accent_color=? WHERE id=?",
                (key, name, accent_color, part_type_id),
            )

    def delete_part_type(self, part_type_id: int) -> bool:
        """Delete part type. Returns False if any stock > 0 exists."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM stock_entries WHERE part_type_id=? AND stock > 0",
                (part_type_id,),
            ).fetchone()
            if row and row[0] > 0:
                return False
            conn.execute("DELETE FROM part_types WHERE id=?", (part_type_id,))
            return True

    def reorder_part_types(self, ordered_ids: list[int]) -> None:
        """Update sort_order for part types based on provided id order."""
        with self._conn() as conn:
            for i, pt_id in enumerate(ordered_ids, start=1):
                conn.execute(
                    "UPDATE part_types SET sort_order=? WHERE id=?", (i, pt_id)
                )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _pt(self, row) -> PartTypeConfig:
        return PartTypeConfig(
            id=row["id"], category_id=row["category_id"],
            key=row["key"], name=row["name"],
            accent_color=row["accent_color"], sort_order=row["sort_order"],
        )

    def _build(self, conn, row) -> CategoryConfig:
        pts = conn.execute(
            "SELECT * FROM part_types WHERE category_id=? ORDER BY sort_order",
            (row["id"],),
        ).fetchall()
        return CategoryConfig(
            id=row["id"], key=row["key"],
            name_en=row["name_en"], name_de=row["name_de"], name_ar=row["name_ar"],
            sort_order=row["sort_order"], icon=row["icon"],
            is_active=bool(row["is_active"]),
            part_types=[self._pt(p) for p in pts],
        )
