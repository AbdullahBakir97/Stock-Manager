"""app/repositories/price_list_repo.py — Price list data access."""
from __future__ import annotations

from app.core.database import get_connection
from app.models.price_list import MarginAnalysis, PriceList, PriceListItem


class PriceListRepository:
    """Repository for price list operations."""

    def get_all(self) -> list[PriceList]:
        """Get all price lists with item count."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                pl.id,
                pl.name,
                pl.description,
                pl.is_active,
                pl.created_at,
                COUNT(pli.id) as item_count
            FROM price_lists pl
            LEFT JOIN price_list_items pli ON pl.id = pli.price_list_id
            GROUP BY pl.id
            ORDER BY pl.created_at DESC
            """
        )
        rows = cursor.fetchall()
        conn.close()

        result = []
        for row in rows:
            result.append(
                PriceList(
                    id=row[0],
                    name=row[1],
                    description=row[2],
                    is_active=bool(row[3]),
                    created_at=row[4],
                    item_count=row[5],
                )
            )
        return result

    def get_by_id(self, list_id: int) -> PriceList | None:
        """Get a price list by ID."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                pl.id,
                pl.name,
                pl.description,
                pl.is_active,
                pl.created_at,
                COUNT(pli.id) as item_count
            FROM price_lists pl
            LEFT JOIN price_list_items pli ON pl.id = pli.price_list_id
            WHERE pl.id = ?
            GROUP BY pl.id
            """,
            (list_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return PriceList(
            id=row[0],
            name=row[1],
            description=row[2],
            is_active=bool(row[3]),
            created_at=row[4],
            item_count=row[5],
        )

    def create(self, name: str, description: str = "") -> int:
        """Create a new price list."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO price_lists (name, description, is_active, created_at)
            VALUES (?, ?, 1, datetime('now'))
            """,
            (name, description),
        )
        conn.commit()
        list_id = cursor.lastrowid
        conn.close()
        return list_id

    def update(
        self, list_id: int, name: str, description: str, is_active: bool
    ) -> None:
        """Update a price list."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE price_lists
            SET name = ?, description = ?, is_active = ?
            WHERE id = ?
            """,
            (name, description, 1 if is_active else 0, list_id),
        )
        conn.commit()
        conn.close()

    def delete(self, list_id: int) -> None:
        """Delete a price list and its items."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM price_list_items WHERE price_list_id = ?", (list_id,))
        cursor.execute("DELETE FROM price_lists WHERE id = ?", (list_id,))
        conn.commit()
        conn.close()

    def get_items(self, list_id: int) -> list[PriceListItem]:
        """Get all items in a price list with cost and margin."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                pli.id,
                pli.price_list_id,
                pli.item_id,
                CASE
                    WHEN ii.model_id IS NOT NULL
                    THEN COALESCE(pm.brand, '') || ' ' || COALESCE(pm.name, '')
                         || ' · ' || COALESCE(pt.name, '')
                         || CASE WHEN ii.color != '' THEN ' · ' || ii.color ELSE '' END
                    ELSE COALESCE(NULLIF(ii.brand || ' ' || ii.name, ' '), 'Item #' || ii.id)
                END AS display_name,
                ii.barcode,
                ii.sell_price,
                pli.price,
                COALESCE(si.cost_price, 0.0) as cost_price,
                ii.stock
            FROM price_list_items pli
            JOIN inventory_items ii ON pli.item_id = ii.id
            LEFT JOIN phone_models pm ON pm.id = ii.model_id
            LEFT JOIN part_types pt ON pt.id = ii.part_type_id
            LEFT JOIN supplier_items si ON ii.id = si.item_id
            WHERE pli.price_list_id = ?
            ORDER BY display_name
            """,
            (list_id,),
        )
        rows = cursor.fetchall()
        conn.close()

        result = []
        for row in rows:
            cost_price = row[7] or 0.0
            list_price = row[6] or 0.0
            margin_pct = 0.0
            if list_price > 0 and cost_price > 0:
                margin_pct = ((list_price - cost_price) / list_price) * 100

            result.append(
                PriceListItem(
                    id=row[0],
                    price_list_id=row[1],
                    item_id=row[2],
                    item_name=row[3] or f"Item #{row[2]}",
                    barcode=row[4],
                    current_price=row[5],
                    list_price=list_price,
                    cost_price=cost_price,
                    margin_pct=margin_pct,
                    stock=row[8] or 0,
                )
            )
        return result

    def add_item(self, list_id: int, item_id: int, price: float) -> int:
        """Add an item to a price list."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO price_list_items (price_list_id, item_id, price)
            VALUES (?, ?, ?)
            """,
            (list_id, item_id, price),
        )
        conn.commit()
        item_id_result = cursor.lastrowid
        conn.close()
        return item_id_result

    def update_item_price(self, pli_id: int, price: float) -> None:
        """Update the price of an item in a price list."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE price_list_items
            SET price = ?
            WHERE id = ?
            """,
            (price, pli_id),
        )
        conn.commit()
        conn.close()

    def remove_item(self, pli_id: int) -> None:
        """Remove an item from a price list."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM price_list_items WHERE id = ?", (pli_id,))
        conn.commit()
        conn.close()

    def bulk_add_all_items(self, list_id: int) -> int:
        """Add all inventory items to a price list with their current sell price."""
        conn = get_connection()
        cursor = conn.cursor()

        # Get all items not already in list
        cursor.execute(
            """
            INSERT INTO price_list_items (price_list_id, item_id, price)
            SELECT ?, ii.id, COALESCE(ii.sell_price, 0.0)
            FROM inventory_items ii
            WHERE ii.is_active = 1
              AND ii.id NOT IN (
                SELECT item_id FROM price_list_items WHERE price_list_id = ?
            )
            """,
            (list_id, list_id),
        )
        conn.commit()
        count = cursor.rowcount
        conn.close()
        return count

    def get_margin_analysis(self) -> list[MarginAnalysis]:
        """Get margin analysis for all inventory items."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                ii.id,
                CASE
                    WHEN ii.model_id IS NOT NULL
                    THEN COALESCE(pm.brand, '') || ' ' || COALESCE(pm.name, '')
                         || ' · ' || COALESCE(pt.name, '')
                         || CASE WHEN ii.color != '' THEN ' · ' || ii.color ELSE '' END
                    ELSE COALESCE(NULLIF(ii.brand || ' ' || ii.name, ' '), 'Item #' || ii.id)
                END AS display_name,
                ii.barcode,
                ii.sell_price,
                COALESCE(si.cost_price, 0.0) as cost_price,
                ii.stock
            FROM inventory_items ii
            LEFT JOIN phone_models pm ON pm.id = ii.model_id
            LEFT JOIN part_types pt ON pt.id = ii.part_type_id
            LEFT JOIN supplier_items si ON ii.id = si.item_id
            WHERE ii.is_active = 1
            ORDER BY display_name
            """
        )
        rows = cursor.fetchall()
        conn.close()

        result = []
        for row in rows:
            item_id = row[0]
            item_name = row[1] or f"Item #{row[0]}"
            barcode = row[2]
            sell_price = row[3] or 0.0
            cost_price = row[4] or 0.0
            stock = row[5] or 0

            margin_amount = sell_price - cost_price
            margin_pct = 0.0
            if sell_price > 0:
                margin_pct = (margin_amount / sell_price) * 100

            potential_profit = margin_amount * stock

            result.append(
                MarginAnalysis(
                    item_id=item_id,
                    item_name=item_name,
                    barcode=barcode,
                    sell_price=sell_price,
                    cost_price=cost_price,
                    margin_amount=margin_amount,
                    margin_pct=margin_pct,
                    stock=stock,
                    potential_profit=potential_profit,
                )
            )
        return result

    def get_summary(self) -> dict:
        """Get summary statistics for price lists."""
        conn = get_connection()
        cursor = conn.cursor()

        # Total and active lists
        cursor.execute(
            """
            SELECT COUNT(*) as total, SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active
            FROM price_lists
            """
        )
        row = cursor.fetchone()
        total_lists = row[0] or 0
        active_lists = row[1] or 0

        # Total items priced
        cursor.execute("SELECT COUNT(*) FROM price_list_items")
        total_items_priced = cursor.fetchone()[0] or 0

        # Average margin
        cursor.execute(
            """
            SELECT AVG(
                CASE
                    WHEN pli.price > 0 AND si.cost_price > 0
                    THEN ((pli.price - si.cost_price) / pli.price) * 100
                    ELSE 0
                END
            ) as avg_margin
            FROM price_list_items pli
            LEFT JOIN inventory_items ii ON pli.item_id = ii.id
            LEFT JOIN supplier_items si ON ii.id = si.item_id
            """
        )
        avg_margin = cursor.fetchone()[0] or 0.0

        conn.close()

        return {
            "total_lists": total_lists,
            "active_lists": active_lists,
            "total_items_priced": total_items_priced,
            "avg_margin": float(avg_margin),
        }
