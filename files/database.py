import sqlite3
import os
import sys
from typing import Optional

# ── Display type keys (fixed) ─────────────────────────────────────────────────
DISPLAY_TYPE_KEYS = [
    "JK_INCELL_FHD",
    "DD_SOFT_OLED",
    "DD_SOFT_OLED_DIAG",
    "ORG_PULLED",
    "ORG_DIAGNOSE_USED",
]

# Default models seeded on first run: (name, sort_order, brand)
_DEFAULT_MODELS = [
    # Apple
    ("X / XS",        1,  "Apple"), ("XR",             2,  "Apple"), ("XS max",         3,  "Apple"),
    ("11",            4,  "Apple"), ("11 Pro",         5,  "Apple"), ("11 Pro max",      6,  "Apple"),
    ("12 mini",       7,  "Apple"), ("12 / 12 Pro",    8,  "Apple"), ("12 Pro max",      9,  "Apple"),
    ("13 mini",      10,  "Apple"), ("13",            11,  "Apple"), ("13 Pro",         12,  "Apple"),
    ("13 Pro max",   13,  "Apple"), ("14",            14,  "Apple"), ("14 Plus",        15,  "Apple"),
    ("14 Pro",       16,  "Apple"), ("14 Pro max",    17,  "Apple"), ("15",             18,  "Apple"),
    ("15 Plus",      19,  "Apple"), ("15 Pro",        20,  "Apple"), ("15 Pro max",     21,  "Apple"),
    ("16",           22,  "Apple"), ("16 Plus",       23,  "Apple"), ("16 Pro",         24,  "Apple"),
    ("16 Pro max",   25,  "Apple"),
    # Samsung
    ("Galaxy S21",    1, "Samsung"), ("Galaxy S21+",   2, "Samsung"), ("Galaxy S21 Ultra", 3, "Samsung"),
    ("Galaxy S22",    4, "Samsung"), ("Galaxy S22+",   5, "Samsung"), ("Galaxy S22 Ultra", 6, "Samsung"),
    ("Galaxy S23",    7, "Samsung"), ("Galaxy S23+",   8, "Samsung"), ("Galaxy S23 Ultra", 9, "Samsung"),
    ("Galaxy S24",   10, "Samsung"), ("Galaxy S24+",  11, "Samsung"), ("Galaxy S24 Ultra",12, "Samsung"),
    ("Galaxy A32",   13, "Samsung"), ("Galaxy A52",   14, "Samsung"), ("Galaxy A53",      15, "Samsung"),
    ("Galaxy A54",   16, "Samsung"), ("Galaxy A72",   17, "Samsung"),
]

