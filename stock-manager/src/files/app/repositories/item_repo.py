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

    def search(self, query: str, limit: int = 20) -> list[InventoryItem]:
        """Search items by barcode (exact) then by name/brand (fuzzy).
        Used by POS dialog for quick item lookup."""
        query = query.strip()
        if not query:
            return []
        # Try exact barcode match first
        by_barcode = self.get_by_barcode(query)
        if by_barcode:
            return [by_barcode]
        # Fuzzy search
        sql = (
            self._SELECT
            + " WHERE ii.is_active = 1 AND ii.stock > 0"
            " AND (ii.brand LIKE ? OR ii.name LIKE ? OR ii.color LIKE ?"
            " OR ii.barcode LIKE ? OR pm.name LIKE ? OR pt.name LIKE ?)"
            " ORDER BY ii.name LIMIT ?"
        )
        s = f"%{query}%"
        with self._conn() as conn:
            rows = conn.execute(sql, (s, s, s, s, s, s, limit)).fetchall()
            return [self._build(r) for r in rows]

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
    ) -> dict[tuple[int, str, str], InventoryItem]:
        """Returns {(model_id, part_type_key, color): InventoryItem} for a category.

        Excludes colorless parent rows when colored siblings exist
        (the parent is only for barcode scanning, not for stock display).
        """
        sql = (self._SELECT +
               " WHERE pt.category_id=? AND ii.model_id IS NOT NULL")
        params: list = [category_id]
        if brand:
            sql += " AND pm.brand=?"
            params.append(brand)
        sql += " ORDER BY pm.sort_order, pt.sort_order, ii.color"
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
            all_items = {(r["model_id"], r["pt_key"], r["color"] or ""): self._build(r) for r in rows}

            # Find which (model_id, pt_key) combos have colors
            has_colors: set[tuple[int, str]] = set()
            for (mid, ptk, clr) in all_items:
                if clr:  # non-empty color
                    has_colors.add((mid, ptk))

            # Exclude colorless parent rows when colors exist
            return {k: v for k, v in all_items.items()
                    if k[2] or (k[0], k[1]) not in has_colors}

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
                    sell_price: Optional[float] = None,
                    expiry_date: Optional[str] = None,
                    warranty_date: Optional[str] = None) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO inventory_items
                   (brand, name, color, stock, barcode, min_stock, sell_price,
                    expiry_date, warranty_date)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (brand.strip(), name.strip(), color.strip(), stock,
                 barcode.strip() if barcode else None, min_stock, sell_price,
                 expiry_date, warranty_date),
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
                       sell_price: Optional[float] = None,
                       image_path: Optional[str] = None,
                       expiry_date: Optional[str] = None,
                       warranty_date: Optional[str] = None) -> None:
        with self._conn() as conn:
            conn.execute(
                """UPDATE inventory_items
                   SET brand=?, name=?, color=?, barcode=?, min_stock=?,
                       sell_price=?, image_path=?, expiry_date=?, warranty_date=?,
                       updated_at=datetime('now')
                   WHERE id=?""",
                (brand.strip(), name.strip(), color.strip(),
                 barcode.strip() if barcode else None,
                 min_stock, sell_price, image_path, expiry_date, warranty_date,
                 item_id),
            )

    def update_image(self, item_id: int, image_path: Optional[str]) -> None:
        """Update only the image_path for an item."""
        with self._conn() as conn:
            conn.execute(
                "UPDATE inventory_items SET image_path=?, updated_at=datetime('now') WHERE id=?",
                (image_path, item_id),
            )

    def delete(self, item_id: int) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM inventory_items WHERE id=?", (item_id,))

    def update_price(self, item_id: int, new_price: float) -> None:
        """Update the sell_price for an inventory item."""
        with self._conn() as conn:
            conn.execute(
                "UPDATE inventory_items SET sell_price=?, updated_at=datetime('now') WHERE id=?",
                (new_price, item_id),
            )

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

    def get_by_part_type(self, part_type_id: int) -> list[InventoryItem]:
        """Get all inventory items for a specific part type (all models)."""
        with self._conn() as conn:
            rows = conn.execute(
                self._SELECT + " WHERE ii.part_type_id=? ORDER BY pm.name",
                (part_type_id,),
            ).fetchall()
        return [self._build(r) for r in rows]

    def get_colored_siblings(self, model_id: int, part_type_id: int) -> list[InventoryItem]:
        """Get all colored variants of a model×part_type combination."""
        sql = self._SELECT + " WHERE ii.model_id=? AND ii.part_type_id=? AND ii.color != '' ORDER BY ii.color"
        with self._conn() as conn:
            rows = conn.execute(sql, (model_id, part_type_id)).fetchall()
        return [self._build(r) for r in rows]

    def get_by_model_parttype_color(self, model_id: int, part_type_id: int, color: str) -> InventoryItem | None:
        """Get a specific colored item."""
        sql = self._SELECT + " WHERE ii.model_id=? AND ii.part_type_id=? AND ii.color=?"
        with self._conn() as conn:
            row = conn.execute(sql, (model_id, part_type_id, color)).fetchone()
        return self._build(row) if row else None

    def update_barcode(self, item_id: int, barcode: str | None) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE inventory_items SET barcode=?, updated_at=datetime('now') WHERE id=?",
                (barcode or None, item_id),
            )

    def get_items_without_barcode(self, category_id: int | None = None,
                                  model_ids: list[int] | None = None,
                                  part_type_ids: list[int] | None = None) -> list[InventoryItem]:
        """Get matrix items that have no barcode, filtered by scope."""
        sql = self._SELECT + " WHERE ii.model_id IS NOT NULL AND (ii.barcode IS NULL OR ii.barcode = '')"
        params: list = []
        if category_id is not None:
            sql += " AND pt.category_id = ?"
            params.append(category_id)
        if model_ids:
            placeholders = ",".join("?" * len(model_ids))
            sql += f" AND ii.model_id IN ({placeholders})"
            params.extend(model_ids)
        if part_type_ids:
            placeholders = ",".join("?" * len(part_type_ids))
            sql += f" AND ii.part_type_id IN ({placeholders})"
            params.extend(part_type_ids)
        sql += " ORDER BY pm.brand, pm.name, pt.sort_order"
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._build(r) for r in rows]

    def get_all_matrix_items(self, category_id: int | None = None) -> list[InventoryItem]:
        """Get all matrix items, optionally filtered by category."""
        sql = self._SELECT + " WHERE ii.model_id IS NOT NULL"
        params: list = []
        if category_id is not None:
            sql += " AND pt.category_id = ?"
            params.append(category_id)
        sql += " ORDER BY pm.brand, pm.name, pt.sort_order"
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._build(r) for r in rows]

    def bulk_update_barcodes(self, updates: list[tuple[int, str]]) -> int:
        """Batch update [(item_id, barcode_text), ...]. Returns count."""
        count = 0
        with self._conn() as conn:
            for item_id, barcode in updates:
                try:
                    conn.execute(
                        "UPDATE inventory_items SET barcode=?, updated_at=datetime('now') WHERE id=?",
                        (barcode, item_id),
                    )
                    count += 1
                except Exception:
                    pass  # skip duplicates
        return count

    # ── Builder ───────────────────────────────────────────────────────────────

    def get_expiring(self, days: int = 30) -> list[InventoryItem]:
        """Items whose expiry_date falls within the next `days` days (not yet expired)."""
        sql = (self._SELECT +
               " WHERE ii.is_active = 1"
               "   AND ii.expiry_date IS NOT NULL"
               "   AND ii.expiry_date > date('now')"
               "   AND ii.expiry_date <= date('now', '+' || ? || ' days')"
               " ORDER BY ii.expiry_date ASC")
        with self._conn() as conn:
            return [self._build(r) for r in conn.execute(sql, (days,)).fetchall()]

    def get_expired(self) -> list[InventoryItem]:
        """Items whose expiry_date has already passed."""
        sql = (self._SELECT +
               " WHERE ii.is_active = 1"
               "   AND ii.expiry_date IS NOT NULL"
               "   AND ii.expiry_date <= date('now')"
               " ORDER BY ii.expiry_date ASC")
        with self._conn() as conn:
            return [self._build(r) for r in conn.execute(sql).fetchall()]

    # ── Builder ───────────────────────────────────────────────────────────────

    def _build(self, row) -> InventoryItem:
        keys = row.keys()
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
            image_path=row["image_path"] if "image_path" in keys else None,
            expiry_date=row["expiry_date"] if "expiry_date" in keys else None,
            warranty_date=row["warranty_date"] if "warranty_date" in keys else None,
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
