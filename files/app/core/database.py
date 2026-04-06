"""
app/core/database.py — Connection, schema init, and seed data.

Schema versioning via app_config table.
V1 → V2 migration handled automatically.
"""
from __future__ import annotations

import os
import sys
import sqlite3
from typing import Optional
from app.core.logger import get_logger

_log = get_logger(__name__)


# ── DB path resolution ────────────────────────────────────────────────────────

def _db_path() -> str:
    if getattr(sys, "frozen", False):
        # PyInstaller bundle — use user's AppData (Windows) / equivalent
        try:
            from platformdirs import user_data_dir
            base = user_data_dir("StockManagerPro", "StockPro")
        except ImportError:
            base = os.path.join(
                os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                "StockPro", "StockManagerPro",
            )
        os.makedirs(base, exist_ok=True)
        db_path = os.path.join(base, "stock_manager.db")
        _log.info(f"DB path (production): {db_path}")
        return db_path
    # Development: DB next to source files (two levels up from app/core/)
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_path = os.path.join(root, "stock_manager.db")
    _log.debug(f"DB path (development): {db_path}")
    return db_path


DB_PATH: str = _db_path()


# ── Connection ────────────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


# ── Schema DDL ────────────────────────────────────────────────────────────────

_DDL = """
    -- Version tracking
    CREATE TABLE IF NOT EXISTS app_config (
        key   TEXT PRIMARY KEY,
        value TEXT
    );

    -- Inventory categories (tabs)
    CREATE TABLE IF NOT EXISTS categories (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        key        TEXT NOT NULL UNIQUE,
        name_en    TEXT NOT NULL,
        name_de    TEXT NOT NULL DEFAULT '',
        name_ar    TEXT NOT NULL DEFAULT '',
        sort_order INTEGER NOT NULL DEFAULT 0,
        icon       TEXT NOT NULL DEFAULT '',
        is_active  INTEGER NOT NULL DEFAULT 1
    );

    -- Part types within a category (column groups in the matrix)
    CREATE TABLE IF NOT EXISTS part_types (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id  INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
        key          TEXT NOT NULL,
        name         TEXT NOT NULL,
        accent_color TEXT NOT NULL DEFAULT '#4A9EFF',
        sort_order   INTEGER NOT NULL DEFAULT 0,
        UNIQUE(category_id, key)
    );

    -- Colors available for a part type (e.g., ORG Service Pack → Black, Blue, Silver)
    CREATE TABLE IF NOT EXISTS part_type_colors (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        part_type_id INTEGER NOT NULL REFERENCES part_types(id) ON DELETE CASCADE,
        color_name   TEXT NOT NULL,
        color_code   TEXT NOT NULL DEFAULT '',
        sort_order   INTEGER NOT NULL DEFAULT 0,
        UNIQUE(part_type_id, color_name)
    );

    -- Phone models (shared across all categories)
    CREATE TABLE IF NOT EXISTS phone_models (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        brand      TEXT NOT NULL,
        name       TEXT NOT NULL UNIQUE,
        sort_order INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- LEGACY: Generic stock entries (kept for migration in V3→V4, dropped in V6)
    CREATE TABLE IF NOT EXISTS stock_entries (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        model_id     INTEGER NOT NULL REFERENCES phone_models(id) ON DELETE CASCADE,
        part_type_id INTEGER NOT NULL REFERENCES part_types(id)   ON DELETE CASCADE,
        stamm_zahl   INTEGER NOT NULL DEFAULT 0,
        stock        INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
        inventur     INTEGER,
        updated_at   TEXT    NOT NULL DEFAULT (datetime('now')),
        UNIQUE(model_id, part_type_id)
    );

    -- LEGACY: Audit log for matrix stock movements (kept for migration in V3→V4, dropped in V6)
    CREATE TABLE IF NOT EXISTS stock_transactions (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_id     INTEGER NOT NULL REFERENCES stock_entries(id) ON DELETE CASCADE,
        operation    TEXT    NOT NULL CHECK(operation IN ('IN','OUT','ADJUST')),
        quantity     INTEGER NOT NULL,
        stock_before INTEGER NOT NULL,
        stock_after  INTEGER NOT NULL,
        note         TEXT,
        timestamp    TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- LEGACY: General products (kept for migration in V3→V4, dropped in V6)
    CREATE TABLE IF NOT EXISTS products (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        brand               TEXT    NOT NULL,
        type                TEXT    NOT NULL,
        color               TEXT    NOT NULL,
        stock               INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
        barcode             TEXT    UNIQUE,
        low_stock_threshold INTEGER NOT NULL DEFAULT 5,
        created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
        updated_at          TEXT    NOT NULL DEFAULT (datetime('now'))
    );

    -- LEGACY: Audit log for product stock movements (kept for migration in V3→V4, dropped in V6)
    CREATE TABLE IF NOT EXISTS product_transactions (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id   INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
        operation    TEXT    NOT NULL CHECK(operation IN ('IN','OUT','ADJUST','CREATE')),
        quantity     INTEGER NOT NULL,
        stock_before INTEGER NOT NULL,
        stock_after  INTEGER NOT NULL,
        note         TEXT,
        timestamp    TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- Unified inventory (replaces products + stock_entries in V4)
    -- color is part of unique key: model × part_type × color
    CREATE TABLE IF NOT EXISTS inventory_items (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        brand        TEXT    NOT NULL DEFAULT '',
        name         TEXT    NOT NULL DEFAULT '',
        color        TEXT    NOT NULL DEFAULT '',
        sku          TEXT,
        barcode      TEXT    UNIQUE,
        sell_price   REAL,
        stock        INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
        min_stock    INTEGER NOT NULL DEFAULT 0,
        inventur     INTEGER,
        model_id     INTEGER REFERENCES phone_models(id) ON DELETE CASCADE,
        part_type_id INTEGER REFERENCES part_types(id)   ON DELETE CASCADE,
        is_active    INTEGER NOT NULL DEFAULT 1,
        created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
        updated_at   TEXT    NOT NULL DEFAULT (datetime('now')),
        UNIQUE(model_id, part_type_id, color)
    );

    -- Unified audit log (replaces product_transactions + stock_transactions in V4)
    CREATE TABLE IF NOT EXISTS inventory_transactions (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id      INTEGER NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
        operation    TEXT    NOT NULL CHECK(operation IN ('IN','OUT','ADJUST','CREATE')),
        quantity     INTEGER NOT NULL,
        stock_before INTEGER NOT NULL,
        stock_after  INTEGER NOT NULL,
        note         TEXT,
        timestamp    TEXT    NOT NULL DEFAULT (datetime('now'))
    );

    -- Indexes
    CREATE INDEX IF NOT EXISTS idx_products_barcode       ON products(barcode);
    CREATE INDEX IF NOT EXISTS idx_product_txn_product    ON product_transactions(product_id);
    CREATE INDEX IF NOT EXISTS idx_product_txn_time       ON product_transactions(timestamp);
    CREATE INDEX IF NOT EXISTS idx_stock_entries_model    ON stock_entries(model_id);
    CREATE INDEX IF NOT EXISTS idx_stock_entries_part     ON stock_entries(part_type_id);
    CREATE INDEX IF NOT EXISTS idx_stock_txn_entry        ON stock_transactions(entry_id);
    CREATE INDEX IF NOT EXISTS idx_part_types_category    ON part_types(category_id);
    CREATE INDEX IF NOT EXISTS idx_inv_items_model        ON inventory_items(model_id);
    CREATE INDEX IF NOT EXISTS idx_inv_items_barcode      ON inventory_items(barcode);
    CREATE INDEX IF NOT EXISTS idx_inv_txn_item           ON inventory_transactions(item_id);
    CREATE INDEX IF NOT EXISTS idx_inv_txn_time           ON inventory_transactions(timestamp);
"""

