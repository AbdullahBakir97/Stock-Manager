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
                      accent_color: str = "#4A9EFF",
                      default_price: float | None = None) -> int:
        with self._conn() as conn:
            max_order = conn.execute(
                "SELECT COALESCE(MAX(sort_order),0) FROM part_types WHERE category_id=?",
                (category_id,),
            ).fetchone()[0]
            cur = conn.execute(
                """INSERT INTO part_types
                   (category_id, key, name, accent_color, sort_order, default_price)
                   VALUES (?,?,?,?,?,?)""",
                (category_id, key, name, accent_color, max_order + 1, default_price),
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
                """SELECT COUNT(*) FROM inventory_items ii
                   JOIN part_types pt ON pt.id = ii.part_type_id
                   WHERE pt.category_id=? AND ii.stock > 0""",
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
                         name: str, accent_color: str,
                         default_price: float | None = None) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE part_types SET key=?, name=?, accent_color=?, default_price=? "
                "WHERE id=?",
                (key, name, accent_color, default_price, part_type_id),
            )

    def update_part_type_price(self, part_type_id: int, default_price: float | None) -> None:
        """Update just the default_price on a part type."""
        with self._conn() as conn:
            conn.execute(
                "UPDATE part_types SET default_price=? WHERE id=?",
                (default_price, part_type_id),
            )

    def delete_part_type(self, part_type_id: int) -> bool:
        """Delete part type. Returns False if any stock > 0 exists."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM inventory_items WHERE part_type_id=? AND stock > 0",
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

    # ── Part Type Colors ────────────────────────────────────────────────────

    def get_pt_colors(self, part_type_id: int) -> list[dict]:
        """Get colors for a part type. Returns [{id, color_name, color_code, sort_order}]."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM part_type_colors WHERE part_type_id=? ORDER BY sort_order",
                (part_type_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def add_pt_color(self, part_type_id: int, color_name: str, color_code: str = "") -> int:
        """Add a color to a part type."""
        with self._conn() as conn:
            max_order = conn.execute(
                "SELECT COALESCE(MAX(sort_order),0) FROM part_type_colors WHERE part_type_id=?",
                (part_type_id,),
            ).fetchone()[0]
            cur = conn.execute(
                "INSERT OR IGNORE INTO part_type_colors (part_type_id, color_name, color_code, sort_order) VALUES (?,?,?,?)",
                (part_type_id, color_name, color_code, max_order + 1),
            )
            return cur.lastrowid or 0

    def remove_pt_color(self, color_id: int) -> None:
        """Remove a color from a part type."""
        with self._conn() as conn:
            conn.execute("DELETE FROM part_type_colors WHERE id=?", (color_id,))

    # ── Per-model product-color overrides ───────────────────────────────────

    def get_model_pt_colors(self, model_id: int, part_type_id: int) -> list[str]:
        """Return per-model product colors (e.g. ['Black','Silver']).
        Empty list means no override — caller should fall back to global."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT color_name FROM model_part_type_colors "
                "WHERE model_id=? AND part_type_id=?",
                (model_id, part_type_id),
            ).fetchall()
            return [r["color_name"] for r in rows]

    def set_model_pt_colors(self, model_id: int, part_type_id: int,
                            color_names: list[str]) -> None:
        """Replace all per-model colors for a model+part_type."""
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM model_part_type_colors "
                "WHERE model_id=? AND part_type_id=?",
                (model_id, part_type_id),
            )
            for name in color_names:
                conn.execute(
                    "INSERT OR IGNORE INTO model_part_type_colors "
                    "(model_id, part_type_id, color_name) VALUES (?, ?, ?)",
                    (model_id, part_type_id, name),
                )

    def clear_model_pt_colors(self, model_id: int, part_type_id: int) -> None:
        """Remove all per-model color overrides (falls back to global)."""
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM model_part_type_colors "
                "WHERE model_id=? AND part_type_id=?",
                (model_id, part_type_id),
            )

    def _pt(self, row) -> PartTypeConfig:
        return PartTypeConfig(
            id=row["id"], category_id=row["category_id"],
            key=row["key"], name=row["name"],
            accent_color=row["accent_color"], sort_order=row["sort_order"],
            default_price=(row["default_price"] if "default_price" in row.keys() else None),
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
