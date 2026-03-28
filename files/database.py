import sqlite3
import os
import sys
from typing import Optional


def _db_path() -> str:
    """
    Resolve database location:
    - Installed / bundled (PyInstaller): LOCALAPPDATA/StockPro/StockManagerPro/
    - Development (running from source):  same folder as database.py
    """
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle — use user's AppData so the DB is writable
        base = os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
            "StockPro", "StockManagerPro",
        )
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, "stock_manager.db")
    # Development: keep DB next to source file
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "stock_manager.db")


DB_PATH = _db_path()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                brand               TEXT NOT NULL,
                type                TEXT NOT NULL,
                color               TEXT NOT NULL,
                stock               INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
                barcode             TEXT UNIQUE,
                low_stock_threshold INTEGER NOT NULL DEFAULT 5,
                created_at          TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id  INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                operation   TEXT NOT NULL CHECK(operation IN ('IN','OUT','ADJUST','CREATE')),
                quantity    INTEGER NOT NULL,
                stock_before INTEGER NOT NULL,
                stock_after  INTEGER NOT NULL,
                note        TEXT,
                timestamp   TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_products_barcode   ON products(barcode);
            CREATE INDEX IF NOT EXISTS idx_transactions_product ON transactions(product_id);
            CREATE INDEX IF NOT EXISTS idx_transactions_time  ON transactions(timestamp);
        """)


# ── Products ──────────────────────────────────────────────────────────────────

def add_product(brand: str, type_: str, color: str, stock: int,
                barcode: Optional[str], low_stock_threshold: int) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO products (brand, type, color, stock, barcode, low_stock_threshold)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (brand.strip(), type_.strip(), color.strip(), stock,
             barcode.strip() if barcode else None, low_stock_threshold),
        )
        pid = cur.lastrowid
        conn.execute(
            """INSERT INTO transactions
               (product_id, operation, quantity, stock_before, stock_after, note)
               VALUES (?, 'CREATE', ?, 0, ?, 'Product created')""",
            (pid, stock, stock),
        )
        return pid


def update_product(product_id: int, brand: str, type_: str, color: str,
                   barcode: Optional[str], low_stock_threshold: int):
    with get_connection() as conn:
        conn.execute(
            """UPDATE products
               SET brand=?, type=?, color=?, barcode=?, low_stock_threshold=?,
                   updated_at=datetime('now')
               WHERE id=?""",
            (brand.strip(), type_.strip(), color.strip(),
             barcode.strip() if barcode else None, low_stock_threshold, product_id),
        )


def delete_product(product_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM products WHERE id=?", (product_id,))


def get_all_products(search: str = "", filter_low_stock: bool = False):
    sql = """
        SELECT p.*,
               CASE WHEN p.stock <= p.low_stock_threshold THEN 1 ELSE 0 END AS is_low
        FROM products p WHERE 1=1
    """
    params: list = []
    if search:
        sql += " AND (p.brand LIKE ? OR p.type LIKE ? OR p.color LIKE ? OR p.barcode LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s, s])
    if filter_low_stock:
        sql += " AND p.stock <= p.low_stock_threshold"
    sql += " ORDER BY p.brand, p.type, p.color"
    with get_connection() as conn:
        return conn.execute(sql, params).fetchall()


def get_product_by_id(product_id: int):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()


def get_product_by_barcode(barcode: str):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM products WHERE barcode=?", (barcode.strip(),)
        ).fetchone()


# ── Stock Operations ──────────────────────────────────────────────────────────

def stock_in(product_id: int, quantity: int, note: str = "") -> dict:
    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    with get_connection() as conn:
        row = conn.execute("SELECT stock FROM products WHERE id=?", (product_id,)).fetchone()
        if not row:
            raise ValueError("Product not found")
        before = row["stock"]
        after  = before + quantity
        conn.execute(
            "UPDATE products SET stock=?, updated_at=datetime('now') WHERE id=?",
            (after, product_id),
        )
        conn.execute(
            """INSERT INTO transactions
               (product_id, operation, quantity, stock_before, stock_after, note)
               VALUES (?, 'IN', ?, ?, ?, ?)""",
            (product_id, quantity, before, after, note),
        )
        return {"before": before, "after": after, "delta": quantity}


def stock_out(product_id: int, quantity: int, note: str = "") -> dict:
    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    with get_connection() as conn:
        row = conn.execute("SELECT stock FROM products WHERE id=?", (product_id,)).fetchone()
        if not row:
            raise ValueError("Product not found")
        before = row["stock"]
        if quantity > before:
            raise ValueError(
                f"Insufficient stock.  Available: {before}   Requested: {quantity}"
            )
        after = before - quantity
        conn.execute(
            "UPDATE products SET stock=?, updated_at=datetime('now') WHERE id=?",
            (after, product_id),
        )
        conn.execute(
            """INSERT INTO transactions
               (product_id, operation, quantity, stock_before, stock_after, note)
               VALUES (?, 'OUT', ?, ?, ?, ?)""",
            (product_id, quantity, before, after, note),
        )
        return {"before": before, "after": after, "delta": -quantity}


def adjust_stock(product_id: int, new_stock: int, note: str = "") -> dict:
    if new_stock < 0:
        raise ValueError("Stock cannot be negative")
    with get_connection() as conn:
        row = conn.execute("SELECT stock FROM products WHERE id=?", (product_id,)).fetchone()
        if not row:
            raise ValueError("Product not found")
        before = row["stock"]
        conn.execute(
            "UPDATE products SET stock=?, updated_at=datetime('now') WHERE id=?",
            (new_stock, product_id),
        )
        conn.execute(
            """INSERT INTO transactions
               (product_id, operation, quantity, stock_before, stock_after, note)
               VALUES (?, 'ADJUST', ?, ?, ?, ?)""",
            (product_id, abs(new_stock - before), before, new_stock, note),
        )
        return {"before": before, "after": new_stock, "delta": new_stock - before}


# ── Transactions ──────────────────────────────────────────────────────────────

def get_transactions(product_id: Optional[int] = None, limit: int = 500):
    sql = """
        SELECT t.*, p.brand, p.type, p.color, p.barcode
        FROM transactions t
        JOIN products p ON p.id = t.product_id
    """
    params: list = []
    if product_id:
        sql += " WHERE t.product_id=?"
        params.append(product_id)
    sql += " ORDER BY t.timestamp DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        return conn.execute(sql, params).fetchall()


def get_low_stock_products():
    with get_connection() as conn:
        return conn.execute(
            """SELECT * FROM products
               WHERE stock <= low_stock_threshold
               ORDER BY (stock * 1.0 / NULLIF(low_stock_threshold, 0)) ASC"""
        ).fetchall()


# ── Summary Stats ─────────────────────────────────────────────────────────────

def get_summary() -> dict:
    with get_connection() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*)  AS total_products,
                SUM(stock) AS total_units,
                SUM(CASE WHEN stock <= low_stock_threshold THEN 1 ELSE 0 END) AS low_stock_count,
                SUM(CASE WHEN stock = 0 THEN 1 ELSE 0 END) AS out_of_stock_count
            FROM products
        """).fetchone()
        return dict(row) if row else {}


def get_distinct_brands() -> list[str]:
    with get_connection() as conn:
        return [r["brand"] for r in
                conn.execute("SELECT DISTINCT brand FROM products ORDER BY brand").fetchall()]


def get_distinct_types() -> list[str]:
    with get_connection() as conn:
        return [r["type"] for r in
                conn.execute("SELECT DISTINCT type FROM products ORDER BY type").fetchall()]