# Mock stock data seeded on first run: (model_name, display_type, stamm_zahl, stock)
_MOCK_DISPLAY_DATA = [
    # Apple — mix of deficit (red), OK (green), zero (out)
    ("X / XS",       "JK_INCELL_FHD",     12, 10), ("X / XS",       "DD_SOFT_OLED",      8,  5),
    ("X / XS",       "DD_SOFT_OLED_DIAG",  5,  0), ("X / XS",       "ORG_PULLED",         5,  2),
    ("X / XS",       "ORG_DIAGNOSE_USED",  3,  1),
    ("XR",           "JK_INCELL_FHD",     10,  5), ("XR",           "DD_SOFT_OLED",       5,  0),
    ("XR",           "ORG_PULLED",         5,  3),
    ("XS max",       "JK_INCELL_FHD",     15, 16), ("XS max",       "DD_SOFT_OLED",      10,  8),
    ("XS max",       "ORG_PULLED",         8,  6),
    ("11",           "JK_INCELL_FHD",     20, 18), ("11",           "DD_SOFT_OLED",      15, 12),
    ("11",           "ORG_PULLED",         8, 10), ("11",           "ORG_DIAGNOSE_USED",  4,  2),
    ("12 / 12 Pro",  "JK_INCELL_FHD",     18, 22), ("12 / 12 Pro",  "DD_SOFT_OLED",      12,  8),
    ("12 / 12 Pro",  "DD_SOFT_OLED_DIAG",  6,  4), ("12 / 12 Pro",  "ORG_PULLED",        10, 15),
    ("13 Pro",       "DD_SOFT_OLED",      20, 14), ("13 Pro",       "DD_SOFT_OLED_DIAG",  8,  3),
    ("13 Pro",       "ORG_PULLED",        10,  9), ("13 Pro",       "ORG_DIAGNOSE_USED",  5,  7),
    ("14 Pro",       "DD_SOFT_OLED",      25, 20), ("14 Pro",       "DD_SOFT_OLED_DIAG", 10,  6),
    ("14 Pro",       "ORG_PULLED",        12, 18), ("14 Pro",       "ORG_DIAGNOSE_USED",  6,  4),
    ("15 Pro",       "DD_SOFT_OLED",      22, 22), ("15 Pro",       "DD_SOFT_OLED_DIAG",  8,  0),
    ("15 Pro",       "ORG_PULLED",        10,  7),
    ("16 Pro",       "DD_SOFT_OLED",      18,  5), ("16 Pro",       "ORG_PULLED",        10,  3),
    # Samsung
    ("Galaxy S22",   "JK_INCELL_FHD",     10,  7), ("Galaxy S22",   "DD_SOFT_OLED",      15, 18),
    ("Galaxy S22 Ultra","DD_SOFT_OLED",   20, 12), ("Galaxy S22 Ultra","ORG_PULLED",      10,  8),
    ("Galaxy S23",   "DD_SOFT_OLED",      12,  5), ("Galaxy S23",   "DD_SOFT_OLED_DIAG",  6,  0),
    ("Galaxy S23 Ultra","DD_SOFT_OLED",   18, 15), ("Galaxy S23 Ultra","ORG_PULLED",       8, 10),
    ("Galaxy S24",   "DD_SOFT_OLED",      15,  9), ("Galaxy S24 Ultra","DD_SOFT_OLED",    20, 14),
    ("Galaxy S24 Ultra","DD_SOFT_OLED_DIAG", 8, 3),("Galaxy A54",   "JK_INCELL_FHD",     12,  8),
]


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

            CREATE TABLE IF NOT EXISTS phone_models (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL UNIQUE,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS display_stock (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id     INTEGER NOT NULL REFERENCES phone_models(id) ON DELETE CASCADE,
                display_type TEXT NOT NULL,
                stamm_zahl   INTEGER NOT NULL DEFAULT 0,
                stock        INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
                inventur     INTEGER,
                updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(model_id, display_type)
            );

            CREATE TABLE IF NOT EXISTS display_transactions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id     INTEGER NOT NULL,
                display_type TEXT NOT NULL,
                operation    TEXT NOT NULL,
                quantity     INTEGER NOT NULL,
                stock_before INTEGER NOT NULL,
                stock_after  INTEGER NOT NULL,
                note         TEXT,
                timestamp    TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_products_barcode     ON products(barcode);
            CREATE INDEX IF NOT EXISTS idx_transactions_product ON transactions(product_id);
            CREATE INDEX IF NOT EXISTS idx_transactions_time    ON transactions(timestamp);
            CREATE INDEX IF NOT EXISTS idx_display_stock_model  ON display_stock(model_id);
            CREATE INDEX IF NOT EXISTS idx_display_txn          ON display_transactions(model_id, display_type);
        """)

        # Safe migration: add brand column if it doesn't exist yet
        existing = {r[1] for r in conn.execute("PRAGMA table_info(phone_models)").fetchall()}
        if "brand" not in existing:
            conn.execute("ALTER TABLE phone_models ADD COLUMN brand TEXT NOT NULL DEFAULT 'Apple'")

        # Seed phone models on first run
        count = conn.execute("SELECT COUNT(*) FROM phone_models").fetchone()[0]
        first_run = count == 0
        if first_run:
            conn.executemany(
                "INSERT OR IGNORE INTO phone_models (name, sort_order, brand) VALUES (?, ?, ?)",
                _DEFAULT_MODELS,
            )

        # Ensure a display_stock row exists for every model × display_type combo
        models = conn.execute("SELECT id, name FROM phone_models").fetchall()
        for m in models:
            for dtype in DISPLAY_TYPE_KEYS:
                conn.execute(
                    "INSERT OR IGNORE INTO display_stock (model_id, display_type) VALUES (?, ?)",
                    (m["id"], dtype),
                )

        # Seed mock display data on first run
        if first_run:
            name_to_id = {m["name"]: m["id"] for m in models}
            # Re-fetch after insert
            name_to_id = {
                r["name"]: r["id"]
                for r in conn.execute("SELECT id, name FROM phone_models").fetchall()
            }
            for model_name, dtype, stamm, stock in _MOCK_DISPLAY_DATA:
                mid = name_to_id.get(model_name)
                if mid:
                    conn.execute(
                        """UPDATE display_stock SET stamm_zahl=?, stock=?
                           WHERE model_id=? AND display_type=?""",
                        (stamm, stock, mid, dtype),
                    )


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


# ── Phone Models ──────────────────────────────────────────────────────────────

def get_phone_models(brand: Optional[str] = None) -> list[dict]:
    with get_connection() as conn:
        if brand:
            rows = conn.execute(
                "SELECT id, name, brand, sort_order FROM phone_models WHERE brand=? ORDER BY sort_order",
                (brand,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, name, brand, sort_order FROM phone_models ORDER BY brand, sort_order"
            ).fetchall()
        return [dict(r) for r in rows]


def get_phone_brands() -> list[str]:
    with get_connection() as conn:
        return [
            r["brand"]
            for r in conn.execute(
                "SELECT DISTINCT brand FROM phone_models ORDER BY brand"
            ).fetchall()
        ]


def add_phone_model(brand: str, name: str) -> int:
    brand = brand.strip(); name = name.strip()
    with get_connection() as conn:
        max_order = conn.execute(
            "SELECT COALESCE(MAX(sort_order), 0) FROM phone_models WHERE brand=?", (brand,)
        ).fetchone()[0]
        cur = conn.execute(
            "INSERT INTO phone_models (name, brand, sort_order) VALUES (?, ?, ?)",
            (name, brand, max_order + 1),
        )
        mid = cur.lastrowid
        for dtype in DISPLAY_TYPE_KEYS:
            conn.execute(
                "INSERT OR IGNORE INTO display_stock (model_id, display_type) VALUES (?, ?)",
                (mid, dtype),
            )
        return mid


# ── Display Stock ─────────────────────────────────────────────────────────────

def get_all_display_stock() -> dict:
    """Returns {(model_id, display_type): {id, stamm_zahl, stock, inventur}}"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, model_id, display_type, stamm_zahl, stock, inventur FROM display_stock"
        ).fetchall()
        return {(r["model_id"], r["display_type"]): dict(r) for r in rows}