_SCHEMA_VERSION = "6"


# ── V2 → V3 migration ────────────────────────────────────────────────────────

def _migrate_v2_to_v3(conn: sqlite3.Connection) -> None:
    """V3 adds new ShopConfig keys and setup_complete flag. No new tables."""
    _log.info("Migrating database schema from V2 to V3")
    defaults = {
        "currency_position": "prefix",
        "logo_path":         "",
        "admin_pin":         "",
        "contact_info":      "",
        "setup_complete":    "1",   # existing installs skip the setup wizard
    }
    for k, v in defaults.items():
        conn.execute(
            "INSERT OR IGNORE INTO app_config (key, value) VALUES (?,?)", (k, v)
        )
    _log.info("V2 to V3 migration completed")


# ── V3 → V4 migration ────────────────────────────────────────────────────────

def _migrate_v5_to_v6(conn: sqlite3.Connection) -> None:
    """Add part_type_colors table and change inventory_items unique constraint to include color."""
    # Create part_type_colors table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS part_type_colors (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            part_type_id INTEGER NOT NULL REFERENCES part_types(id) ON DELETE CASCADE,
            color_name   TEXT NOT NULL,
            color_code   TEXT NOT NULL DEFAULT '',
            sort_order   INTEGER NOT NULL DEFAULT 0,
            UNIQUE(part_type_id, color_name)
        )
    """)

    # Recreate inventory_items with UNIQUE(model_id, part_type_id, color) instead of UNIQUE(model_id, part_type_id)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory_items_new (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            brand        TEXT    NOT NULL DEFAULT '',
            name         TEXT    NOT NULL DEFAULT '',
            color        TEXT    NOT NULL DEFAULT '',
            sku          TEXT,
            barcode      TEXT    UNIQUE,
            sell_price   REAL,
            stock        INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
            min_stock    INTEGER NOT NULL DEFAULT 0,
            inventur     INTEGER,
            model_id     INTEGER REFERENCES phone_models(id) ON DELETE CASCADE,
            part_type_id INTEGER REFERENCES part_types(id)   ON DELETE CASCADE,
            is_active    INTEGER NOT NULL DEFAULT 1,
            created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at   TEXT    NOT NULL DEFAULT (datetime('now')),
            UNIQUE(model_id, part_type_id, color)
        )
    """)
    conn.execute("""
        INSERT OR IGNORE INTO inventory_items_new
            (id, brand, name, color, sku, barcode, sell_price, stock, min_stock,
             inventur, model_id, part_type_id, is_active, created_at, updated_at)
        SELECT id, brand, name, color, sku, barcode, sell_price, stock, min_stock,
               inventur, model_id, part_type_id, is_active, created_at, updated_at
        FROM inventory_items
    """)
    conn.execute("DROP TABLE inventory_items")
    conn.execute("ALTER TABLE inventory_items_new RENAME TO inventory_items")
    # Recreate indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_inv_items_model ON inventory_items(model_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_inv_items_barcode ON inventory_items(barcode)")


