"""
app/repositories/product_repo.py — Standalone product CRUD.

Now reads/writes from inventory_items (model_id IS NULL) instead of the
legacy products table. The Product model is preserved for Phase C UI compat.
"""
from __future__ import annotations
from typing import Optional

from app.repositories.base import BaseRepository
from app.models.product import Product


class ProductRepository(BaseRepository):
    """
    Thin compat layer used by the products tab (main_window.py) until Phase C.
    All SQL now targets inventory_items WHERE model_id IS NULL.
    """

    def get_all(self, search: str = "",
                filter_low_stock: bool = False) -> list[Product]:
        sql = """
            SELECT *,
                   CASE WHEN stock <= min_stock THEN 1 ELSE 0 END AS is_low
            FROM inventory_items
            WHERE model_id IS NULL
        """
        params: list = []
        if search:
            sql += (" AND (brand LIKE ? OR name LIKE ? "
                    "OR color LIKE ? OR barcode LIKE ?)")
            s = f"%{search}%"
            params.extend([s, s, s, s])
        if filter_low_stock:
            sql += " AND stock <= min_stock"
        sql += " ORDER BY brand, name, color"
        with self._conn() as conn:
            return [self._build(r) for r in conn.execute(sql, params).fetchall()]

    def get_by_id(self, product_id: int) -> Optional[Product]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM inventory_items WHERE id=? AND model_id IS NULL",
                (product_id,),
            ).fetchone()
            return self._build(row) if row else None

    def get_by_barcode(self, barcode: str) -> Optional[Product]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM inventory_items WHERE barcode=? AND model_id IS NULL",
                (barcode.strip(),),
            ).fetchone()
            return self._build(row) if row else None

    def get_low_stock(self) -> list[Product]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT * FROM inventory_items
                WHERE model_id IS NULL
                  AND min_stock > 0
                  AND stock <= min_stock
                ORDER BY (CAST(stock AS REAL) / NULLIF(min_stock, 0)) ASC
            """).fetchall()
            return [self._build(r) for r in rows]

    def get_summary(self) -> dict:
        with self._conn() as conn:
            row = conn.execute("""
                SELECT
                    COUNT(*) AS total_products,
                    SUM(stock) AS total_units,
                    SUM(CASE WHEN stock <= min_stock THEN 1 ELSE 0 END) AS low_stock_count,
                    SUM(CASE WHEN stock = 0 THEN 1 ELSE 0 END) AS out_of_stock_count
                FROM inventory_items
                WHERE model_id IS NULL
            """).fetchone()
            return dict(row) if row else {}

    def get_distinct_brands(self) -> list[str]:
        with self._conn() as conn:
            return [r["brand"] for r in conn.execute(
                "SELECT DISTINCT brand FROM inventory_items"
                " WHERE model_id IS NULL AND brand != '' ORDER BY brand"
            ).fetchall()]

    def get_distinct_types(self) -> list[str]:
        with self._conn() as conn:
            return [r["name"] for r in conn.execute(
                "SELECT DISTINCT name FROM inventory_items"
                " WHERE model_id IS NULL AND name != '' ORDER BY name"
            ).fetchall()]

    def add(self, brand: str, type_: str, color: str, stock: int,
            barcode: Optional[str], low_stock_threshold: int,
            sell_price: Optional[float] = None) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO inventory_items
                   (brand, name, color, stock, barcode, min_stock, sell_price)
                   VALUES (?,?,?,?,?,?,?)""",
                (brand.strip(), type_.strip(), color.strip(), stock,
                 barcode.strip() if barcode else None,
                 low_stock_threshold, sell_price or None),
            )
            pid = cur.lastrowid
            conn.execute(
                """INSERT INTO inventory_transactions
                   (item_id, operation, quantity, stock_before, stock_after, note)
                   VALUES (?, 'CREATE', ?, 0, ?, 'Product created')""",
                (pid, stock, stock),
            )
            return pid

    def update(self, product_id: int, brand: str, type_: str, color: str,
               barcode: Optional[str], low_stock_threshold: int,
               sell_price: Optional[float] = None) -> None:
        with self._conn() as conn:
            conn.execute(
                """UPDATE inventory_items
                   SET brand=?, name=?, color=?, barcode=?,
                       min_stock=?, sell_price=?, updated_at=datetime('now')
                   WHERE id=? AND model_id IS NULL""",
                (brand.strip(), type_.strip(), color.strip(),
                 barcode.strip() if barcode else None,
                 low_stock_threshold, sell_price or None, product_id),
            )

    def delete(self, product_id: int) -> None:
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM inventory_items WHERE id=? AND model_id IS NULL",
                (product_id,),
            )

    def apply_delta(self, conn, product_id: int, delta: int) -> tuple[int, int]:
        row = conn.execute(
            "SELECT stock FROM inventory_items WHERE id=?", (product_id,)
        ).fetchone()
        before = row["stock"]
        after  = before + delta
        conn.execute(
            "UPDATE inventory_items SET stock=?, updated_at=datetime('now') WHERE id=?",
            (after, product_id),
        )
        return before, after

    def set_exact(self, conn, product_id: int, new_stock: int) -> tuple[int, int]:
        row = conn.execute(
            "SELECT stock FROM inventory_items WHERE id=?", (product_id,)
        ).fetchone()
        before = row["stock"]
        conn.execute(
            "UPDATE inventory_items SET stock=?, updated_at=datetime('now') WHERE id=?",
            (new_stock, product_id),
        )
        return before, new_stock

    def _build(self, row) -> Product:
        return Product(
            id=row["id"],
            brand=row["brand"] or "",
            type=row["name"] or "",           # inventory_items.name = products.type
            color=row["color"] or "",
            stock=row["stock"],
            barcode=row["barcode"],
            low_stock_threshold=row["min_stock"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            sell_price=row["sell_price"],
        )
