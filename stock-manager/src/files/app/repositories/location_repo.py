"""app/repositories/location_repo.py — Location, location stock, and transfers."""
from __future__ import annotations

from typing import Optional

from app.repositories.base import BaseRepository
from app.models.location import Location, LocationStock, StockTransfer


class LocationRepository(BaseRepository):

    # ── Location CRUD ────────────────────────────────────────────────────────

    def get_all(self, active_only: bool = False) -> list[Location]:
        with self._conn() as conn:
            sql = "SELECT * FROM locations"
            if active_only:
                sql += " WHERE is_active = 1"
            sql += " ORDER BY is_default DESC, name"
            return [self._build(r) for r in conn.execute(sql).fetchall()]

    def get_by_id(self, location_id: int) -> Optional[Location]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM locations WHERE id=?", (location_id,)
            ).fetchone()
            return self._build(row) if row else None

    def get_default(self) -> Optional[Location]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM locations WHERE is_default = 1 LIMIT 1"
            ).fetchone()
            return self._build(row) if row else None

    def add(self, name: str, description: str = "",
            is_default: bool = False) -> int:
        with self._conn() as conn:
            if is_default:
                conn.execute("UPDATE locations SET is_default = 0")
            cur = conn.execute(
                """INSERT INTO locations (name, description, is_default)
                   VALUES (?,?,?)""",
                (name.strip(), description.strip(), int(is_default)),
            )
            return cur.lastrowid

    def update(self, location_id: int, name: str, description: str = "",
               is_default: bool = False, is_active: bool = True) -> None:
        with self._conn() as conn:
            if is_default:
                conn.execute("UPDATE locations SET is_default = 0")
            conn.execute(
                """UPDATE locations
                   SET name=?, description=?, is_default=?, is_active=?
                   WHERE id=?""",
                (name.strip(), description.strip(),
                 int(is_default), int(is_active), location_id),
            )

    def delete(self, location_id: int) -> bool:
        """Delete location. Blocks if it holds stock or is the default."""
        with self._conn() as conn:
            loc = conn.execute(
                "SELECT is_default FROM locations WHERE id=?", (location_id,)
            ).fetchone()
            if not loc:
                return False
            if loc["is_default"]:
                return False  # cannot delete default location
            has_stock = conn.execute(
                "SELECT COUNT(*) FROM location_stock WHERE location_id=? AND quantity > 0",
                (location_id,),
            ).fetchone()
            if has_stock and has_stock[0] > 0:
                return False
            conn.execute("DELETE FROM locations WHERE id=?", (location_id,))
            return True

    # ── Location Stock ───────────────────────────────────────────────────────

    def get_stock(self, item_id: int) -> list[LocationStock]:
        """Get stock breakdown by location for a single item."""
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT ls.*, l.name AS location_name
                   FROM location_stock ls
                   JOIN locations l ON l.id = ls.location_id
                   WHERE ls.item_id=?
                   ORDER BY l.name""",
                (item_id,),
            ).fetchall()
            return [self._build_ls(r) for r in rows]

    def get_location_items(self, location_id: int) -> list[LocationStock]:
        """Get all items and quantities at a given location."""
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT ls.*, l.name AS location_name,
                          COALESCE(ii.name, pm.name, '') AS item_name
                   FROM location_stock ls
                   JOIN locations l ON l.id = ls.location_id
                   JOIN inventory_items ii ON ii.id = ls.item_id
                   LEFT JOIN phone_models pm ON pm.id = ii.model_id
                   WHERE ls.location_id=? AND ls.quantity > 0
                   ORDER BY item_name""",
                (location_id,),
            ).fetchall()
            return [self._build_ls(r) for r in rows]

    def set_stock(self, item_id: int, location_id: int, quantity: int) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO location_stock (item_id, location_id, quantity)
                   VALUES (?,?,?)
                   ON CONFLICT(item_id, location_id) DO UPDATE SET quantity=?""",
                (item_id, location_id, quantity, quantity),
            )

    def adjust_stock(self, item_id: int, location_id: int, delta: int) -> int:
        """Add or subtract stock at a location. Returns new quantity."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT quantity FROM location_stock WHERE item_id=? AND location_id=?",
                (item_id, location_id),
            ).fetchone()
            current = row["quantity"] if row else 0
            new_qty = max(0, current + delta)
            conn.execute(
                """INSERT INTO location_stock (item_id, location_id, quantity)
                   VALUES (?,?,?)
                   ON CONFLICT(item_id, location_id) DO UPDATE SET quantity=?""",
                (item_id, location_id, new_qty, new_qty),
            )
            return new_qty

    # ── Transfers ────────────────────────────────────────────────────────────

    def transfer(self, item_id: int, from_id: int, to_id: int,
                 quantity: int, note: str = "") -> int:
        """Move stock between locations. Returns transfer record id."""
        with self._conn() as conn:
            # Decrease source
            self.adjust_stock(item_id, from_id, -quantity)
            # Increase destination
            self.adjust_stock(item_id, to_id, quantity)
            cur = conn.execute(
                """INSERT INTO stock_transfers
                   (item_id, from_location_id, to_location_id, quantity, note)
                   VALUES (?,?,?,?,?)""",
                (item_id, from_id, to_id, quantity, note.strip()),
            )
            return cur.lastrowid

    def get_transfers(self, item_id: Optional[int] = None,
                      limit: int = 100) -> list[StockTransfer]:
        with self._conn() as conn:
            sql = """SELECT st.*,
                            COALESCE(ii.name, pm.name, '') AS item_name,
                            fl.name AS from_location_name,
                            tl.name AS to_location_name
                     FROM stock_transfers st
                     JOIN inventory_items ii ON ii.id = st.item_id
                     LEFT JOIN phone_models pm ON pm.id = ii.model_id
                     JOIN locations fl ON fl.id = st.from_location_id
                     JOIN locations tl ON tl.id = st.to_location_id"""
            params: list = []
            if item_id is not None:
                sql += " WHERE st.item_id=?"
                params.append(item_id)
            sql += " ORDER BY st.timestamp DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
            return [self._build_st(r) for r in rows]

    # ── Builders ─────────────────────────────────────────────────────────────

    def _build(self, row) -> Location:
        return Location(
            id=row["id"], name=row["name"],
            description=row["description"],
            is_default=bool(row["is_default"]),
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
        )

    def _build_ls(self, row) -> LocationStock:
        return LocationStock(
            id=row["id"], item_id=row["item_id"],
            location_id=row["location_id"],
            quantity=row["quantity"],
            location_name=row["location_name"] if "location_name" in row.keys() else "",
            item_name=row["item_name"] if "item_name" in row.keys() else "",
        )

    def _build_st(self, row) -> StockTransfer:
        return StockTransfer(
            id=row["id"], item_id=row["item_id"],
            from_location_id=row["from_location_id"],
            to_location_id=row["to_location_id"],
            quantity=row["quantity"],
            note=row["note"], timestamp=row["timestamp"],
            item_name=row["item_name"] if "item_name" in row.keys() else "",
            from_location_name=row["from_location_name"] if "from_location_name" in row.keys() else "",
            to_location_name=row["to_location_name"] if "to_location_name" in row.keys() else "",
        )