def _migrate_v4_to_v5(conn: sqlite3.Connection) -> None:
    """Seed default command barcodes for Quick Scan."""
    _log.info("Migrating database schema from V4 to V5")
    defaults = [
        ("scan_cmd_takeout", "CMD-TAKEOUT"),
        ("scan_cmd_insert",  "CMD-INSERT"),
        ("scan_cmd_confirm", "CMD-CONFIRM"),
    ]
    for key, val in defaults:
        conn.execute(
            "INSERT OR IGNORE INTO app_config (key, value) VALUES (?,?)",
            (key, val),
        )
    _log.info("V4 to V5 migration completed")


def _migrate_v5_to_v6(conn: sqlite3.Connection) -> None:
    """V6: Drop legacy tables now that data is fully in inventory_items."""
    _log.info("Migrating database schema from V5 to V6 (drop legacy tables)")

    # Safety: verify inventory_items has data before dropping
    count = conn.execute("SELECT COUNT(*) FROM inventory_items").fetchone()[0]
    if count == 0:
        # Don't drop if unified table is empty — data might not be migrated
        _log.warning("V5 to V6: Skipping legacy table drop — inventory_items is empty")
        return

    # Drop legacy tables that are no longer used
    conn.execute("DROP TABLE IF EXISTS product_transactions")
    conn.execute("DROP TABLE IF EXISTS stock_transactions")
    conn.execute("DROP TABLE IF EXISTS products")
    conn.execute("DROP TABLE IF EXISTS stock_entries")

    # Drop legacy indexes
    conn.execute("DROP INDEX IF EXISTS idx_products_barcode")
    conn.execute("DROP INDEX IF EXISTS idx_product_txn_product")
    conn.execute("DROP INDEX IF EXISTS idx_product_txn_time")
    conn.execute("DROP INDEX IF EXISTS idx_stock_entries_model")
    conn.execute("DROP INDEX IF EXISTS idx_stock_entries_part")
    conn.execute("DROP INDEX IF EXISTS idx_stock_txn_entry")

    _log.info("V5 to V6 migration completed")


