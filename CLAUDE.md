# CLAUDE.md — Stock Manager Pro (v2)

> Project guidance for Claude Code. Read this before touching any file.

---

## Project Overview

**Stock Manager Pro** is a cross-platform desktop inventory app built with Python + PyQt6.
It is designed as a **white-label platform** — shops configure their own product categories
(Displays, Batteries, Cases, Cameras, etc.) without touching source code.

**Primary customer:** Phone repair / accessory shops (Galaxy@Phone is reference customer).
**Business model:** Resell to multiple shops, each with their own configuration.

---

## Tech Stack

| Layer      | Technology                |
|------------|---------------------------|
| UI         | PyQt6                     |
| Database   | SQLite 3 (via stdlib)     |
| Packaging  | PyInstaller               |
| Language   | Python 3.11+              |
| Platform   | Windows 10/11 (cross-platform in v2) |

---

## Architecture Principles (MUST follow)

### SOLID
- **S** — Each class has one responsibility. `StockService` does business logic, `StockRepository` does DB queries, `MatrixTab` does UI rendering.
- **O** — New categories (tabs) are added by registering data in DB/config, NOT by modifying existing classes.
- **L** — All tab widgets implement the same `BaseTab` interface, so `MainWindow` can treat them uniformly.
- **I** — Repositories expose only the methods each consumer needs.
- **D** — UI depends on service interfaces, not concrete DB calls.

### DRY
- The `MatrixTab` widget is the single, generic implementation for ALL category tabs (Displays, Batteries, Cases, etc.).
- Translations live only in `i18n.py`. Never hardcode English strings in UI code.
- Stock operations (IN/OUT/ADJUST) share one `StockService` used by all tabs.

### OOP
- Use dataclasses for value objects (`PartTypeConfig`, `StockEntry`, `PhoneModel`).
- Repository classes own all SQL. UI classes never call `sqlite3` directly.
- Signals/slots for all UI communication. No direct method calls across layers.

---

## Project Structure (v2 target)

```
src/
├── files/                    ← working directory (matches PyInstaller bundle)
│   ├── main.py               ← entry point (minimal)
│   ├── app/
│   │   ├── core/
│   │   │   ├── database.py   ← connection + migration + seeding
│   │   │   ├── config.py     ← app & shop settings (JSON)
│   │   │   ├── theme.py      ← design tokens + ThemeManager
│   │   │   ├── i18n.py       ← translations (EN / DE / AR)
│   │   │   └── colors.py     ← color palette
│   │   ├── models/           ← pure data classes (no DB logic)
│   │   │   ├── category.py
│   │   │   ├── part_type.py
│   │   │   ├── phone_model.py
│   │   │   ├── stock_entry.py
│   │   │   ├── product.py
│   │   │   └── transaction.py
│   │   ├── repositories/     ← all SQL lives here
│   │   │   ├── base.py
│   │   │   ├── category_repo.py
│   │   │   ├── model_repo.py
│   │   │   ├── stock_repo.py
│   │   │   ├── product_repo.py
│   │   │   └── transaction_repo.py
│   │   ├── services/         ← business logic
│   │   │   ├── stock_service.py
│   │   │   └── alert_service.py
│   │   └── ui/
│   │       ├── components/   ← reusable widgets
│   │       │   ├── matrix_widget.py   ← THE generic matrix (core of v2)
│   │       │   ├── summary_cards.py
│   │       │   ├── product_detail.py
│   │       │   └── barcode_input.py
│   │       ├── dialogs/
│   │       │   ├── product_dialog.py
│   │       │   ├── stock_op_dialog.py
│   │       │   ├── matrix_op_dialog.py
│   │       │   ├── category_dialog.py
│   │       │   └── alerts_dialog.py
│   │       ├── tabs/
│   │       │   ├── base_tab.py         ← abstract base for all tabs
│   │       │   ├── products_tab.py
│   │       │   ├── transactions_tab.py
│   │       │   └── matrix_tab.py       ← generic, config-driven
│   │       └── main_window.py
│   └── img/
```

---

## Database Schema (v2)

