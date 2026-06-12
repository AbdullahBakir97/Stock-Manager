"""app/repositories/phone_repo.py — CRUD for individual phone unit inventory."""
from __future__ import annotations

from typing import Optional

from app.models.phone_unit import PhoneUnit
from app.models.phone_transaction import PhoneTransaction
from app.repositories.base import BaseRepository

_SELECT = """
    SELECT p.*, pm.name AS model_name, pm.brand AS model_brand
    FROM phones p
    JOIN phone_models pm ON pm.id = p.model_id
"""

_TX_SELECT = "SELECT * FROM phone_transactions"


def _build(row) -> PhoneUnit:
    return PhoneUnit(
        id          = row["id"],
        model_id    = row["model_id"],
        imei        = row["imei"] or "",
        storage     = row["storage"] or "",
        condition   = row["condition"] or "used",
        battery_pct = row["battery_pct"],
        buy_price   = row["buy_price"],
        sell_price  = row["sell_price"],
        status      = row["status"] or "in_stock",
        notes       = row["notes"] or "",
        created_at  = row["created_at"] or "",
        model_name  = row["model_name"] or "",
        model_brand = row["model_brand"] or "",
    )


def _build_tx(row) -> PhoneTransaction:
    return PhoneTransaction(
        id            = row["id"],
        phone_id      = row["phone_id"],
        operation     = row["operation"],
        status_before = row["status_before"] or "",
        status_after  = row["status_after"] or "",
        imei          = row["imei"] or "",
        model_brand   = row["model_brand"] or "",
        model_name    = row["model_name"] or "",
        storage       = row["storage"] or "",
        sell_price    = row["sell_price"],
        note          = row["note"] or "",
        timestamp     = row["timestamp"] or "",
    )