def _ensure_display_row(conn, model_id: int, display_type: str) -> dict:
    row = conn.execute(
        "SELECT * FROM display_stock WHERE model_id=? AND display_type=?",
        (model_id, display_type),
    ).fetchone()
    if not row:
        conn.execute(
            "INSERT OR IGNORE INTO display_stock (model_id, display_type) VALUES (?, ?)",
            (model_id, display_type),
        )
        row = conn.execute(
            "SELECT * FROM display_stock WHERE model_id=? AND display_type=?",
            (model_id, display_type),
        ).fetchone()
    return dict(row)


def set_display_stamm_zahl(model_id: int, display_type: str, stamm_zahl: int):
    with get_connection() as conn:
        _ensure_display_row(conn, model_id, display_type)
        conn.execute(
            """UPDATE display_stock SET stamm_zahl=?, updated_at=datetime('now')
               WHERE model_id=? AND display_type=?""",
            (stamm_zahl, model_id, display_type),
        )


def display_stock_in(model_id: int, display_type: str, quantity: int, note: str = ""):
    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    with get_connection() as conn:
        row = _ensure_display_row(conn, model_id, display_type)
        before = row["stock"]
        after  = before + quantity
        conn.execute(
            "UPDATE display_stock SET stock=?, updated_at=datetime('now') WHERE model_id=? AND display_type=?",
            (after, model_id, display_type),
        )
        conn.execute(
            """INSERT INTO display_transactions
               (model_id, display_type, operation, quantity, stock_before, stock_after, note)
               VALUES (?, ?, 'IN', ?, ?, ?, ?)""",
            (model_id, display_type, quantity, before, after, note),
        )
        return {"before": before, "after": after}


def display_stock_out(model_id: int, display_type: str, quantity: int, note: str = ""):
    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    with get_connection() as conn:
        row = _ensure_display_row(conn, model_id, display_type)
        before = row["stock"]
        if quantity > before:
            raise ValueError(f"Insufficient stock.  Available: {before}   Requested: {quantity}")
        after = before - quantity
        conn.execute(
            "UPDATE display_stock SET stock=?, updated_at=datetime('now') WHERE model_id=? AND display_type=?",
            (after, model_id, display_type),
        )
        conn.execute(
            """INSERT INTO display_transactions
               (model_id, display_type, operation, quantity, stock_before, stock_after, note)
               VALUES (?, ?, 'OUT', ?, ?, ?, ?)""",
            (model_id, display_type, quantity, before, after, note),
        )
        return {"before": before, "after": after}


def display_stock_adjust(model_id: int, display_type: str, new_stock: int, note: str = ""):
    if new_stock < 0:
        raise ValueError("Stock cannot be negative")
    with get_connection() as conn:
        row = _ensure_display_row(conn, model_id, display_type)
        before = row["stock"]
        conn.execute(
            "UPDATE display_stock SET stock=?, updated_at=datetime('now') WHERE model_id=? AND display_type=?",
            (new_stock, model_id, display_type),
        )
        conn.execute(
            """INSERT INTO display_transactions
               (model_id, display_type, operation, quantity, stock_before, stock_after, note)
               VALUES (?, ?, 'ADJUST', ?, ?, ?, ?)""",
            (model_id, display_type, abs(new_stock - before), before, new_stock, note),
        )
        return {"before": before, "after": new_stock}


def set_display_inventur(model_id: int, display_type: str, inventur: int):
    with get_connection() as conn:
        _ensure_display_row(conn, model_id, display_type)
        conn.execute(
            """UPDATE display_stock SET inventur=?, updated_at=datetime('now')
               WHERE model_id=? AND display_type=?""",
            (inventur, model_id, display_type),
        )
