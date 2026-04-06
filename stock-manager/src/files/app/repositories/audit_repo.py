"""app/repositories/audit_repo.py — Inventory audit data access layer."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.core.database import get_connection
from app.models.audit import AuditLine, InventoryAudit


class AuditRepository:
    """Repository for inventory audit CRUD operations."""

    def get_all(self) -> list[InventoryAudit]:
        """Fetch all audits with computed counts."""
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                a.id,
                a.name,
                a.status,
                a.notes,
                a.started_at,
                a.completed_at,
                COALESCE(al.total_lines, 0) AS total_lines,
                COALESCE(al.counted_lines, 0) AS counted_lines,
                COALESCE(al.discrepancies, 0) AS discrepancies
            FROM inventory_audits a
            LEFT JOIN (
                SELECT
                    audit_id,
                    COUNT(*) AS total_lines,
                    SUM(CASE WHEN counted_qty IS NOT NULL THEN 1 ELSE 0 END) AS counted_lines,
                    SUM(CASE WHEN (counted_qty - system_qty) != 0 THEN 1 ELSE 0 END) AS discrepancies
                FROM audit_lines
                GROUP BY audit_id
            ) al ON a.id = al.audit_id
            ORDER BY a.started_at DESC
            """
        )

        audits = []
        for row in cur.fetchall():
            audit = InventoryAudit(
                id=row[0],
                name=row[1],
                status=row[2],
                notes=row[3],
                started_at=row[4],
                completed_at=row[5],
                total_lines=row[6],
                counted_lines=row[7],
                discrepancies=row[8],
            )
            audits.append(audit)

        conn.close()
        return audits

    def get_by_id(self, audit_id: int) -> Optional[InventoryAudit]:
        """Fetch a single audit by ID with computed counts."""
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                a.id,
                a.name,
                a.status,
                a.notes,
                a.started_at,
                a.completed_at,
                COALESCE(al.total_lines, 0) AS total_lines,
                COALESCE(al.counted_lines, 0) AS counted_lines,
                COALESCE(al.discrepancies, 0) AS discrepancies
            FROM inventory_audits a
            LEFT JOIN (
                SELECT
                    audit_id,
                    COUNT(*) AS total_lines,
                    SUM(CASE WHEN counted_qty IS NOT NULL THEN 1 ELSE 0 END) AS counted_lines,
                    SUM(CASE WHEN (counted_qty - system_qty) != 0 THEN 1 ELSE 0 END) AS discrepancies
                FROM audit_lines
                GROUP BY audit_id
            ) al ON a.id = al.audit_id
            WHERE a.id = ?
            """,
            (audit_id,),
        )

        row = cur.fetchone()
        conn.close()

        if not row:
            return None

        return InventoryAudit(
            id=row[0],
            name=row[1],
            status=row[2],
            notes=row[3],
            started_at=row[4],
            completed_at=row[5],
            total_lines=row[6],
            counted_lines=row[7],
            discrepancies=row[8],
        )

    def create(self, name: str, notes: str = "") -> int:
        """Create a new audit and return its ID."""
        conn = get_connection()
        cur = conn.cursor()

        now = datetime.now().isoformat()
        cur.execute(
            """
            INSERT INTO inventory_audits (name, status, notes, started_at)
            VALUES (?, ?, ?, ?)
            """,
            (name, "IN_PROGRESS", notes, now),
        )
        audit_id = cur.lastrowid

        conn.commit()
        conn.close()

        return audit_id

    def update_status(
        self, audit_id: int, status: str, completed_at: Optional[str] = None
    ) -> None:
        """Update audit status. If COMPLETED, set completed_at timestamp."""
        conn = get_connection()
        cur = conn.cursor()

        if status == "COMPLETED" and not completed_at:
            completed_at = datetime.now().isoformat()

        cur.execute(
            """
            UPDATE inventory_audits
            SET status = ?, completed_at = ?
            WHERE id = ?
            """,
            (status, completed_at, audit_id),
        )

        conn.commit()
        conn.close()

    def delete(self, audit_id: int) -> None:
        """Delete an audit and its lines."""
        conn = get_connection()
        cur = conn.cursor()

        # Delete lines first (FK constraint)
        cur.execute("DELETE FROM audit_lines WHERE audit_id = ?", (audit_id,))
        # Delete audit
        cur.execute("DELETE FROM inventory_audits WHERE id = ?", (audit_id,))

        conn.commit()
        conn.close()

    def get_lines(self, audit_id: int) -> list[AuditLine]:
        """Fetch all lines for an audit, joined with item data."""
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                al.id,
                al.audit_id,
                al.item_id,
                ii.name,
                ii.barcode,
                al.system_qty,
                al.counted_qty,
                al.difference,
                al.note
            FROM audit_lines al
            JOIN inventory_items ii ON al.item_id = ii.id
            WHERE al.audit_id = ?
            ORDER BY ii.name ASC
            """,
            (audit_id,),
        )

        lines = []
        for row in cur.fetchall():
            line = AuditLine(
                id=row[0],
                audit_id=row[1],
                item_id=row[2],
                item_name=row[3],
                barcode=row[4],
                system_qty=row[5],
                counted_qty=row[6],
                difference=row[7],
                note=row[8],
            )
            lines.append(line)

        conn.close()
        return lines

    def add_line(self, audit_id: int, item_id: int, system_qty: int) -> int:
        """Add a line to an audit and return its ID."""
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO audit_lines (audit_id, item_id, system_qty, counted_qty, difference, note)
            VALUES (?, ?, ?, NULL, NULL, '')
            """,
            (audit_id, item_id, system_qty),
        )
        line_id = cur.lastrowid

        conn.commit()
        conn.close()

        return line_id

    def update_line_count(self, line_id: int, counted_qty: int, note: str = "") -> None:
        """Update counted qty for a line and auto-compute difference."""
        conn = get_connection()
        cur = conn.cursor()

        # Get system_qty to compute difference
        cur.execute("SELECT system_qty FROM audit_lines WHERE id = ?", (line_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return

        system_qty = row[0]
        difference = counted_qty - system_qty

        cur.execute(
            """
            UPDATE audit_lines
            SET counted_qty = ?, difference = ?, note = ?
            WHERE id = ?
            """,
            (counted_qty, difference, note, line_id),
        )

        conn.commit()
        conn.close()

    def populate_from_inventory(self, audit_id: int) -> int:
        """Bulk insert all current inventory items as audit lines. Returns count inserted."""
        conn = get_connection()
        cur = conn.cursor()

        # Get all items with their current qty
        cur.execute(
            """
            SELECT id, stock
            FROM inventory_items
            ORDER BY name ASC
            """
        )

        items = cur.fetchall()
        inserted = 0

        for item_id, current_qty in items:
            cur.execute(
                """
                INSERT INTO audit_lines (audit_id, item_id, system_qty, counted_qty, difference, note)
                VALUES (?, ?, ?, NULL, NULL, '')
                """,
                (audit_id, item_id, current_qty),
            )
            inserted += 1

        conn.commit()
        conn.close()

        return inserted

    def get_summary(self) -> dict:
        """Get summary statistics for all audits."""
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                COUNT(DISTINCT id) AS total_audits,
                SUM(CASE WHEN status = 'IN_PROGRESS' THEN 1 ELSE 0 END) AS in_progress,
                SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN status = 'CANCELLED' THEN 1 ELSE 0 END) AS cancelled
            FROM inventory_audits
            """
        )

        row = cur.fetchone()

        # Get total discrepancies
        cur.execute(
            """
            SELECT COUNT(*) FROM audit_lines
            WHERE difference IS NOT NULL AND difference != 0
            """
        )
        total_discrepancies = cur.fetchone()[0]

        conn.close()

        return {
            "total_audits": row[0] or 0,
            "in_progress": row[1] or 0,
            "completed": row[2] or 0,
            "cancelled": row[3] or 0,
            "total_discrepancies": total_discrepancies,
        }