class PhoneRepository(BaseRepository):

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_all(
        self,
        brand:     str = "",
        storage:   str = "",
        condition: str = "",
        status:    str = "",
        search:    str = "",
    ) -> list[PhoneUnit]:
        sql = _SELECT + " WHERE 1=1"
        params: list = []
        if brand:
            sql += " AND pm.brand = ?"
            params.append(brand)
        if storage:
            sql += " AND p.storage = ?"
            params.append(storage)
        if condition:
            sql += " AND p.condition = ?"
            params.append(condition)
        if status:
            sql += " AND p.status = ?"
            params.append(status)
        if search:
            sql += (
                " AND (p.imei LIKE ? OR pm.name LIKE ? OR pm.brand LIKE ?"
                " OR p.storage LIKE ? OR p.notes LIKE ?)"
            )
            s = f"%{search}%"
            params.extend([s, s, s, s, s])
        sql += " ORDER BY pm.brand, pm.name, p.storage, p.condition, p.created_at DESC"
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_build(r) for r in rows]

    def get_by_model(
        self,
        model_id:  int,
        storage:   str = "",
        condition: str = "",
        status:    str = "in_stock",
    ) -> list[PhoneUnit]:
        sql = _SELECT + " WHERE p.model_id = ?"
        params: list = [model_id]
        if storage:
            sql += " AND p.storage = ?"
            params.append(storage)
        if condition:
            sql += " AND p.condition = ?"
            params.append(condition)
        if status:
            sql += " AND p.status = ?"
            params.append(status)
        sql += " ORDER BY p.storage, p.condition, p.battery_pct DESC"
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_build(r) for r in rows]

    def get_by_id(self, phone_id: int) -> Optional[PhoneUnit]:
        with self._conn() as conn:
            row = conn.execute(
                _SELECT + " WHERE p.id = ?", (phone_id,)
            ).fetchone()
        return _build(row) if row else None

    def get_by_imei(self, imei: str) -> Optional[PhoneUnit]:
        if not imei:
            return None
        with self._conn() as conn:
            row = conn.execute(
                _SELECT + " WHERE p.imei = ?", (imei.strip(),)
            ).fetchone()
        return _build(row) if row else None

    def get_stock_grid(self) -> list[dict]:
        """Aggregate in-stock counts by (model_id, storage). Hot-path for grid render."""
        sql = """
            SELECT p.model_id, pm.name AS model_name, pm.brand AS model_brand,
                   p.storage, COUNT(*) AS cnt
            FROM phones p
            JOIN phone_models pm ON pm.id = p.model_id
            WHERE p.status = 'in_stock'
            GROUP BY p.model_id, p.storage
            ORDER BY pm.brand, pm.name, p.storage
        """
        with self._conn() as conn:
            rows = conn.execute(sql).fetchall()
        return [dict(r) for r in rows]

    def get_all_models_with_phones(self) -> list[dict]:
        """Returns distinct models that have at least one phone (any status)."""
        sql = """
            SELECT DISTINCT pm.id, pm.name AS model_name, pm.brand AS model_brand
            FROM phones p
            JOIN phone_models pm ON pm.id = p.model_id
            ORDER BY pm.brand, pm.name
        """
        with self._conn() as conn:
            rows = conn.execute(sql).fetchall()
        return [dict(r) for r in rows]

    def get_summary(self) -> dict:
        """KPI summary: total, in_stock, sold, reserved, avg_battery, total_value."""
        with self._conn() as conn:
            row = conn.execute("""
                SELECT
                    COUNT(*)                                       AS total,
                    SUM(status = 'in_stock')                       AS in_stock,
                    SUM(status = 'sold')                           AS sold,
                    SUM(status = 'reserved')                       AS reserved,
                    ROUND(AVG(CASE WHEN battery_pct IS NOT NULL
                                   THEN battery_pct END), 1)       AS avg_battery,
                    -- Stock value = cost basis (buy_price). Falls back to
                    -- sell_price only when no buy price was recorded.
                    ROUND(SUM(CASE WHEN status = 'in_stock'
                                   THEN COALESCE(buy_price, sell_price, 0)
                                   ELSE 0 END), 2) AS total_value
                FROM phones
            """).fetchone()
        return {
            "total":       row["total"]       or 0,
            "in_stock":    row["in_stock"]     or 0,
            "sold":        row["sold"]         or 0,
            "reserved":    row["reserved"]     or 0,
            "avg_battery": row["avg_battery"],
            "total_value": row["total_value"]  or 0.0,
        }

    def get_brands(self) -> list[str]:
        """Distinct brands that have at least one phone."""
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT DISTINCT pm.brand
                FROM phones p JOIN phone_models pm ON pm.id = p.model_id
                ORDER BY pm.brand
            """).fetchall()
        return [r["brand"] for r in rows]

    def get_by_scan(self, scan_text: str) -> Optional[PhoneUnit]:
        """Look up a phone unit from scanner input.

        Handles two barcode formats:
          - IMEI (15 digits) → look up phones.imei directly.
          - PHN{digits} code → parse ID, look up phones.id.

        The IMEI is pure digits so German QWERTZ ß/Y-Z transforms don't
        apply; we match the raw scan text after stripping whitespace.
        """
        text = (scan_text or "").strip()
        if not text:
            return None
        # PHN-code: e.g. "PHN00042"
        upper = text.upper()
        if upper.startswith("PHN") and upper[3:].isdigit():
            return self.get_by_id(int(upper[3:]))
        # Strip Code 128 code-set prefix characters that some scanners emit:
        # e.g. leading lowercase 'a', 'b', 'c' before the actual digit payload.
        # Example: scanner outputs "a352199012345678" instead of "352199012345678".
        clean = text.lstrip("abcABC")
        # IMEI: all digits, typically 15 chars (accept 13-16 for scanner quirks)
        if clean.isdigit() and 13 <= len(clean) <= 16:
            return self.get_by_imei(clean)
        return None

    def imei_exists(self, imei: str, exclude_id: int = 0) -> bool:
        if not imei:
            return False
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id FROM phones WHERE imei = ? AND id != ?",
                (imei.strip(), exclude_id),
            ).fetchone()
        return row is not None

    # ── Transaction / audit history ─────────────────────────────────────────────

    def _log_tx(
        self, conn, phone_id: int, operation: str,
        status_before: str = "", status_after: str = "",
        imei: str = "", model_brand: str = "", model_name: str = "",
        storage: str = "", sell_price: Optional[float] = None, note: str = "",
    ) -> None:
        conn.execute(
            """INSERT INTO phone_transactions
               (phone_id, operation, status_before, status_after,
                imei, model_brand, model_name, storage, sell_price, note)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (phone_id, operation, status_before, status_after,
             imei or "", model_brand or "", model_name or "",
             storage or "", sell_price, note or ""),
        )

    def get_transactions(self, phone_id: Optional[int] = None, limit: int = 500) -> list[PhoneTransaction]:
        sql = _TX_SELECT
        params: list = []
        if phone_id is not None:
            sql += " WHERE phone_id = ?"
            params.append(phone_id)
        sql += " ORDER BY timestamp DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_build_tx(r) for r in rows]

    def get_sold_history(
        self, *, search: str = "", date_from: str = "", date_to: str = "",
        limit: int = 500,
    ) -> list[PhoneTransaction]:
        """All 'SOLD' events, most recent first — the Sold Phones history view."""
        sql = _TX_SELECT + " WHERE operation = 'SOLD'"
        params: list = []
        if search:
            sql += " AND (imei LIKE ? OR model_brand LIKE ? OR model_name LIKE ?)"
            s = f"%{search}%"
            params.extend([s, s, s])
        if date_from:
            sql += " AND timestamp >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND timestamp <= ?"
            params.append(date_to + " 23:59:59")
        sql += " ORDER BY timestamp DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_build_tx(r) for r in rows]

    # ── Writes ────────────────────────────────────────────────────────────────

    def add(
        self,
        model_id:    int,
        imei:        str,
        storage:     str,
        condition:   str,
        battery_pct: Optional[int],
        buy_price:   Optional[float],
        sell_price:  Optional[float],
        notes:       str = "",
    ) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO phones
                   (model_id, imei, storage, condition, battery_pct,
                    buy_price, sell_price, notes)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    model_id,
                    imei.strip() or None,
                    storage,
                    condition,
                    battery_pct,
                    buy_price,
                    sell_price,
                    notes.strip(),
                ),
            )
            phone_id = cur.lastrowid
            row = conn.execute(_SELECT + " WHERE p.id = ?", (phone_id,)).fetchone()
            unit = _build(row) if row else None
            self._log_tx(
                conn, phone_id, "CREATE",
                status_before="", status_after="in_stock",
                imei=unit.imei if unit else (imei.strip() or ""),
                model_brand=unit.model_brand if unit else "",
                model_name=unit.model_name if unit else "",
                storage=storage, sell_price=sell_price,
                note="Phone unit added to inventory",
            )
            return phone_id

    def update(
        self,
        phone_id:    int,
        model_id:    int,
        imei:        str,
        storage:     str,
        condition:   str,
        battery_pct: Optional[int],
        buy_price:   Optional[float],
        sell_price:  Optional[float],
        notes:       str = "",
    ) -> None:
        with self._conn() as conn:
            old_row = conn.execute(_SELECT + " WHERE p.id = ?", (phone_id,)).fetchone()
            old = _build(old_row) if old_row else None
            conn.execute(
                """UPDATE phones SET
                   model_id=?, imei=?, storage=?, condition=?,
                   battery_pct=?, buy_price=?, sell_price=?, notes=?
                   WHERE id=?""",
                (
                    model_id,
                    imei.strip() or None,
                    storage,
                    condition,
                    battery_pct,
                    buy_price,
                    sell_price,
                    notes.strip(),
                    phone_id,
                ),
            )
            new_row = conn.execute(_SELECT + " WHERE p.id = ?", (phone_id,)).fetchone()
            new = _build(new_row) if new_row else None
            status = old.status if old else "in_stock"
            self._log_tx(
                conn, phone_id, "EDIT",
                status_before=status, status_after=status,
                imei=new.imei if new else (imei.strip() or ""),
                model_brand=new.model_brand if new else "",
                model_name=new.model_name if new else "",
                storage=storage, sell_price=sell_price,
                note="Phone unit details edited",
            )

    def update_status(self, phone_id: int, status: str) -> None:
        with self._conn() as conn:
            old_row = conn.execute(_SELECT + " WHERE p.id = ?", (phone_id,)).fetchone()
            old = _build(old_row) if old_row else None
            old_status = old.status if old else ""
            conn.execute(
                "UPDATE phones SET status=? WHERE id=?", (status, phone_id)
            )
            operation = {
                "sold": "SOLD",
                "reserved": "RESERVED",
                "in_stock": "IN_STOCK",
            }.get(status, status.upper())
            self._log_tx(
                conn, phone_id, operation,
                status_before=old_status, status_after=status,
                imei=old.imei if old else "",
                model_brand=old.model_brand if old else "",
                model_name=old.model_name if old else "",
                storage=old.storage if old else "",
                sell_price=old.sell_price if old else None,
                note=f"Status changed from {old_status or '?'} to {status}",
            )

    def delete(self, phone_id: int) -> None:
        with self._conn() as conn:
            old_row = conn.execute(_SELECT + " WHERE p.id = ?", (phone_id,)).fetchone()
            old = _build(old_row) if old_row else None
            conn.execute("DELETE FROM phones WHERE id=?", (phone_id,))
            self._log_tx(
                conn, phone_id, "DELETE",
                status_before=old.status if old else "",
                status_after="",
                imei=old.imei if old else "",
                model_brand=old.model_brand if old else "",
                model_name=old.model_name if old else "",
                storage=old.storage if old else "",
                sell_price=old.sell_price if old else None,
                note="Phone unit removed from inventory",
            )

    # ── Portable export / import (cross-database migration) ────────────────────

    def export_units(self) -> list[dict]:
        """Portable dump of every phone unit, keyed by model brand+name rather
        than internal IDs so it can be re-imported into a different database
        (e.g. moving phones onto the PC that holds the master parts data
        before a one-time cloud push)."""
        with self._conn() as conn:
            rows = conn.execute(_SELECT).fetchall()
        return [{
            "model_brand": r["model_brand"] or "",
            "model_name":  r["model_name"] or "",
            "imei":        r["imei"] or "",
            "storage":     r["storage"] or "",
            "condition":   r["condition"] or "used",
            "battery_pct": r["battery_pct"],
            "buy_price":   r["buy_price"],
            "sell_price":  r["sell_price"],
            "status":      r["status"] or "in_stock",
            "notes":       r["notes"] or "",
            "created_at":  r["created_at"] or "",
        } for r in rows]

    def import_units(self, rows: list[dict]) -> dict:
        """Import phone units produced by export_units() into this database.

        Models are matched (or created) by name; phone units are de-duplicated
        by IMEI so re-running the import is safe. Units with a blank IMEI are
        always inserted (they can't be reliably de-duplicated). Returns
        {"imported": n, "skipped": n, "models_created": n}.
        """
        imported = skipped = models_created = 0
        with self._conn() as conn:
            # Cache existing models by name and existing IMEIs up front.
            model_by_name = {
                (r["name"] or "").strip().lower(): r["id"]
                for r in conn.execute("SELECT id, name FROM phone_models").fetchall()
            }
            existing_imeis = {
                (r["imei"] or "").strip()
                for r in conn.execute(
                    "SELECT imei FROM phones WHERE imei IS NOT NULL AND imei != ''"
                ).fetchall()
            }

            for row in rows:
                name  = (row.get("model_name") or "").strip()
                brand = (row.get("model_brand") or "").strip()
                if not name:
                    skipped += 1
                    continue

                key = name.lower()
                model_id = model_by_name.get(key)
                if model_id is None:
                    max_order = conn.execute(
                        "SELECT COALESCE(MAX(sort_order),0) FROM phone_models"
                    ).fetchone()[0]
                    cur = conn.execute(
                        "INSERT INTO phone_models (brand, name, sort_order) VALUES (?,?,?)",
                        (brand, name, max_order + 1),
                    )
                    model_id = cur.lastrowid
                    model_by_name[key] = model_id
                    models_created += 1

                imei = (row.get("imei") or "").strip()
                if imei and imei in existing_imeis:
                    skipped += 1
                    continue

                conn.execute(
                    """INSERT INTO phones
                       (model_id, imei, storage, condition, battery_pct,
                        buy_price, sell_price, status, notes, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (
                        model_id,
                        imei or None,
                        row.get("storage") or "",
                        row.get("condition") or "used",
                        row.get("battery_pct"),
                        row.get("buy_price"),
                        row.get("sell_price"),
                        row.get("status") or "in_stock",
                        row.get("notes") or "",
                        row.get("created_at") or None,
                    ),
                )
                if imei:
                    existing_imeis.add(imei)
                imported += 1

        try:
            from app.repositories.model_repo import _invalidate_model_caches
            _invalidate_model_caches()
        except Exception:
            pass
        return {"imported": imported, "skipped": skipped,
                "models_created": models_created}