```sql
categories (id, key, name_en, name_de, name_ar, sort_order, icon, is_active)
part_types  (id, category_id, key, name, accent_color, sort_order)
phone_models (id, brand, name, sort_order)
stock_entries (id, model_id, part_type_id, stamm_zahl, stock, inventur, updated_at)
stock_transactions (id, entry_id, operation, qty, stock_before, stock_after, note, timestamp)
products (id, brand, type, color, stock, barcode, low_stock_threshold, ...)
product_transactions (id, product_id, operation, qty, stock_before, stock_after, note, timestamp)
app_config (key TEXT PRIMARY KEY, value TEXT)
```

---

## Coding Conventions

- **Type hints** on all function signatures.
- **Dataclasses** for all model objects (`@dataclass`).
- **No raw SQL in UI code** — always call a repository or service.
- **No hardcoded strings in UI** — always use `t("key")`.
- **Signal names**: `snake_case_verb_noun` e.g. `stock_updated`, `model_selected`.
- **File names**: `snake_case.py`.
- **Class names**: `PascalCase`.
- **Constants**: `UPPER_SNAKE_CASE`.
- Keep functions under 40 lines. Extract helpers aggressively.
- One class per file (except small dataclasses grouped in `models/`).

---

## Key Design Decisions

### Sidebar Navigation (v2.1)
Professional sidebar replaces the old tab widget:
- Fixed 200px sidebar with logo, shop name, nav buttons
- QStackedWidget for page switching (no QTabWidget)
- Pages: Inventory, Transactions, Stock Ops, Quick Scan, + dynamic category pages
- Dark/light theme toggle (custom painted ThemeToggle widget) in sidebar bottom
- Language switcher + Admin button in sidebar bottom
- Alert badge in sidebar

### Summary Cards — Inventory Only
Summary cards (Total Products, Units, Low Stock, Out of Stock, Value) are shown
only on the Inventory page, not globally.

### The Generic Matrix Tab
`MatrixTab` takes a `CategoryConfig` and renders:
- Rows = phone models (filterable by brand)
- Column groups = part types (each with Stamm-Zahl | Best-Bung | Stock | Order)
- Double-click any cell → context-appropriate dialog
- **Excel-like color banding**: model name column has distinct background,
  each part type group gets a subtle tint from its accent color
- Brand filter, Add Model button, color-coded Best-Bung

### Order Field (was Inventur)
The 4th column in each part type group is now "Order" instead of "Inventur".
The shop owner enters the amount they ordered. When delivery arrives, they
check against this number, then clear it after verification.

### Quick Scan Mode
Fast barcode scanning for high-pressure shop environments:
- Dedicated page with large barcode input field
- Each scan instantly takes 1 unit out of stock
- Live feed shows scan results (success/error/warning)
- For parts without barcodes (displays, etc.), shop can print custom barcodes

### Stock Operations Tab
Professional IN/OUT/ADJUST page with:
- Searchable product list with barcode scanning
- Quantity spinner + optional note
- Recent transaction history for selected item

### Configuration-Driven Categories
Categories are driven by data in the `categories` and `part_types` tables.
To add "Batteries": insert 1 row in `categories` + rows in `part_types`.
No code changes required. Sidebar nav auto-updates.

### Backward Compatibility
v1 database must be auto-migrated. Never drop columns; only ADD.
`init_db()` checks schema version and applies incremental migrations.

---

## Build & Run

```bash
# From repo root
cd src/files
python main.py

# Build exe
cd src
pyinstaller StockManagerPro.spec --noconfirm
```

---

## Git Workflow

- `main` = stable releases only
- `dev` = active development (current branch)
- Feature branches: `feat/matrix-engine`, `feat/batteries-tab`, etc.
- Commit messages: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`

---

## UX Philosophy

> Customers should **feel** the product, not just use it.

- Every action has immediate visual feedback.
- Color is semantic: green = OK, yellow = at minimum, red = critical, orange = low.
- Dark mode is the primary mode (phone shop lighting is often dim).
- Animations/transitions on tab switch and data load (subtle, not flashy).
- No modal dialogs for read-only info — use the detail panel.
- Every number that matters is big and readable at a glance.