def _migrate_v3_to_v4(conn: sqlite3.Connection) -> None:
    """Consolidate products + stock_entries into inventory_items."""
    _log.info("Migrating database schema from V3 to V4 (consolidate products + stock_entries)")
    # 1. Products → inventory_items (preserve IDs so product_id refs stay valid)
    conn.execute("""
        INSERT OR IGNORE INTO inventory_items
            (id, brand, name, color, barcode, stock, min_stock, created_at, updated_at)
        SELECT id, brand, type, color, barcode, stock, low_stock_threshold,
               created_at, updated_at
        FROM products
    """)
    _log.debug("V3->V4: Migrated products to inventory_items")

    # 2. stock_entries → inventory_items (new IDs, build a mapping for transaction migration)
    conn.execute("CREATE TEMP TABLE _se_map (old_id INTEGER, new_id INTEGER)")
    entries = conn.execute("SELECT * FROM stock_entries").fetchall()
    for e in entries:
        conn.execute("""
            INSERT OR IGNORE INTO inventory_items
                (model_id, part_type_id, stock, min_stock, inventur, updated_at)
            VALUES (?,?,?,?,?,?)
        """, (e["model_id"], e["part_type_id"], e["stock"],
              e["stamm_zahl"], e["inventur"], e["updated_at"]))
        row = conn.execute(
            "SELECT id FROM inventory_items WHERE model_id=? AND part_type_id=?",
            (e["model_id"], e["part_type_id"]),
        ).fetchone()
        if row:
            conn.execute("INSERT INTO _se_map VALUES (?,?)", (e["id"], row["id"]))

    # 3. product_transactions → inventory_transactions
    conn.execute("""
        INSERT OR IGNORE INTO inventory_transactions
            (item_id, operation, quantity, stock_before, stock_after, note, timestamp)
        SELECT product_id, operation, quantity, stock_before, stock_after, note, timestamp
        FROM product_transactions
    """)

    # 4. stock_transactions → inventory_transactions (remap entry_id via mapping table)
    txns = conn.execute("SELECT * FROM stock_transactions").fetchall()
    for tx in txns:
        mapping = conn.execute(
            "SELECT new_id FROM _se_map WHERE old_id=?", (tx["entry_id"],)
        ).fetchone()
        if mapping:
            conn.execute("""
                INSERT INTO inventory_transactions
                    (item_id, operation, quantity, stock_before, stock_after, note, timestamp)
                VALUES (?,?,?,?,?,?,?)
            """, (mapping["new_id"], tx["operation"], tx["quantity"],
                  tx["stock_before"], tx["stock_after"], tx["note"], tx["timestamp"]))

    conn.execute("DROP TABLE _se_map")
    _log.info("V3 to V4 migration completed")


# ── V1 → V2 migration helpers ─────────────────────────────────────────────────

