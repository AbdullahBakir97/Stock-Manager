"""app/repositories/item_repo.py — Unified CRUD for inventory_items."""
from __future__ import annotations
from typing import Optional
import sqlite3

from app.repositories.base import BaseRepository
from app.models.item import InventoryItem


class ItemRepository(BaseRepository):
    """
    Single repository for all inventory — both standalone products
    (model_id IS NULL) and matrix items (model_id + part_type_id set).
    """

    # ── SELECT helpers ────────────────────────────────────────────────────────

    _SELECT = """
        SELECT ii.*,
               pm.name  AS model_name,  pm.brand AS model_brand,
               pt.key   AS pt_key,      pt.name  AS pt_name,
               pt.accent_color AS pt_color
        FROM inventory_items ii
        LEFT JOIN phone_models pm ON pm.id = ii.model_id
        LEFT JOIN part_types   pt ON pt.id = ii.part_type_id
    """

    # ── Product queries (model_id IS NULL) ────────────────────────────────────

    def get_all_items(self, search: str = "",
                      filter_low_stock: bool = False) -> list[InventoryItem]:
        """Return ALL active inventory items (standalone + matrix)."""
        sql = self._SELECT + " WHERE ii.is_active = 1"
        params: list = []
        if search:
            sql += (
                " AND (ii.brand LIKE ? OR ii.name LIKE ? OR ii.color LIKE ?"
                " OR ii.barcode LIKE ? OR pm.name LIKE ? OR pm.brand LIKE ? OR pt.name LIKE ?)"
            )
            s = f"%{search}%"
            params.extend([s, s, s, s, s, s, s])
        if filter_low_stock:
            sql += " AND ii.min_stock > 0 AND ii.stock <= ii.min_stock"
        # Standalone products first, then matrix items grouped by model/part
        sql += (" ORDER BY (ii.model_id IS NULL) DESC,"
                " pm.brand, pm.name, pt.sort_order, ii.brand, ii.name")
        with self._conn() as conn:
            return [self._build(r) for r in conn.execute(sql, params).fetchall()]

    def get_all_products(self, search: str = "",
                         filter_low_stock: bool = False) -> list[InventoryItem]:
        sql = self._SELECT + " WHERE ii.model_id IS NULL"
        params: list = []
        if search:
            sql += (" AND (ii.brand LIKE ? OR ii.name LIKE ? "
                    "OR ii.color LIKE ? OR ii.barcode LIKE ?)")
            s = f"%{search}%"
            params.extend([s, s, s, s])
        if filter_low_stock:
            sql += " AND ii.stock <= ii.min_stock"
        sql += " ORDER BY ii.brand, ii.name, ii.color"
        with self._conn() as conn:
            return [self._build(r) for r in conn.execute(sql, params).fetchall()]

    def get_by_id(self, item_id: int) -> Optional[InventoryItem]:
        with self._conn() as conn:
            row = conn.execute(
                self._SELECT + " WHERE ii.id=?", (item_id,)
            ).fetchone()
            return self._build(row) if row else None

    def get_by_barcode(self, barcode: str) -> Optional[InventoryItem]:
        with self._conn() as conn:
            row = conn.execute(
                self._SELECT + " WHERE ii.barcode=?", (barcode.strip(),)
            ).fetchone()
            return self._build(row) if row else None

    def get_low_stock(self) -> list[InventoryItem]:
        """All items (products + matrix) at or below min_stock."""
        sql = (self._SELECT +
               " WHERE ii.min_stock > 0 AND ii.stock <= ii.min_stock"
               " ORDER BY (CAST(ii.stock AS REAL) / ii.min_stock) ASC")
        with self._conn() as conn:
            return [self._build(r) for r in conn.execute(sql).fetchall()]

    def get_summary(self) -> dict:
        """Aggregate counts for the summary cards."""
        with self._conn() as conn:
            row = conn.execute("""
                SELECT
                    COUNT(CASE WHEN model_id IS NULL THEN 1 END)  AS total_products,
                    SUM(stock)                                      AS total_units,
                    SUM(CASE WHEN min_stock > 0 AND stock <= min_stock THEN 1 ELSE 0 END)
                                                                    AS low_stock_count,
                    SUM(CASE WHEN stock = 0 THEN 1 ELSE 0 END)    AS out_of_stock_count,
                    SUM(CASE WHEN sell_price IS NOT NULL
                             THEN stock * sell_price ELSE 0 END)   AS inventory_value
                FROM inventory_items
            """).fetchone()
            return dict(row) if row else {}

    def get_distinct_brands(self) -> list[str]:
        with self._conn() as conn:
            return [r["brand"] for r in conn.execute(
                "SELECT DISTINCT brand FROM inventory_items"
                " WHERE model_id IS NULL AND brand != '' ORDER BY brand"
            ).fetchall()]

    def get_distinct_names(self) -> list[str]:
        with self._conn() as conn:
            return [r["name"] for r in conn.execute(
                "SELECT DISTINCT name FROM inventory_items"
                " WHERE model_id IS NULL AND name != '' ORDER BY name"
            ).fetchall()]

    # ── Matrix queries (model_id IS NOT NULL) ─────────────────────────────────

    def get_matrix_items(
        self, category_id: int, brand: Optional[str] = None
    ) -> dict[tuple[int, str], InventoryItem]:
        """Returns {(model_id, part_type_key): InventoryItem} for a category."""
        sql = (self._SELECT +
               " WHERE pt.category_id=? AND ii.model_id IS NOT NULL")
        params: list = [category_id]
        if brand:
            sql += " AND pm.brand=?"
            params.append(brand)
        sql += " ORDER BY pm.sort_order, pt.sort_order"
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            return {(r["model_id"], r["pt_key"]): self._build(r) for r in rows}

    def get_summary_for_category(self, category_id: int) -> dict:
        with self._conn() as conn:
            row = conn.execute("""
                SELECT
                    COUNT(*)  AS total_entries,
                    SUM(ii.stock) AS total_units,
                    SUM(CASE WHEN ii.stock = 0 THEN 1 ELSE 0 END) AS out_count,
                    SUM(CASE WHEN ii.stock < ii.min_stock AND ii.stock > 0 THEN 1 ELSE 0 END)
                        AS low_count
                FROM inventory_items ii
                JOIN part_types pt ON pt.id = ii.part_type_id
                WHERE pt.category_id = ? AND ii.model_id IS NOT NULL
            """, (category_id,)).fetchone()
            return dict(row) if row else {}

    # ── Write — products ──────────────────────────────────────────────────────

    def add_product(self, brand: str, name: str, color: str, stock: int,
                    barcode: Optional[str], min_stock: int,
                    sell_price: Optional[float] = None) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO inventory_items
                   (brand, name, color, stock, barcode, min_stock, sell_price)
                   VALUES (?,?,?,?,?,?,?)""",
                (brand.strip(), name.strip(), color.strip(), stock,
                 barcode.strip() if barcode else None, min_stock, sell_price),
            )
            pid = cur.lastrowid
            conn.execute(
                """INSERT INTO inventory_transactions
                   (item_id, operation, quantity, stock_before, stock_after, note)
                   VALUES (?, 'CREATE', ?, 0, ?, 'Product created')""",
                (pid, stock, stock),
            )
            return pid

    def update_product(self, item_id: int, brand: str, name: str, color: str,
                       barcode: Optional[str], min_stock: int,
                       sell_price: Optional[float] = None) -> None:
        with self._conn() as conn:
            conn.execute(
                """UPDATE inventory_items
                   SET brand=?, name=?, color=?, barcode=?, min_stock=?,
                       sell_price=?, updated_at=datetime('now')
                   WHERE id=?""",
                (brand.strip(), name.strip(), color.strip(),
                 barcode.strip() if barcode else None,
                 min_stock, sell_price, item_id),
            )

    def delete(self, item_id: int) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM inventory_items WHERE id=?", (item_id,))

    # ── Write — stock operations ──────────────────────────────────────────────

    def apply_delta(self, conn: sqlite3.Connection,
                    item_id: int, delta: int) -> tuple[int, int]:
        row = conn.execute(
            "SELECT stock FROM inventory_items WHERE id=?", (item_id,)
        ).fetchone()
        before = row["stock"]
        after  = before + delta
        conn.execute(
            "UPDATE inventory_items SET stock=?, updated_at=datetime('now') WHERE id=?",
            (after, item_id),
        )
        return before, after

    def set_exact(self, conn: sqlite3.Connection,
                  item_id: int, new_stock: int) -> tuple[int, int]:
        row = conn.execute(
            "SELECT stock FROM inventory_items WHERE id=?", (item_id,)
        ).fetchone()
        before = row["stock"]
        conn.execute(
            "UPDATE inventory_items SET stock=?, updated_at=datetime('now') WHERE id=?",
            (new_stock, item_id),
        )
        return before, new_stock

    # ── Write — matrix-specific ───────────────────────────────────────────────

    def ensure_matrix_entry(self, conn: sqlite3.Connection,
                            model_id: int, part_type_id: int) -> InventoryItem:
        conn.execute(
            "INSERT OR IGNORE INTO inventory_items (model_id, part_type_id) VALUES (?,?)",
            (model_id, part_type_id),
        )
        row = conn.execute(
            self._SELECT + " WHERE ii.model_id=? AND ii.part_type_id=?",
            (model_id, part_type_id),
        ).fetchone()
        return self._build(row)

    def update_min_stock(self, item_id: int, value: int) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE inventory_items SET min_stock=?, updated_at=datetime('now') WHERE id=?",
                (value, item_id),
            )

    def update_inventur(self, item_id: int, value: int) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE inventory_items SET inventur=?, updated_at=datetime('now') WHERE id=?",
                (value, item_id),
            )

    # ── Builder ───────────────────────────────────────────────────────────────

    def _build(self, row) -> InventoryItem:
        return InventoryItem(
            id=row["id"],
            brand=row["brand"] or "",
            name=row["name"] or "",
            color=row["color"] or "",
            sku=row["sku"],
            barcode=row["barcode"],
            sell_price=row["sell_price"],
            stock=row["stock"],
            min_stock=row["min_stock"],
            inventur=row["inventur"],
            model_id=row["model_id"],
            part_type_id=row["part_type_id"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            model_name=row["model_name"] or "",
            model_brand=row["model_brand"] or "",
            part_type_key=row["pt_key"] or "",
            part_type_name=row["pt_name"] or "",
            part_type_color=row["pt_color"] or "",
        )