def _has_table(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return bool(row and row[0])


def _migrate_v1_display_stock(conn: sqlite3.Connection) -> None:
    """Copy v1 display_stock rows into the new stock_entries table."""
    if not _has_table(conn, "display_stock"):
        return

    # Build display_type_key → part_type_id mapping
    pt_rows = conn.execute(
        "SELECT pt.id, pt.key FROM part_types pt "
        "JOIN categories c ON c.id = pt.category_id WHERE c.key = 'displays'"
    ).fetchall()
    key_to_pt_id = {r["key"]: r["id"] for r in pt_rows}

    # Build old model name → new model id mapping
    old_models = conn.execute("SELECT id, name FROM phone_models").fetchall()
    name_to_id = {r["name"]: r["id"] for r in old_models}

    rows = conn.execute(
        "SELECT model_id, display_type, stamm_zahl, stock, inventur FROM display_stock"
    ).fetchall()

    for row in rows:
        model_id   = row["model_id"]
        pt_id      = key_to_pt_id.get(row["display_type"])
        if pt_id is None:
            continue
        conn.execute(
            """INSERT OR IGNORE INTO stock_entries
               (model_id, part_type_id, stamm_zahl, stock, inventur)
               VALUES (?, ?, ?, ?, ?)""",
            (model_id, pt_id, row["stamm_zahl"], row["stock"], row["inventur"]),
        )


def _migrate_v1_transactions(conn: sqlite3.Connection) -> None:
    """Copy v1 transactions table into product_transactions."""
    if not _has_table(conn, "transactions"):
        return
    if not _has_table(conn, "product_transactions"):
        return
    existing = conn.execute("SELECT COUNT(*) FROM product_transactions").fetchone()[0]
    if existing > 0:
        return  # already migrated
    conn.execute("""
        INSERT OR IGNORE INTO product_transactions
            (id, product_id, operation, quantity, stock_before, stock_after, note, timestamp)
        SELECT id, product_id, operation, quantity, stock_before, stock_after, note, timestamp
        FROM transactions
    """)


# ── Public init ───────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create schema, run migrations, seed reference data."""
    _log.info("Initializing database")
    with get_connection() as conn:
        conn.executescript(_DDL)

        # Detect schema version
        version = conn.execute(
            "SELECT value FROM app_config WHERE key='schema_version'"
        ).fetchone()
        is_fresh = version is None

        if is_fresh:
            _log.info("Database is fresh, initializing new schema")
            # Check if this is a v1 upgrade or truly fresh
            is_v1_upgrade = _has_table(conn, "display_stock")

            if is_v1_upgrade:
                # V1 upgrade: migrate existing data into v2 schema
                from app.core.demo_data import (
                    DEMO_CATEGORIES, DEMO_PART_TYPES,
                )
                # Seed categories and part types (needed for migration mapping)
                conn.executemany(
                    """INSERT OR IGNORE INTO categories
                       (key, name_en, name_de, name_ar, sort_order, icon)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    DEMO_CATEGORIES,
                )
                cat_rows = conn.execute("SELECT id, key FROM categories").fetchall()
                cat_key_to_id = {r["key"]: r["id"] for r in cat_rows}
                for cat_key, parts in DEMO_PART_TYPES.items():
                    cat_id = cat_key_to_id.get(cat_key)
                    if cat_id is None:
                        continue
                    conn.executemany(
                        """INSERT OR IGNORE INTO part_types
                           (category_id, key, name, accent_color, sort_order)
                           VALUES (?, ?, ?, ?, ?)""",
                        [(cat_id, k, n, c, s) for k, n, c, s in parts],
                    )
                # Migrate existing phone_models brand column if needed
                cols = {r[1] for r in conn.execute("PRAGMA table_info(phone_models)").fetchall()}
                if "brand" not in cols:
                    conn.execute(
                        "ALTER TABLE phone_models ADD COLUMN brand TEXT NOT NULL DEFAULT 'Apple'"
                    )
                _migrate_v1_display_stock(conn)
                _migrate_v1_transactions(conn)
                # Mark setup as complete for V1 upgrades
                conn.execute(
                    "INSERT OR IGNORE INTO app_config (key, value) VALUES ('setup_complete', '1')"
                )
            # Fresh installs: no seed data — setup wizard will handle it

            conn.execute(
                "INSERT OR REPLACE INTO app_config (key, value) VALUES ('schema_version', ?)",
                (_SCHEMA_VERSION,),
            )

        # Incremental migrations for existing installs
        if not is_fresh:
            ver_row = conn.execute(
                "SELECT value FROM app_config WHERE key='schema_version'"
            ).fetchone()
            current = ver_row["value"] if ver_row else "1"
            _log.info(f"Current schema version: {current}, target: {_SCHEMA_VERSION}")

            if current == "2":
                _migrate_v2_to_v3(conn)
                current = "3"

            if current == "3":
                _migrate_v3_to_v4(conn)
                current = "4"

            if current == "4":
                _migrate_v4_to_v5(conn)
                current = "5"

            if current == "5":
                _migrate_v5_to_v6(conn)
                current = "6"

            if current != _SCHEMA_VERSION:
                _log.info(f"Updating schema version to {_SCHEMA_VERSION}")
                conn.execute(
                    "INSERT OR REPLACE INTO app_config (key, value) VALUES ('schema_version', ?)",
                    (_SCHEMA_VERSION,),
                )

        # Ensure all (model × part_type) entries exist so matrix is fully populated
        _ensure_all_entries(conn)
        _log.info("Database initialization complete")


def load_demo_data() -> None:
    """
    Seed the Galaxy@Phone demo data.
    Safe to call multiple times — uses INSERT OR IGNORE.
    Display part types are brand-specific (Apple has 5 types, Samsung has 2).
    """
    from app.core.demo_data import (
        DEMO_CATEGORIES, DEMO_PART_TYPES, DEMO_PHONE_MODELS, DISPLAY_BRAND_MAP,
        DEMO_PART_TYPE_COLORS,
    )
    with get_connection() as conn:
        conn.executemany(
            """INSERT OR IGNORE INTO categories
               (key, name_en, name_de, name_ar, sort_order, icon)
               VALUES (?,?,?,?,?,?)""",
            DEMO_CATEGORIES,
        )
        cat_rows = conn.execute("SELECT id, key FROM categories").fetchall()
        cat_key_to_id = {r["key"]: r["id"] for r in cat_rows}
        for cat_key, parts in DEMO_PART_TYPES.items():
            cat_id = cat_key_to_id.get(cat_key)
            if cat_id is None:
                continue
            conn.executemany(
                """INSERT OR IGNORE INTO part_types
                   (category_id, key, name, accent_color, sort_order)
                   VALUES (?,?,?,?,?)""",
                [(cat_id, k, n, c, s) for k, n, c, s in parts],
            )
        conn.executemany(
            "INSERT OR IGNORE INTO phone_models (brand, name, sort_order) VALUES (?,?,?)",
            DEMO_PHONE_MODELS,
        )

        # Seed part type colors
        pt_rows_all = conn.execute("SELECT id, key FROM part_types").fetchall()
        pt_key_to_id_all = {r["key"]: r["id"] for r in pt_rows_all}
        for pt_key, colors in DEMO_PART_TYPE_COLORS.items():
            pt_id = pt_key_to_id_all.get(pt_key)
            if pt_id:
                for color_name, color_code, sort_order in colors:
                    conn.execute(
                        "INSERT OR IGNORE INTO part_type_colors (part_type_id, color_name, color_code, sort_order) VALUES (?,?,?,?)",
                        (pt_id, color_name, color_code, sort_order),
                    )

        # Brand-aware matrix entries for displays
        # Delete wrong brand × display combos (e.g., Samsung + JK incell)
        displays_cat_id = cat_key_to_id.get("displays")
        if displays_cat_id:
            # Get all display part types with their keys
            pt_rows = conn.execute(
                "SELECT id, key FROM part_types WHERE category_id=?",
                (displays_cat_id,),
            ).fetchall()
            pt_key_to_id = {r["key"]: r["id"] for r in pt_rows}

            # Get all models with their brands
            models = conn.execute("SELECT id, brand FROM phone_models").fetchall()

            # Clean up: delete display entries where brand doesn't match
            for model in models:
                brand = model["brand"]
                allowed_keys = DISPLAY_BRAND_MAP.get(brand, [])
                disallowed_pt_ids = [pt_key_to_id[k] for k in pt_key_to_id if k not in allowed_keys]
                if disallowed_pt_ids:
                    placeholders = ",".join("?" * len(disallowed_pt_ids))
                    # Only delete if stock is 0 (don't lose actual data)
                    conn.execute(
                        f"DELETE FROM inventory_items WHERE model_id=? AND part_type_id IN ({placeholders}) "
                        f"AND (stock IS NULL OR stock = 0) AND (min_stock IS NULL OR min_stock = 0)",
                        [model["id"]] + disallowed_pt_ids,
                    )

            # Create display entries only for matching brands
            for model in models:
                brand = model["brand"]
                allowed_keys = DISPLAY_BRAND_MAP.get(brand, [])
                for pt_key in allowed_keys:
                    pt_id = pt_key_to_id.get(pt_key)
                    if pt_id:
                        conn.execute(
                            "INSERT OR IGNORE INTO inventory_items (model_id, part_type_id) VALUES (?,?)",
                            (model["id"], pt_id),
                        )

            # For non-display categories, create all model × part_type entries
            non_display_pts = conn.execute(
                "SELECT id FROM part_types WHERE category_id != ?",
                (displays_cat_id,),
            ).fetchall()
            for model in models:
                for pt in non_display_pts:
                    conn.execute(
                        "INSERT OR IGNORE INTO inventory_items (model_id, part_type_id) VALUES (?,?)",
                        (model["id"], pt["id"]),
                    )
        else:
            # No displays category — use default ensure_all
            _ensure_all_entries(conn)


def _ensure_all_entries(conn: sqlite3.Connection) -> None:
    """Insert missing inventory_items rows, respecting brand-specific display rules."""
    try:
        from app.core.demo_data import DISPLAY_BRAND_MAP, DISPLAY_EXCLUSIONS
    except ImportError:
        DISPLAY_BRAND_MAP = {}
        DISPLAY_EXCLUSIONS = {}

    models = conn.execute("SELECT id, brand, name FROM phone_models").fetchall()

    # Find the displays category
    displays_row = conn.execute(
        "SELECT id FROM categories WHERE key='displays'"
    ).fetchone()
    displays_cat_id = displays_row["id"] if displays_row else None

    # Build display part type key→id map
    display_pt_map: dict[str, int] = {}
    display_pt_ids: set[int] = set()
    if displays_cat_id:
        for r in conn.execute(
            "SELECT id, key FROM part_types WHERE category_id=?",
            (displays_cat_id,),
        ).fetchall():
            display_pt_map[r["key"]] = r["id"]
            display_pt_ids.add(r["id"])

    # Load colors per part type from part_type_colors table
    pt_colors: dict[int, list[str]] = {}  # pt_id → [color_name, ...]
    try:
        for r in conn.execute("SELECT part_type_id, color_name FROM part_type_colors ORDER BY sort_order").fetchall():
            pt_colors.setdefault(r["part_type_id"], []).append(r["color_name"])
    except Exception:
        pass  # table might not exist yet during initial schema creation

    def _insert_item(mid: int, pt_id: int):
        """Insert inventory items — colored rows for stock + colorless parent for barcode."""
        colors = pt_colors.get(pt_id, [])
        if colors:
            # Create colored rows (for individual stock tracking)
            for color in colors:
                conn.execute(
                    "INSERT OR IGNORE INTO inventory_items (model_id, part_type_id, color) VALUES (?,?,?)",
                    (mid, pt_id, color),
                )
            # Also create colorless parent row (this gets the barcode for scanning)
            conn.execute(
                "INSERT OR IGNORE INTO inventory_items (model_id, part_type_id, color) VALUES (?,?,'')",
                (mid, pt_id),
            )
        else:
            conn.execute(
                "INSERT OR IGNORE INTO inventory_items (model_id, part_type_id, color) VALUES (?,?,'')",
                (mid, pt_id),
            )

    # All non-display part types
    all_pts = conn.execute("SELECT id FROM part_types").fetchall()
    non_display_pt_ids = [r["id"] for r in all_pts if r["id"] not in display_pt_ids]

    for model in models:
        brand = model["brand"]
        model_name = model["name"]
        mid = model["id"]

        # Non-display part types: create for ALL models
        for pt_id in non_display_pt_ids:
            _insert_item(mid, pt_id)

        # Display part types: brand-aware + model-specific exclusions
        if DISPLAY_BRAND_MAP and display_pt_map:
            allowed_keys = DISPLAY_BRAND_MAP.get(brand)
            if allowed_keys is not None:
                for key in allowed_keys:
                    excluded_models = DISPLAY_EXCLUSIONS.get(key, [])
                    if model_name in excluded_models:
                        pt_id = display_pt_map.get(key)
                        if pt_id:
                            conn.execute(
                                "DELETE FROM inventory_items WHERE model_id=? AND part_type_id=? "
                                "AND (stock IS NULL OR stock=0) AND (min_stock IS NULL OR min_stock=0)",
                                (mid, pt_id),
                            )
                        continue
                    pt_id = display_pt_map.get(key)
                    if pt_id:
                        _insert_item(mid, pt_id)
            else:
                for pt_id in display_pt_ids:
                    _insert_item(mid, pt_id)
        else:
            for pt_id in display_pt_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO inventory_items (model_id, part_type_id, color) VALUES (?,?,'')",
                    (mid, pt_id),
                )


def ensure_matrix_entries() -> None:
    """Public helper — call after adding new models or part types via admin UI."""
    with get_connection() as conn:
        _ensure_all_entries(conn)
