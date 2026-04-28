# Changelog

All notable changes to **Stock Manager Pro** are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

## [2.4.7] - 2026-04-28


## [2.4.7] - 2026-04-28

### Fixed
- **YunPrint export format — switched from `.xlsx` to RFC-4180 CSV (`.txt`)** so YunPrint's Database dialog actually parses the file. The 2.4.5 implementation wrote an openpyxl `.xlsx` and instructed the user to import via Excel mode; live testing on the K30F revealed YunPrint's Excel parser silently rejects openpyxl-generated workbooks (Sample-data preview empty, field-binding dropdown empty), and the tab-delimited fallback was read as a single oversized column because YunPrint's `.txt` mode defaults to `Character Segmentation: Comma` and doesn't auto-detect tabs. Final format is comma-separated, UTF-8-BOM, written via Python's `csv.writer` with `QUOTE_MINIMAL` — YunPrint parses out the six columns (`barcode`, `model`, `part_type`, `model_full`, `brand`, `label`) cleanly and the user can bind each template field to a single column from the dropdown.
  - File extension stays `.txt` (matches the YunPrint Database mode that actually works on the K30F + Dlabel driver combo).
  - The how-to dialog shown after export now reflects the `.txt` Database mode flow rather than the broken Excel mode flow.
  - `openpyxl` import is removed from `BarcodeGenService.export_for_yunprint`. The dep stays in `requirements.txt` because `export_service.py` and `import_service.py` still use it for general Excel I/O.

## [2.4.6] - 2026-04-28

### Fixed
- **Part Type Settings — Models & Colors table now shows every brand, not just one.** Previously, when selecting a part type (especially a brand-new one with no inventory yet), the table only displayed models from a single auto-detected brand: the brand with the most existing items, or — for a fresh part type — the brand that came first alphabetically. Every other brand was invisible, so users couldn't tick/untick across the full catalogue without dropping to the database.
  - Default scope is now **All brands**, with brand-header rows separating each brand's models in the table.
  - New **Brand:** dropdown (All brands · Apple · Samsung · …) at the top of the Models & Colors card lets the user narrow the scope when a single brand has too many models. Selection is preserved across part-type changes within the same session.
  - Brand-header rows use the existing `model_id == -1` placeholder convention, so the include/exclude checkbox handler and double-click color-edit handler skip them automatically — no risk of accidentally toggling/editing a header.
  - The auto-detect-by-most-items logic that picked a single brand has been removed entirely; the user is in control via the dropdown.

## [2.4.5] - 2026-04-27

### Added
- **Export for YunPrint (K30F label printer support)** — new "Export for YunPrint" button on the Barcode Generator page. Generates an `.xlsx` workbook one-row-per-barcode that YunPrint/Dlabel can import via its **Database** dialog (Excel mode, "first line contains the field name"). Once a 50×20mm template is designed once with template fields bound to `Database`, every future batch is: Generate → Export for YunPrint → in YunPrint click Database → pick the file → Print all. One print job for the whole batch — no per-label clicking.
  - **Same Code39 strings** already saved on items go straight into the `barcode` column, so labels printed by the K30F scan identically to the existing app barcodes — no regeneration, no migration.
  - Columns exported: `barcode`, `model` (compact brand-prefixed form like "IP 11 Pro Max" / "SA S25 Ultra"), `part_type`, `model_full` (full original "iPhone 11 Pro Max"), `brand`, `label`. The user picks whichever fits their template.
  - Brand short codes (`IP`/`SA`/`XI`/`HW`/...) live in `_BRAND_SHORT` in `barcode_gen_service.py` with a 2-letter fallback for unknown brands.
  - Skips command/color scanner barcodes — those are scanner-only and don't belong on per-item stickers.
  - After save, opens the containing folder in Explorer and shows a one-shot how-to dialog so the user knows the YunPrint import flow without leaving the app.
  - Reuses the existing scope selector on the Barcode Generator page (All / Category / Model / Part Type) — same scope produces the YunPrint xlsx and the legacy A4 PDF.

### Changed
- **`requirements.txt`** — declares `openpyxl==3.1.5` explicitly. The dep was already imported by `export_service.py` and `import_service.py` but had been missing from the requirements file, so fresh venvs / PyInstaller builds were missing it. The new YunPrint export uses it too. No runtime change for environments where it was already installed transitively.

## [2.4.4] - 2026-04-27

### Fixed
- **Part Type Settings — unchecking a model now removes it from the matrix instead of leaving a "disabled" empty row.** Previously, unchecking a model in Admin → Part Types only set an `__EXCLUDED__` marker in `model_part_type_colors` and pruned zero-stock inventory rows; rows with stock/min_stock/inventur stayed in the DB and continued to render in the matrix as "—" cells, producing a confusing half-removed look.
  - `ItemRepository.get_matrix_items` now joins against `model_part_type_colors` with a `NOT EXISTS` filter, so any (model, part_type) combo carrying the `__EXCLUDED__` marker is dropped from the result regardless of stock state. Existing data is preserved — re-checking the model in Part Type Settings restores the rows exactly as before.
  - `MatrixTab._apply_refresh`, `_add_brand_section`, and `_reload_brand_container` now filter the `models` list to only those that have at least one item left in `item_map`. A model that has been excluded from every part type its brand previously had inventory in vanishes from the matrix entirely instead of rendering as an empty row.

## [2.4.2] - 2026-04-21


## [2.4.2] - 2026-04-21

### Added
- **Shop setting: "Show sell totals in matrix"** — new checkbox in Admin → Shop Settings (Regional card, under UI Scale). When off, the matrix TOTAL column and the value portion of the per-part-type cards + the grand-total card are hidden, so shop assistants see stock counts without seeing sell valuation. Units stay visible either way. Cost mode (PIN-gated via 👁) overrides the hide so the cost/sell comparison still makes sense when the owner has authenticated.
  - Persisted via `ShopConfig.show_sell_totals` (reuses the existing `app_config` key-value mechanism — no DB migration needed).
  - Typed accessor `ShopConfig.is_show_sell_totals`.
  - Default is ON — existing users see zero change until they toggle it off.
  - Live-update on Save: the existing settings-close rebuild chain (`ShopConfig.invalidate()` → `rebuild_matrix_tabs()` fast path → `tab.refresh()`) propagates the new state to every matrix tab instantly.

### Fixed
- **Float-precision display bug** — `7 × 22.99` was rendering as `€160.9299999999998` in matrix TOTAL cells and cards. `ShopConfig.format_currency` used `str(amount)` which exposed the full Python-float representation. Now formats with `f"{float(amount):,.2f}"` — always exactly 2 decimals, thousands separator included. One-line fix at source means every money display across the whole app (matrix cells, cards, Quick Scan, Sales, POS, Analytics, Reports, Purchase Orders) benefits automatically.

---

## [2.4.0] - 2026-04-21

### Added
#### Lazy UI construction — startup & settings-close no longer freeze

- **`NavController.register_lazy(key, page_index, factory, on_activate)`** — new API. The factory runs on first navigation; a lightweight `QWidget` placeholder holds the stack slot until then. `register_placeholder(page_index)` + `realize(key)` + `get_lazy_instance(key)` complete the contract.
- **`_MatrixPlaceholder`** — matrix category tabs are now placeholders until the user clicks their sidebar entry. On first click `NavController._go_matrix` swaps the placeholder for a real `MatrixTab` in the same stack slot, emits `navigated`, then kicks the first `refresh()` via `QTimer.singleShot(0, …)` so the switch paints before the DB round-trip lands.
- **10 static pages migrated to lazy**: `SalesPage`, `CustomersPanel`, `PurchaseOrdersPage`, `ReturnsPage`, `BarcodeGenPage`, `ReportsPage`, `SuppliersPage`, `AnalyticsPage`, `AuditPage`, `PriceListsPage`. Each has a closure-style factory that sets `self._xxx_page` before returning; the `AnalyticsPage` factory also wires `navigate_to.connect(nav_ctrl.go)` after construction. Eager pages (`InventoryPage`, `TransactionsPage`, `QuickScanTab`) stay immediate.
- **`AsyncRefreshMixin`** (new `app/ui/workers/async_refresh.py`) — single contract for pages/tabs: `self.async_refresh(fetch, apply, key_suffix, debounce_ms)`. Keyed cancellation, `_is_alive()` guard using `sip.isdeleted`, error-path falls through to a non-blocking `_show_empty_state` instead of a modal. Baked into `BaseTab` so every matrix tab inherits it.
- **UI-thread watchdog** (new `app/ui/workers/ui_watchdog.py`) — opt-in via `SM_UI_WATCHDOG=1`. A 10 ms `QTimer` stamps `time.monotonic()`; a daemon thread warns whenever the main thread hasn't heartbeat in > 50 ms. Zero cost when disabled. Regressions that put sync DB calls back on the UI thread show up instantly in the logs.
- **Grand-total card** at the end of the matrix cards strip — emerald-accent anchor showing total units and total valuation across every part-type in the current filter. Metric tag flips `sell` ↔ `cost` with the admin toggle, exactly like the per-part-type cards.

### Performance

- **Worker pool hardening** (`app/ui/workers/worker_pool.py`) —
  - Epoch-based stale-result guard: every `submit(key, …)` bumps a per-key monotonic epoch; result / error callbacks are gated by the captured epoch so a late signal carrying stale data is silently dropped even if the cancel-event check missed it.
  - `POOL.has_pending(key)` helper so callers can coordinate with in-flight critical workers.
  - `POOL.shutdown(timeout_ms)` — called from `MainWindow.closeEvent`; cancels all work, stops debounce timers, `waitForDone()` the underlying `QThreadPool`. No more leaked workers on exit.
  - Callback error containment: exceptions inside `on_result` / `on_error` are logged instead of silently killing the signal chain.

- **Settings-close freeze — fully resolved.** `ensure_matrix_entries` (can touch 1000+ rows) now runs on `POOL` keyed `"admin:matrix_ensure"`. The admin dialog returns **instantly**. The worker's `on_result` on the main thread does the pure-widget rebuild (`rebuild_matrix_tabs` → fast-path, `apply_theme_to_matrix_tabs`, `_retranslate`, `nav_ctrl.go(saved)`). `on_error` fallback still rebuilds so the user never gets a stuck UI on a DB hiccup.

- **`rebuild_matrix_tabs` fast path** — if the active-category set hasn't changed (the common case on settings close), existing realised tabs are KEPT intact and just marked `_dirty=True`; the currently-visible tab gets a refresh via `QTimer.singleShot(0, …)`. Previously rebuild unconditionally nuked every realised tab into a placeholder, leaving the user looking at an empty page for a moment. Only true category adds/removes/reorders take the slow path and recreate placeholders.

- **`MatrixTab.refresh()`** fully async — every DB query (`get_matrix_items`, `get_all`, `get_brands`) runs off the UI thread via `POOL.submit`. In all-brands mode this replaced up to 12 synchronous repo hits per refresh with one pooled fetch; the UI thread no longer touches the DB during brand-combo changes, cost-toggle flips, or post-edit refreshes. `_add_brand_section` / `_reload_brand_container` accept pre-fetched `models=` / `item_map=` kwargs so the worker feeds every brand section at once.

- **Matrix lazy refresh** — per-category `POOL_KEY_PREFIX` (`f"matrix_{category_key}"`) so keys never collide between tabs. Each tab has a `_dirty` flag; on `COST_VIS.changed`, only the currently visible tab refreshes immediately, others flip `_dirty=True` and reconcile on their next `showEvent`. No more stampede of 5-6 parallel DB queries every time the 👁 button is clicked.

- **`ProductTable.load()`** — replaced per-row `setRowHeight(i, 48)` loop with a single pre-loop `verticalHeader().setDefaultSectionSize(48)`. The per-row call triggered a layout recalc even with `setUpdatesEnabled(False)` — saves 400-600 ms of startup UI-thread work for a 300-item inventory.

- **Per-page async conversions** —
  - `SalesPage._load_products` + `_refresh` split into worker-fetch + UI-thread `_apply_sales` / `_render_products`. Keys: `"sales_products"`, `"sales_refresh"`.
  - `PurchaseOrdersPage._refresh` combined `po_repo.get_all` + `po_repo.get_summary` into one `POOL.submit_debounced("po_refresh", …, 150)` and applied via `_apply_po_data`.
  - `AuditPage._load_data` combined `get_all_audits` + `get_summary` into one pooled fetch; KPIs + table render in `_apply_audits` on the main thread.

- **`AnalyticsPage.__init__`** — inline `self.refresh()` deferred via `QTimer.singleShot(0, self.refresh)` so widget-tree construction completes before the skeleton paint + 5 POOL workers fire. Combined with lazy construction, analytics costs nothing until the user actually opens the page.

- **`StartupController._on_ok`** — removed the eager `analytics_page.refresh()` call now that analytics is lazy. Saved 200-400 ms of skeleton-paint + worker dispatch at startup for a page the user may never open.

### Fixed

- **Blank matrix tab after settings close** — root cause was a `POOL.has_pending("admin:matrix_ensure")` guard inside `MatrixTab.refresh()`. Qt dispatches slots in connection order, so user callbacks fire **before** the pool's own `_cleanup` slot; the guard incorrectly returned `True` inside the very callback that was triggered by result delivery. Guard removed (WAL handles concurrent reads safely); the fast-path `refresh()` in `rebuild_matrix_tabs` is now deferred via `QTimer.singleShot(0, …)` so it runs on a clean event-loop idle tick.
- **Silent matrix refresh failures** — `MatrixTab.refresh()`'s `POOL.submit` now has an `on_error` handler that logs the failure with the category key. No more invisible worker exceptions leaving a page blank.
- **`ProductTable.setRowHeight` in loop** — per-row call triggered layout recalcs that `setUpdatesEnabled(False)` couldn't suppress. Moved to `defaultSectionSize` once before the loop.

### Changed

- Matrix staggering experiment reverted — staggering brand sections across ticks via `QTimer.singleShot(0, …)` opened race windows where a second refresh mid-chain left the page blank. Correctness > 200 ms of visual smoothness: `_apply_refresh` builds all sections inline.
- `MainWindow.closeEvent` now calls `POOL.shutdown(2000)` for graceful worker drain.

---

## [2.3.10] - 2026-04-21

### Added
#### Cost valuation — PIN-gated matrix redesign
- **`cost_price` column** on `inventory_items` — purchase / buy price, persisted per item. Schema V16 migration adds the column automatically on first launch.
- **Matrix columns bumped 5 → 7** per part-type group: `MIN-STOCK · DIFFERENCE · STOCK · ORDER · SELL · COST · TOTAL`.
  - **SELL** = the previous "PRICE" column renamed for clarity (item.sell_price with part-type default fallback; edit flow unchanged).
  - **COST** = new, shows `item.cost_price` in the shop's accent blue. **Hidden by default** — only shown after the owner toggles it.
  - **TOTAL** = always visible. Metric flips with the cost toggle:
    - Default: `stock × effective_sell_price`
    - Admin mode: `stock × cost_price`
  - Cell tooltip clarifies which metric is active ("Stock × sell = …" / "Stock × cost = …").
- **👁 cost-visibility toggle** in every matrix tab toolbar. Click prompts for `ShopConfig.admin_pin` (if configured, via `QInputDialog` password-echo — same pattern as `open_admin`). Button swaps closed-eye ↔ talking-eye icon and shows a green accent border when active. One flip fans out to every matrix tab via `CostVisibility.changed`.
- **Professional per-part-type cards** at the top of every matrix tab (name · total units · total valuation · `sell`/`cost` suffix). Live metric — switches from sell-based → cost-based totals when the toggle is on. Card strip lives inside a restored collapsible `BRAND & LEGEND` section alongside the brand filter row.
- **Editable cost_price** — double-click a COST cell (admin mode only) opens the same numeric dialog pattern used for sell; full Undo/Redo via `ItemRepository.update_cost_price()`.
- **Currency symbol everywhere** — SELL, COST, TOTAL cells + tooltips format through a new `_fmt_money()` helper backed by `ShopConfig.format_currency()`.

### New services / repos
- `app/services/cost_visibility.py` — session-local `COST_VIS` singleton (`QObject` with `changed` signal). Default `visible=False` on every app start — nothing persists, so sensitive valuation never leaks on an unattended laptop.
- `ItemRepository.update_cost_price(item_id, new_cost)` — new write method; `_build()` reads `cost_price` when the column exists.
- `_type_visible_width(table, ti)` helper in `matrix_widget.py` — sum of *visible* column widths for a part-type group, so banner chips never over-stretch when the COST column is hidden.
- `_SUB_MIN / _SUB_BB / _SUB_STOCK / _SUB_ORDER / _SUB_SELL / _SUB_PRICE / _SUB_TOTAL` sub-column constants — arithmetic across the matrix now self-documents.

### Performance — professional worker-pool overhaul

- **Pool hardening** (`app/ui/workers/worker_pool.py`) —
  - Epoch-based stale-result guard: every `submit(key, …)` bumps a per-key monotonic epoch; result and error callbacks are gated by the captured epoch, so a late signal carrying stale data is silently dropped even if the cancel-event check missed it.
  - New `POOL.has_pending(key)` helper so callers can skip a refresh while a critical worker (e.g. `admin:matrix_ensure`) is still writing.
  - New `POOL.shutdown(timeout_ms)` that cancels everything, stops debounce timers, and `waitForDone()` the underlying `QThreadPool`. Called from `MainWindow.closeEvent` — no more leaked workers on exit.
  - Callback-error containment: exceptions inside `on_result` / `on_error` handlers are now logged instead of swallowing the signal stream.

- **`AsyncRefreshMixin`** (new `app/ui/workers/async_refresh.py`) — single contract every page/tab now follows:
  - `self.async_refresh(fetch=…, apply=…, key_suffix=…, debounce_ms=…)`
  - Auto-cancels prior task via `POOL` keyed as `f"{POOL_KEY_PREFIX}:{key_suffix}"`.
  - `_is_alive()` guard using `sip.isdeleted` so callbacks skip deleted widgets (tab closed mid-load, language rebuild, etc.).
  - Error path falls through to `_show_empty_state(msg)` inline, not a modal — no more freezing on an error dialog.
  - Baked into `BaseTab` so every matrix tab and future tab gets it for free.

- **Startup freeze — resolved** —
  - `MainWindow._build_ui` defers `rebuild_matrix_tabs()` via `QTimer.singleShot(0, …)`; the main window paints and becomes interactive before any DB work.
  - On first-run setup, `ensure_matrix_entries()` (can touch 1000+ rows) runs on a `POOL` worker; the widget rebuild runs in the `on_result` callback on the main thread.

- **Settings-close freeze — resolved** —
  - Admin-dialog close now submits `ensure_matrix_entries` to `POOL` keyed `"admin:matrix_ensure"`. The dialog returns instantly. The worker's `on_result` on the main thread does the pure-widget rebuild (`rebuild_matrix_tabs`, `apply_theme_to_matrix_tabs`, `_retranslate`, `nav_ctrl.go(saved)`).
  - `on_error` fallback still rebuilds tabs so the user never gets a stuck UI on a DB hiccup.
  - `MatrixTab.refresh()` early-returns when `POOL.has_pending("admin:matrix_ensure")` — prevents mid-write reads and sets `_dirty=True` so the tab reconciles on its next `showEvent`.

- **Matrix lazy refresh** —
  - Every `MatrixTab` now has a `_dirty` flag. On `COST_VIS.changed`, only the **currently visible** tab refreshes immediately; others flip the flag and reconcile on their next `showEvent`. No more stampede of 5-6 parallel DB queries when the 👁 button is clicked.
  - Each `MatrixTab` uses a per-category `POOL_KEY_PREFIX` (`f"matrix_{category_key}"`) so keys never collide between parallel tabs.

- **Per-page migrations off the UI thread** —
  - `SalesPage._load_products` + `SalesPage._refresh` — both split into worker-fetch + UI-thread `_apply_sales` / `_render_products`. Keys: `"sales_products"`, `"sales_refresh"`.
  - `PurchaseOrdersPage._refresh` — `po_repo.get_all` + `po_repo.get_summary` combined into a single `POOL.submit_debounced("po_refresh", …, delay_ms=150)` and applied via `_apply_po_data`.
  - `AuditPage._load_data` — `get_all_audits` + `get_summary` combined into one pooled fetch; KPIs + table render in `_apply_audits` on the main thread.

- **UI watchdog** (new `app/ui/workers/ui_watchdog.py`) —
  - Opt-in dev diagnostic enabled via `SM_UI_WATCHDOG=1`.
  - A 10 ms `QTimer` on the UI thread stamps `time.monotonic()`; a daemon thread polls every 50 ms and logs a warning whenever the stamp is older than a configurable threshold (default 50 ms). Instantly surfaces any regression that puts a sync DB call back on the UI thread.

### Fixed
- Banner chip widths now align correctly with the visible columns when the COST column is hidden (previously over-stretched by one column-width).
- `UnboundLocalError: QScrollArea` on `MatrixTab.__init__` — a nested `from PyQt6.QtWidgets import … QScrollArea` shadowed the module-level import; removed the duplicate.
- Duplicate `BRAND:` label (collapsible section header + filter row) — section header restored to `BRAND & LEGEND` and now wraps both cards + filter together.
- Matrix banner reverted to a slim 30 px name-chip after totals moved to the top card strip; banner keeps column-grouping context without duplicating data.

### Fixed
- Banner chip widths now align correctly with the visible columns when the COST column is hidden (previously over-stretched by one column-width).
- `UnboundLocalError: QScrollArea` on `MatrixTab.__init__` — a nested `from PyQt6.QtWidgets import … QScrollArea` shadowed the module-level import; removed the duplicate.
- Duplicate `BRAND:` label (collapsible section header + filter row) — section header restored to `BRAND & LEGEND` and now wraps both cards + filter together.
- Matrix banner reverted to a slim 30 px name-chip after totals moved to the top card strip; banner keeps column-grouping context without duplicating data.

### Changed
- Matrix edit dialogs for price split into **Sell Price** and **Cost Price** with distinct titles / Undo labels.
- Cost edit instant-repaints the clicked COST cell + neighbouring TOTAL cell synchronously before the DB refresh lands, so the whole edit lands in a single visual frame. SELL edit does the same for TOTAL when not in cost mode.
- Schema version bumped **15 → 16**.

---

## [2.3.9] - 2026-04-20

### Added
#### Pricing · Quick Scan · Invoices
- **Part-type default price** — Admin → Part Types now has a "Default price" field. Every item inheriting the part type takes that price; per-item `sell_price` still overrides. New "PRICE" column in the part-type admin table.
- **€ / Price column in the matrix** — new column per part type. Green when a per-item override exists, grey when falling back to the part-type default. Double-click to edit; Ctrl+Z undoes.
- **Quick Scan live pricing & totals** — pending table now shows **Unit Price** and **Line Total** per scanned line + a totals card with **ITEMS · SUBTOTAL · GRAND TOTAL** (accent green, JetBrains Mono). Currency formatted via `ShopConfig.format_currency`.
- **Customer field on Quick Scan** — optional input; printed on the invoice when present, otherwise a walk-in record.
- **PDF invoices on every commit** — confirming a scan asks **A4 invoice** or **Thermal receipt**, persists the header + line items, and writes to `%LOCALAPPDATA%\StockPro\StockManagerPro\invoices\INV-YYYYMMDD-NNNN.pdf`. Feed row shows an **Open** button. TAKEOUT → "INVOICE"; INSERT → "STOCK RECEIPT". Layout preference remembered via QSettings.
- **New `ScanInvoiceService`** (A4 + 80 mm thermal fpdf2 layouts) and **`InvoiceRepository`** (day-prefixed numbering + price snapshot per line).

#### Reports — full overhaul
- **5 new reports**: Stock Valuation (per part type, category subtotals, grand total), Sales (with top-10 best sellers), Scan Invoices (IN/OUT history with filter), Expiring Stock (urgency-coloured), Category Performance (stock + movement per category).
- **Inventory report** now groups by **Category → Part Type** with per-section subtotals, a Brand column, and a grand-total emerald bar at the end.
- **Date range picker** on the reports page — presets (Today · 7d · 30d · 90d · This year · Custom) + `QDateEdit` from/to pickers. Applied to every date-aware report.
- **Operation filter** — contextual for Transactions (IN/OUT/ADJUST/CREATE) and Scan Invoices (ALL/IN/OUT).
- **Output path + three actions** — status bar shows the saved PDF path with **Open PDF**, **Open folder** (selects file in Explorer), **Copy path**.
- **`_ReportPDF.header() / footer()` overrides** — shop banner, title subtitle, and `Page X of Y` footer render on **every page** (not just page 1) via `alias_nb_pages()`.
- **Logo support** — `ShopConfig.logo_path` is rendered top-left of every report header when the file exists.
- **Per-table pagination** — every table redraws its column headers on a new page when rows cross the bottom margin.

#### Analytics — professional dashboard
- **Top date-range bar** — Today · 7d · 30d · 90d · Year · Custom, with automatic previous-period comparison.
- **Executive KPI row** — 4 tiles (Stock Value · Revenue · Transactions · Low Stock) each with a trend sparkline, ▲/▼ delta badge vs the previous equal-length period, and click-to-drill-down.
- **Brand-separated Valuation section** — Brand chips row at the top, then one card per brand containing category-grouped part-type rows with **share-of-brand** progress bars, category subtotals, and a brand subtotal strip. Bottom: gradient emerald Grand Total.
- **Valuation filter bar** — Brand combo + Category combo + "Clear filters" button. Active-filter badge shows how many filters are applied; grand total note shows the active filter context.
- **Sales section** — revenue trend dual-line chart with previous-period ghost overlay, mini-KPIs (sales count · units sold · avg basket · best day), top sellers + top customers HBars with currency formatting.
- **Stock movement section** — IN vs OUT dual-line chart, busiest-hours HBar, colour-coded recent activity feed.
- **Scan invoices section** — 4 KPIs (count · IN total · OUT total · avg), daily IN/OUT dual-line, top-invoice-customers HBar.
- **New UI components** — `KpiTile` (label + sparkline + delta + click), `DeltaBadge` (▲/▼ pill), `SkeletonBlock` (animated shimmer), `EmptyState` upgraded (icon + retry button), `PivotTable` redesigned as brand-separated valuation, `DualLineChart` (current + ghost overlay + hover tooltip).
- **`AnalyticsService` facade** — one class computes every tile's data block, safe to run on worker threads; tiles load independently via `POOL.submit` and swap skeletons for content as each block completes.
- **Drill-down navigation** — click KPI tile, pivot row, or brand chip → navigates to the filtered Inventory / Sales / Transactions page.

### Schema
- **V15 migration** — adds `part_types.default_price` (REAL, nullable) + two new tables `scan_invoices` and `scan_invoice_items` for invoice records, with indexes on date and invoice_id.

### New architecture
- **Repository helpers**: `ItemRepository.get_value_by_brand / get_value_by_part_type / get_value_pivot`; `TransactionRepository.get_daily_aggregates / get_hourly_aggregates`; `SaleRepository.revenue_daily / top_customers`; `InvoiceRepository.get_totals / get_daily / get_top_customers`.
- **`ScanSessionService.commit(layout, customer_name)`** — snapshots each line's price to `scan_invoice_items` so historical invoices stay stable even if prices change later.
- **`PendingScanItem`** — gains `unit_price` (captured at scan time) and a `line_total` property.
- **`HBarChart.set_data(..., value_format=callable)`** — optional formatter so chart values render with the shop currency (`€12,340.00`) instead of bare integers.

### Fixed
- **Discrepancy report crash** — added missing `_GRAY_700` / `_GRAY_100` colour constants and implemented the missing `_safe()` sanitiser. PDFs render without `NameError` / `AttributeError`.
- **Column overflow on inventory + transaction reports** — widths re-balanced so columns sum to exactly 186 mm (usable page width).
- **Missing page numbers / orphaned continuation pages** — fixed by header/footer overrides.
- **Reports now save to `%LOCALAPPDATA%\StockPro\StockManagerPro\reports\`** — same tree used by invoices and backups (was `%TEMP%`).
- **Valuation pivot ambiguous column bug** — renamed the SQL alias to `brand_name` to avoid clashing with `phone_models.brand` / `inventory_items.brand`, then GROUP BY on the full expression.
- **Brand attribution in reports** — every report resolver now falls back through `model_brand → brand → "(no brand)"`; matrix items no longer show as "(no brand)".
- **Analytics valuation scope** — includes zero-stock brand/part-type combos so the full inventory scope is visible (no more "only Apple and Samsung"); grand total unaffected since zeros add nothing.

### Changed
- **Transaction report** accepts a date range + operation filter (was hardcoded to 30 days with no op filter).
- **Backward-compatible analytics refresh API** — `_fetch_all_data` + `_apply_all_data` still exist so `main_window`'s existing `POOL.submit("analytics_refresh", …)` continues to work; the new implementation forwards to `refresh()` on the main thread.

---

## [2.3.8] - 2026-04-17

### Added
- **Content-aware column widths** — every table column now sizes to `max(proportional_target, header_text_fit, widest_cell_fit)` at the active font, so headers and model names are ALWAYS fully visible at any zoom level. Applied to matrix, inventory, transactions, and admin tables.
- **Per-item font scaling** — matrix items with individual `setFont` (`_FONT_MODEL` 11pt, `_FONT_COLOR` 9pt, `_FONT_BRAND` 12pt, `_FONT_DATA` 10pt, `_FONT_MONO` 11pt) now scale correctly via a new `BASE_PT_ROLE` marker that remembers each item's 100% point size
- **Real-time live zoom on slider drag** — every slider tick applies zoom through the 16 ms coalescer; drag feels instant with no lag

### Changed
- **Only the active tab is re-zoomed** on slider changes — previously all 6 matrix tabs were iterated every tick (~15 000 items rebuilt per drag step). Inactive tabs catch up lazily when the user navigates to them via `matrix_tab.refresh()`.
- **QFont cache keyed by (family, weight, base_pt)** — a typical matrix has ~1000 items but only ~5 unique font variants; reusing the cached `QFont` instances drastically reduces allocations during zoom
- **Widget-level QSS on QHeaderView** — overrides app-wide `font-size: 11px` and `padding: 10px 16px` so programmatic `setFont` actually takes effect; header height scales with the font + proportional vertical padding
- **Footer zoom widget fully locked** — every child (slider, buttons, preset, divider) uses `Fixed/Fixed` size policy with `setFixedSize`; preset button is `setFixedSize(56, 22)` so percentage text changes ("50%" ↔ "200%") never shift the layout

### Fixed
- **Table headers disappearing at low zoom** — caused by app-wide QSS overriding per-table `setFont`; now overridden with widget-level stylesheet so headers render at the actual scaled font
- **Model names clipped** — column now measures widest model cell using that cell's own scaled font, not the widget default
- **Footer zoom group stretching during drag** — every inner widget locked to `Fixed` size policy and the group itself pinned to a fixed total width
- **Zoom slider lag** — live-drag now handled via a 16 ms coalescing timer in `ZoomService` plus visible-tab-only dispatch; slider release commits synchronously

---

## [2.3.7] - 2026-04-17

### Added
- **Professional table zoom** — `ZoomService` singleton drives footer-slider zoom for data tables only: matrix tabs (Displays, Batteries, Cases, …), inventory product table, transaction table, and every QTableWidget inside admin panels. Clean separation from app-chrome sizing.
- **Redesigned footer zoom widget** — zoom-out button + slider with tick marks at every preset + zoom-in button + preset dropdown (50/75/100/125/150/200 + Fit + Reset) + reset button; grouped in a bordered pill with proper QToolButton hover/pressed states
- **Zoom persistence** — table zoom saved to `ShopConfig.zoom_level`, restored on launch; 500ms debounced save so slider drags don't hit the DB
- **UI Scale admin setting** — new dropdown in Shop Settings → Regional & Display: Small (85%), Normal (100%), Large (115%), Extra Large (130%). Controls overall app chrome size (sidebar, header, footer, base font). Restart required — shows a dialog confirmation on change.
- **Slimmer sidebar default** — base width reduced from 240 px → 192 px for a more professional look; UI Scale enlarges it if the user prefers

### Changed
- **Zoom scope limited to tables** — sidebar, header, footer, dashboard KPI cards, analytics charts no longer respond to the footer zoom slider (by design — use UI Scale for chrome sizing)
- **Truly proportional table scaling** — removed arbitrary font floors (9pt body / 8pt header); minimum 6pt for genuine shrinking at 50% zoom. Column widths, row heights, padding all scale via `ZOOM.scale(base, minimum)` — no hard floors fighting the zoom
- **Zoom shortcuts centralised** — Ctrl+=, Ctrl++, Ctrl+-, Ctrl+0, Ctrl+Scroll all route through `ZoomService` so footer + shortcuts + wheel stay in sync
- **Matrix refresh preserves zoom** — after refresh, containers re-apply current zoom factor directly (no round-trip through main window)

### Fixed
- **Header truncation at low zoom** — eliminated by proportional column/padding scaling and lower font floor
- **Zoom reset on tab refresh** — matrix tabs now re-apply zoom to all rebuilt brand containers unconditionally

---

## [2.3.6] - 2026-04-16

### Fixed
- **Undo/redo UI freeze** — undo and redo operations now run on the worker pool instead of the main thread, so the window stays fully responsive during the operation
- **Undo/redo real-time refresh** — after an undo/redo, the currently visible tab (inventory, matrix, transactions, analytics) now refreshes in place; you no longer need to switch tabs and come back to see the changes
- **Undo/redo button responsiveness** — undo/redo buttons re-enable immediately after the DB operation completes, before the view refresh; chained undos feel instant
- **Header truncation at low zoom** — header labels (`MIN-VORRAT`, `BESTELLUNG`, `DIFFERENZ`, `BESTAND`) now stay fully visible when zooming out; column widths measured against the new font and padded with a generous 48px buffer

### Changed
- **Thread-safe undo commands** — all undo/redo command lambdas are now DB-only (no UI calls from worker threads); main-thread refresh handled centrally in `_on_undo_done`
- **Inventory filter on undo** — debounce disabled for the post-undo refresh so the product table updates instantly

---

## [2.3.5] - 2026-04-16

### Added
- **Per-brand matrix sections** — "All Brands" view shows separate sections per brand, each with its own correct part-type columns; outer scroll with full-sized sections and sticky headers
- **No Colors option** — "No Colors" button in color picker removes all colour variants for a model, keeping only the base product
- **Expanded colour palette** — added Red, Pink, Yellow, Orange to available colours in settings and matrix picker

### Fixed
- **Brand display cleanup** — Samsung/Xiaomi no longer show Apple-only part types (stale inventory rows cleaned on startup)

---

## [2.4.3] - 2026-04-23

### Added
- **Shop setting: "Show color totals in matrix"** — new checkbox in Admin → Shop Settings (Regional card, under "Show sell totals"). When off, the per-color sub-rows hide their SELL / COST / TOTAL cells (rendered as `—`, not editable), so valuation is only shown on the model summary row. Useful when all color variants share the same price — the per-color repeats are just noise. Persisted via `ShopConfig.show_color_totals` (reuses `app_config`, no migration). Typed accessor `ShopConfig.is_show_color_totals`. Default ON — existing layouts unchanged until toggled.
- **Color picker on aggregate stock edits** — when a model has color variants, double-clicking STOCK on the model summary row now pops a "Choose Color" dialog (listing the variants of that model × part-type). Previously the edit silently landed on whichever sibling was returned first (usually White), because the parent row's meta held `any_item.id` — a real bug that let stock ops overwrite the wrong color. Uses `ItemRepository.get_colored_siblings`.

### Changed
- **Sell / cost price edits on aggregate rows propagate to all color variants.** Editing SELL or COST on the model summary row of a colored model now writes the new price to every sibling in one pass, with a single bundled undo entry (`Sell <model>·<part> all colors → X` / `Cost … all colors → X`). The prompt title gains a "(all colors)" suffix and a trailing note so it's obvious what's about to happen. Single-color (non-aggregate) edits keep the previous per-item behaviour. Rationale: in practice variants of the same model share pricing — editing one and not the rest was a common source of drift.

### Fixed
- **Aggregate stock edits no longer silently hit the wrong color.** See the color-picker note above.

---

## [2.4.2] - 2026-04-21

### Added
- **Shop setting: "Show sell totals in matrix"** — new checkbox in Admin → Shop Settings (Regional card, under UI Scale). When off, the matrix TOTAL column and the value portion of the per-part-type cards + the grand-total card are hidden, so shop assistants see stock counts without seeing sell valuation. Units stay visible either way. Cost mode (PIN-gated via 👁) overrides the hide so the cost/sell comparison still makes sense when the owner has authenticated.
  - Persisted via `ShopConfig.show_sell_totals` (reuses the existing `app_config` key-value mechanism — no DB migration needed).
  - Typed accessor `ShopConfig.is_show_sell_totals`.
  - Default is ON — existing users see zero change until they toggle it off.
  - Live-update on Save: the existing settings-close rebuild chain (`ShopConfig.invalidate()` → `rebuild_matrix_tabs()` fast path → `tab.refresh()`) propagates the new state to every matrix tab instantly.

### Fixed
- **Float-precision display bug** — `7 × 22.99` was rendering as `€160.9299999999998` in matrix TOTAL cells and cards. `ShopConfig.format_currency` used `str(amount)` which exposed the full Python-float representation. Now formats with `f"{float(amount):,.2f}"` — always exactly 2 decimals, thousands separator included. One-line fix at source means every money display across the whole app (matrix cells, cards, Quick Scan, Sales, POS, Analytics, Reports, Purchase Orders) benefits automatically.

---

## [2.4.0] - 2026-04-21

### Added
#### Lazy UI construction — startup & settings-close no longer freeze

- **`NavController.register_lazy(key, page_index, factory, on_activate)`** — new API. The factory runs on first navigation; a lightweight `QWidget` placeholder holds the stack slot until then. `register_placeholder(page_index)` + `realize(key)` + `get_lazy_instance(key)` complete the contract.
- **`_MatrixPlaceholder`** — matrix category tabs are now placeholders until the user clicks their sidebar entry. On first click `NavController._go_matrix` swaps the placeholder for a real `MatrixTab` in the same stack slot, emits `navigated`, then kicks the first `refresh()` via `QTimer.singleShot(0, …)` so the switch paints before the DB round-trip lands.
- **10 static pages migrated to lazy**: `SalesPage`, `CustomersPanel`, `PurchaseOrdersPage`, `ReturnsPage`, `BarcodeGenPage`, `ReportsPage`, `SuppliersPage`, `AnalyticsPage`, `AuditPage`, `PriceListsPage`. Each has a closure-style factory that sets `self._xxx_page` before returning; the `AnalyticsPage` factory also wires `navigate_to.connect(nav_ctrl.go)` after construction. Eager pages (`InventoryPage`, `TransactionsPage`, `QuickScanTab`) stay immediate.
- **`AsyncRefreshMixin`** (new `app/ui/workers/async_refresh.py`) — single contract for pages/tabs: `self.async_refresh(fetch, apply, key_suffix, debounce_ms)`. Keyed cancellation, `_is_alive()` guard using `sip.isdeleted`, error-path falls through to a non-blocking `_show_empty_state` instead of a modal. Baked into `BaseTab` so every matrix tab inherits it.
- **UI-thread watchdog** (new `app/ui/workers/ui_watchdog.py`) — opt-in via `SM_UI_WATCHDOG=1`. A 10 ms `QTimer` stamps `time.monotonic()`; a daemon thread warns whenever the main thread hasn't heartbeat in > 50 ms. Zero cost when disabled. Regressions that put sync DB calls back on the UI thread show up instantly in the logs.
- **Grand-total card** at the end of the matrix cards strip — emerald-accent anchor showing total units and total valuation across every part-type in the current filter. Metric tag flips `sell` ↔ `cost` with the admin toggle, exactly like the per-part-type cards.

### Performance

- **Worker pool hardening** (`app/ui/workers/worker_pool.py`) —
  - Epoch-based stale-result guard: every `submit(key, …)` bumps a per-key monotonic epoch; result / error callbacks are gated by the captured epoch so a late signal carrying stale data is silently dropped even if the cancel-event check missed it.
  - `POOL.has_pending(key)` helper so callers can coordinate with in-flight critical workers.
  - `POOL.shutdown(timeout_ms)` — called from `MainWindow.closeEvent`; cancels all work, stops debounce timers, `waitForDone()` the underlying `QThreadPool`. No more leaked workers on exit.
  - Callback error containment: exceptions inside `on_result` / `on_error` are logged instead of silently killing the signal chain.

- **Settings-close freeze — fully resolved.** `ensure_matrix_entries` (can touch 1000+ rows) now runs on `POOL` keyed `"admin:matrix_ensure"`. The admin dialog returns **instantly**. The worker's `on_result` on the main thread does the pure-widget rebuild (`rebuild_matrix_tabs` → fast-path, `apply_theme_to_matrix_tabs`, `_retranslate`, `nav_ctrl.go(saved)`). `on_error` fallback still rebuilds so the user never gets a stuck UI on a DB hiccup.

- **`rebuild_matrix_tabs` fast path** — if the active-category set hasn't changed (the common case on settings close), existing realised tabs are KEPT intact and just marked `_dirty=True`; the currently-visible tab gets a refresh via `QTimer.singleShot(0, …)`. Previously rebuild unconditionally nuked every realised tab into a placeholder, leaving the user looking at an empty page for a moment. Only true category adds/removes/reorders take the slow path and recreate placeholders.

- **`MatrixTab.refresh()`** fully async — every DB query (`get_matrix_items`, `get_all`, `get_brands`) runs off the UI thread via `POOL.submit`. In all-brands mode this replaced up to 12 synchronous repo hits per refresh with one pooled fetch; the UI thread no longer touches the DB during brand-combo changes, cost-toggle flips, or post-edit refreshes. `_add_brand_section` / `_reload_brand_container` accept pre-fetched `models=` / `item_map=` kwargs so the worker feeds every brand section at once.

- **Matrix lazy refresh** — per-category `POOL_KEY_PREFIX` (`f"matrix_{category_key}"`) so keys never collide between tabs. Each tab has a `_dirty` flag; on `COST_VIS.changed`, only the currently visible tab refreshes immediately, others flip `_dirty=True` and reconcile on their next `showEvent`. No more stampede of 5-6 parallel DB queries every time the 👁 button is clicked.

- **`ProductTable.load()`** — replaced per-row `setRowHeight(i, 48)` loop with a single pre-loop `verticalHeader().setDefaultSectionSize(48)`. The per-row call triggered a layout recalc even with `setUpdatesEnabled(False)` — saves 400-600 ms of startup UI-thread work for a 300-item inventory.

- **Per-page async conversions** —
  - `SalesPage._load_products` + `_refresh` split into worker-fetch + UI-thread `_apply_sales` / `_render_products`. Keys: `"sales_products"`, `"sales_refresh"`.
  - `PurchaseOrdersPage._refresh` combined `po_repo.get_all` + `po_repo.get_summary` into one `POOL.submit_debounced("po_refresh", …, 150)` and applied via `_apply_po_data`.
  - `AuditPage._load_data` combined `get_all_audits` + `get_summary` into one pooled fetch; KPIs + table render in `_apply_audits` on the main thread.

- **`AnalyticsPage.__init__`** — inline `self.refresh()` deferred via `QTimer.singleShot(0, self.refresh)` so widget-tree construction completes before the skeleton paint + 5 POOL workers fire. Combined with lazy construction, analytics costs nothing until the user actually opens the page.

- **`StartupController._on_ok`** — removed the eager `analytics_page.refresh()` call now that analytics is lazy. Saved 200-400 ms of skeleton-paint + worker dispatch at startup for a page the user may never open.

### Fixed

- **Blank matrix tab after settings close** — root cause was a `POOL.has_pending("admin:matrix_ensure")` guard inside `MatrixTab.refresh()`. Qt dispatches slots in connection order, so user callbacks fire **before** the pool's own `_cleanup` slot; the guard incorrectly returned `True` inside the very callback that was triggered by result delivery. Guard removed (WAL handles concurrent reads safely); the fast-path `refresh()` in `rebuild_matrix_tabs` is now deferred via `QTimer.singleShot(0, …)` so it runs on a clean event-loop idle tick.
- **Silent matrix refresh failures** — `MatrixTab.refresh()`'s `POOL.submit` now has an `on_error` handler that logs the failure with the category key. No more invisible worker exceptions leaving a page blank.
- **`ProductTable.setRowHeight` in loop** — per-row call triggered layout recalcs that `setUpdatesEnabled(False)` couldn't suppress. Moved to `defaultSectionSize` once before the loop.

### Changed

- Matrix staggering experiment reverted — staggering brand sections across ticks via `QTimer.singleShot(0, …)` opened race windows where a second refresh mid-chain left the page blank. Correctness > 200 ms of visual smoothness: `_apply_refresh` builds all sections inline.
- `MainWindow.closeEvent` now calls `POOL.shutdown(2000)` for graceful worker drain.

---

## [2.3.10] - 2026-04-21

### Added
#### Cost valuation — PIN-gated matrix redesign
- **`cost_price` column** on `inventory_items` — purchase / buy price, persisted per item. Schema V16 migration adds the column automatically on first launch.
- **Matrix columns bumped 5 → 7** per part-type group: `MIN-STOCK · DIFFERENCE · STOCK · ORDER · SELL · COST · TOTAL`.
  - **SELL** = the previous "PRICE" column renamed for clarity (item.sell_price with part-type default fallback; edit flow unchanged).
  - **COST** = new, shows `item.cost_price` in the shop's accent blue. **Hidden by default** — only shown after the owner toggles it.
  - **TOTAL** = always visible. Metric flips with the cost toggle:
    - Default: `stock × effective_sell_price`
    - Admin mode: `stock × cost_price`
  - Cell tooltip clarifies which metric is active ("Stock × sell = …" / "Stock × cost = …").
- **👁 cost-visibility toggle** in every matrix tab toolbar. Click prompts for `ShopConfig.admin_pin` (if configured, via `QInputDialog` password-echo — same pattern as `open_admin`). Button swaps closed-eye ↔ talking-eye icon and shows a green accent border when active. One flip fans out to every matrix tab via `CostVisibility.changed`.
- **Professional per-part-type cards** at the top of every matrix tab (name · total units · total valuation · `sell`/`cost` suffix). Live metric — switches from sell-based → cost-based totals when the toggle is on. Card strip lives inside a restored collapsible `BRAND & LEGEND` section alongside the brand filter row.
- **Editable cost_price** — double-click a COST cell (admin mode only) opens the same numeric dialog pattern used for sell; full Undo/Redo via `ItemRepository.update_cost_price()`.
- **Currency symbol everywhere** — SELL, COST, TOTAL cells + tooltips format through a new `_fmt_money()` helper backed by `ShopConfig.format_currency()`.

### New services / repos
- `app/services/cost_visibility.py` — session-local `COST_VIS` singleton (`QObject` with `changed` signal). Default `visible=False` on every app start — nothing persists, so sensitive valuation never leaks on an unattended laptop.
- `ItemRepository.update_cost_price(item_id, new_cost)` — new write method; `_build()` reads `cost_price` when the column exists.
- `_type_visible_width(table, ti)` helper in `matrix_widget.py` — sum of *visible* column widths for a part-type group, so banner chips never over-stretch when the COST column is hidden.
- `_SUB_MIN / _SUB_BB / _SUB_STOCK / _SUB_ORDER / _SUB_SELL / _SUB_PRICE / _SUB_TOTAL` sub-column constants — arithmetic across the matrix now self-documents.

### Performance — professional worker-pool overhaul

- **Pool hardening** (`app/ui/workers/worker_pool.py`) —
  - Epoch-based stale-result guard: every `submit(key, …)` bumps a per-key monotonic epoch; result and error callbacks are gated by the captured epoch, so a late signal carrying stale data is silently dropped even if the cancel-event check missed it.
  - New `POOL.has_pending(key)` helper so callers can skip a refresh while a critical worker (e.g. `admin:matrix_ensure`) is still writing.
  - New `POOL.shutdown(timeout_ms)` that cancels everything, stops debounce timers, and `waitForDone()` the underlying `QThreadPool`. Called from `MainWindow.closeEvent` — no more leaked workers on exit.
  - Callback-error containment: exceptions inside `on_result` / `on_error` handlers are now logged instead of swallowing the signal stream.

- **`AsyncRefreshMixin`** (new `app/ui/workers/async_refresh.py`) — single contract every page/tab now follows:
  - `self.async_refresh(fetch=…, apply=…, key_suffix=…, debounce_ms=…)`
  - Auto-cancels prior task via `POOL` keyed as `f"{POOL_KEY_PREFIX}:{key_suffix}"`.
  - `_is_alive()` guard using `sip.isdeleted` so callbacks skip deleted widgets (tab closed mid-load, language rebuild, etc.).
  - Error path falls through to `_show_empty_state(msg)` inline, not a modal — no more freezing on an error dialog.
  - Baked into `BaseTab` so every matrix tab and future tab gets it for free.

- **Startup freeze — resolved** —
  - `MainWindow._build_ui` defers `rebuild_matrix_tabs()` via `QTimer.singleShot(0, …)`; the main window paints and becomes interactive before any DB work.
  - On first-run setup, `ensure_matrix_entries()` (can touch 1000+ rows) runs on a `POOL` worker; the widget rebuild runs in the `on_result` callback on the main thread.

- **Settings-close freeze — resolved** —
  - Admin-dialog close now submits `ensure_matrix_entries` to `POOL` keyed `"admin:matrix_ensure"`. The dialog returns instantly. The worker's `on_result` on the main thread does the pure-widget rebuild (`rebuild_matrix_tabs`, `apply_theme_to_matrix_tabs`, `_retranslate`, `nav_ctrl.go(saved)`).
  - `on_error` fallback still rebuilds tabs so the user never gets a stuck UI on a DB hiccup.
  - `MatrixTab.refresh()` early-returns when `POOL.has_pending("admin:matrix_ensure")` — prevents mid-write reads and sets `_dirty=True` so the tab reconciles on its next `showEvent`.

- **Matrix lazy refresh** —
  - Every `MatrixTab` now has a `_dirty` flag. On `COST_VIS.changed`, only the **currently visible** tab refreshes immediately; others flip the flag and reconcile on their next `showEvent`. No more stampede of 5-6 parallel DB queries when the 👁 button is clicked.
  - Each `MatrixTab` uses a per-category `POOL_KEY_PREFIX` (`f"matrix_{category_key}"`) so keys never collide between parallel tabs.

- **Per-page migrations off the UI thread** —
  - `SalesPage._load_products` + `SalesPage._refresh` — both split into worker-fetch + UI-thread `_apply_sales` / `_render_products`. Keys: `"sales_products"`, `"sales_refresh"`.
  - `PurchaseOrdersPage._refresh` — `po_repo.get_all` + `po_repo.get_summary` combined into a single `POOL.submit_debounced("po_refresh", …, delay_ms=150)` and applied via `_apply_po_data`.
  - `AuditPage._load_data` — `get_all_audits` + `get_summary` combined into one pooled fetch; KPIs + table render in `_apply_audits` on the main thread.

- **UI watchdog** (new `app/ui/workers/ui_watchdog.py`) —
  - Opt-in dev diagnostic enabled via `SM_UI_WATCHDOG=1`.
  - A 10 ms `QTimer` on the UI thread stamps `time.monotonic()`; a daemon thread polls every 50 ms and logs a warning whenever the stamp is older than a configurable threshold (default 50 ms). Instantly surfaces any regression that puts a sync DB call back on the UI thread.

### Fixed
- Banner chip widths now align correctly with the visible columns when the COST column is hidden (previously over-stretched by one column-width).
- `UnboundLocalError: QScrollArea` on `MatrixTab.__init__` — a nested `from PyQt6.QtWidgets import … QScrollArea` shadowed the module-level import; removed the duplicate.
- Duplicate `BRAND:` label (collapsible section header + filter row) — section header restored to `BRAND & LEGEND` and now wraps both cards + filter together.
- Matrix banner reverted to a slim 30 px name-chip after totals moved to the top card strip; banner keeps column-grouping context without duplicating data.

### Fixed
- Banner chip widths now align correctly with the visible columns when the COST column is hidden (previously over-stretched by one column-width).
- `UnboundLocalError: QScrollArea` on `MatrixTab.__init__` — a nested `from PyQt6.QtWidgets import … QScrollArea` shadowed the module-level import; removed the duplicate.
- Duplicate `BRAND:` label (collapsible section header + filter row) — section header restored to `BRAND & LEGEND` and now wraps both cards + filter together.
- Matrix banner reverted to a slim 30 px name-chip after totals moved to the top card strip; banner keeps column-grouping context without duplicating data.

### Changed
- Matrix edit dialogs for price split into **Sell Price** and **Cost Price** with distinct titles / Undo labels.
- Cost edit instant-repaints the clicked COST cell + neighbouring TOTAL cell synchronously before the DB refresh lands, so the whole edit lands in a single visual frame. SELL edit does the same for TOTAL when not in cost mode.
- Schema version bumped **15 → 16**.

---

## [2.3.9] - 2026-04-20

### Added
#### Pricing · Quick Scan · Invoices
- **Part-type default price** — Admin → Part Types now has a "Default price" field. Every item inheriting the part type takes that price; per-item `sell_price` still overrides. New "PRICE" column in the part-type admin table.
- **€ / Price column in the matrix** — new column per part type. Green when a per-item override exists, grey when falling back to the part-type default. Double-click to edit; Ctrl+Z undoes.
- **Quick Scan live pricing & totals** — pending table now shows **Unit Price** and **Line Total** per scanned line + a totals card with **ITEMS · SUBTOTAL · GRAND TOTAL** (accent green, JetBrains Mono). Currency formatted via `ShopConfig.format_currency`.
- **Customer field on Quick Scan** — optional input; printed on the invoice when present, otherwise a walk-in record.
- **PDF invoices on every commit** — confirming a scan asks **A4 invoice** or **Thermal receipt**, persists the header + line items, and writes to `%LOCALAPPDATA%\StockPro\StockManagerPro\invoices\INV-YYYYMMDD-NNNN.pdf`. Feed row shows an **Open** button. TAKEOUT → "INVOICE"; INSERT → "STOCK RECEIPT". Layout preference remembered via QSettings.
- **New `ScanInvoiceService`** (A4 + 80 mm thermal fpdf2 layouts) and **`InvoiceRepository`** (day-prefixed numbering + price snapshot per line).

#### Reports — full overhaul
- **5 new reports**: Stock Valuation (per part type, category subtotals, grand total), Sales (with top-10 best sellers), Scan Invoices (IN/OUT history with filter), Expiring Stock (urgency-coloured), Category Performance (stock + movement per category).
- **Inventory report** now groups by **Category → Part Type** with per-section subtotals, a Brand column, and a grand-total emerald bar at the end.
- **Date range picker** on the reports page — presets (Today · 7d · 30d · 90d · This year · Custom) + `QDateEdit` from/to pickers. Applied to every date-aware report.
- **Operation filter** — contextual for Transactions (IN/OUT/ADJUST/CREATE) and Scan Invoices (ALL/IN/OUT).
- **Output path + three actions** — status bar shows the saved PDF path with **Open PDF**, **Open folder** (selects file in Explorer), **Copy path**.
- **`_ReportPDF.header() / footer()` overrides** — shop banner, title subtitle, and `Page X of Y` footer render on **every page** (not just page 1) via `alias_nb_pages()`.
- **Logo support** — `ShopConfig.logo_path` is rendered top-left of every report header when the file exists.
- **Per-table pagination** — every table redraws its column headers on a new page when rows cross the bottom margin.

#### Analytics — professional dashboard
- **Top date-range bar** — Today · 7d · 30d · 90d · Year · Custom, with automatic previous-period comparison.
- **Executive KPI row** — 4 tiles (Stock Value · Revenue · Transactions · Low Stock) each with a trend sparkline, ▲/▼ delta badge vs the previous equal-length period, and click-to-drill-down.
- **Brand-separated Valuation section** — Brand chips row at the top, then one card per brand containing category-grouped part-type rows with **share-of-brand** progress bars, category subtotals, and a brand subtotal strip. Bottom: gradient emerald Grand Total.
- **Valuation filter bar** — Brand combo + Category combo + "Clear filters" button. Active-filter badge shows how many filters are applied; grand total note shows the active filter context.
- **Sales section** — revenue trend dual-line chart with previous-period ghost overlay, mini-KPIs (sales count · units sold · avg basket · best day), top sellers + top customers HBars with currency formatting.
- **Stock movement section** — IN vs OUT dual-line chart, busiest-hours HBar, colour-coded recent activity feed.
- **Scan invoices section** — 4 KPIs (count · IN total · OUT total · avg), daily IN/OUT dual-line, top-invoice-customers HBar.
- **New UI components** — `KpiTile` (label + sparkline + delta + click), `DeltaBadge` (▲/▼ pill), `SkeletonBlock` (animated shimmer), `EmptyState` upgraded (icon + retry button), `PivotTable` redesigned as brand-separated valuation, `DualLineChart` (current + ghost overlay + hover tooltip).
- **`AnalyticsService` facade** — one class computes every tile's data block, safe to run on worker threads; tiles load independently via `POOL.submit` and swap skeletons for content as each block completes.
- **Drill-down navigation** — click KPI tile, pivot row, or brand chip → navigates to the filtered Inventory / Sales / Transactions page.

### Schema
- **V15 migration** — adds `part_types.default_price` (REAL, nullable) + two new tables `scan_invoices` and `scan_invoice_items` for invoice records, with indexes on date and invoice_id.

### New architecture
- **Repository helpers**: `ItemRepository.get_value_by_brand / get_value_by_part_type / get_value_pivot`; `TransactionRepository.get_daily_aggregates / get_hourly_aggregates`; `SaleRepository.revenue_daily / top_customers`; `InvoiceRepository.get_totals / get_daily / get_top_customers`.
- **`ScanSessionService.commit(layout, customer_name)`** — snapshots each line's price to `scan_invoice_items` so historical invoices stay stable even if prices change later.
- **`PendingScanItem`** — gains `unit_price` (captured at scan time) and a `line_total` property.
- **`HBarChart.set_data(..., value_format=callable)`** — optional formatter so chart values render with the shop currency (`€12,340.00`) instead of bare integers.

### Fixed
- **Discrepancy report crash** — added missing `_GRAY_700` / `_GRAY_100` colour constants and implemented the missing `_safe()` sanitiser. PDFs render without `NameError` / `AttributeError`.
- **Column overflow on inventory + transaction reports** — widths re-balanced so columns sum to exactly 186 mm (usable page width).
- **Missing page numbers / orphaned continuation pages** — fixed by header/footer overrides.
- **Reports now save to `%LOCALAPPDATA%\StockPro\StockManagerPro\reports\`** — same tree used by invoices and backups (was `%TEMP%`).
- **Valuation pivot ambiguous column bug** — renamed the SQL alias to `brand_name` to avoid clashing with `phone_models.brand` / `inventory_items.brand`, then GROUP BY on the full expression.
- **Brand attribution in reports** — every report resolver now falls back through `model_brand → brand → "(no brand)"`; matrix items no longer show as "(no brand)".
- **Analytics valuation scope** — includes zero-stock brand/part-type combos so the full inventory scope is visible (no more "only Apple and Samsung"); grand total unaffected since zeros add nothing.

### Changed
- **Transaction report** accepts a date range + operation filter (was hardcoded to 30 days with no op filter).
- **Backward-compatible analytics refresh API** — `_fetch_all_data` + `_apply_all_data` still exist so `main_window`'s existing `POOL.submit("analytics_refresh", …)` continues to work; the new implementation forwards to `refresh()` on the main thread.

---

## [2.3.8] - 2026-04-17

### Added
- **Content-aware column widths** — every table column now sizes to `max(proportional_target, header_text_fit, widest_cell_fit)` at the active font, so headers and model names are ALWAYS fully visible at any zoom level. Applied to matrix, inventory, transactions, and admin tables.
- **Per-item font scaling** — matrix items with individual `setFont` (`_FONT_MODEL` 11pt, `_FONT_COLOR` 9pt, `_FONT_BRAND` 12pt, `_FONT_DATA` 10pt, `_FONT_MONO` 11pt) now scale correctly via a new `BASE_PT_ROLE` marker that remembers each item's 100% point size
- **Real-time live zoom on slider drag** — every slider tick applies zoom through the 16 ms coalescer; drag feels instant with no lag

### Changed
- **Only the active tab is re-zoomed** on slider changes — previously all 6 matrix tabs were iterated every tick (~15 000 items rebuilt per drag step). Inactive tabs catch up lazily when the user navigates to them via `matrix_tab.refresh()`.
- **QFont cache keyed by (family, weight, base_pt)** — a typical matrix has ~1000 items but only ~5 unique font variants; reusing the cached `QFont` instances drastically reduces allocations during zoom
- **Widget-level QSS on QHeaderView** — overrides app-wide `font-size: 11px` and `padding: 10px 16px` so programmatic `setFont` actually takes effect; header height scales with the font + proportional vertical padding
- **Footer zoom widget fully locked** — every child (slider, buttons, preset, divider) uses `Fixed/Fixed` size policy with `setFixedSize`; preset button is `setFixedSize(56, 22)` so percentage text changes ("50%" ↔ "200%") never shift the layout

### Fixed
- **Table headers disappearing at low zoom** — caused by app-wide QSS overriding per-table `setFont`; now overridden with widget-level stylesheet so headers render at the actual scaled font
- **Model names clipped** — column now measures widest model cell using that cell's own scaled font, not the widget default
- **Footer zoom group stretching during drag** — every inner widget locked to `Fixed` size policy and the group itself pinned to a fixed total width
- **Zoom slider lag** — live-drag now handled via a 16 ms coalescing timer in `ZoomService` plus visible-tab-only dispatch; slider release commits synchronously

---

## [2.3.7] - 2026-04-17

### Added
- **Professional table zoom** — `ZoomService` singleton drives footer-slider zoom for data tables only: matrix tabs (Displays, Batteries, Cases, …), inventory product table, transaction table, and every QTableWidget inside admin panels. Clean separation from app-chrome sizing.
- **Redesigned footer zoom widget** — zoom-out button + slider with tick marks at every preset + zoom-in button + preset dropdown (50/75/100/125/150/200 + Fit + Reset) + reset button; grouped in a bordered pill with proper QToolButton hover/pressed states
- **Zoom persistence** — table zoom saved to `ShopConfig.zoom_level`, restored on launch; 500ms debounced save so slider drags don't hit the DB
- **UI Scale admin setting** — new dropdown in Shop Settings → Regional & Display: Small (85%), Normal (100%), Large (115%), Extra Large (130%). Controls overall app chrome size (sidebar, header, footer, base font). Restart required — shows a dialog confirmation on change.
- **Slimmer sidebar default** — base width reduced from 240 px → 192 px for a more professional look; UI Scale enlarges it if the user prefers

### Changed
- **Zoom scope limited to tables** — sidebar, header, footer, dashboard KPI cards, analytics charts no longer respond to the footer zoom slider (by design — use UI Scale for chrome sizing)
- **Truly proportional table scaling** — removed arbitrary font floors (9pt body / 8pt header); minimum 6pt for genuine shrinking at 50% zoom. Column widths, row heights, padding all scale via `ZOOM.scale(base, minimum)` — no hard floors fighting the zoom
- **Zoom shortcuts centralised** — Ctrl+=, Ctrl++, Ctrl+-, Ctrl+0, Ctrl+Scroll all route through `ZoomService` so footer + shortcuts + wheel stay in sync
- **Matrix refresh preserves zoom** — after refresh, containers re-apply current zoom factor directly (no round-trip through main window)

### Fixed
- **Header truncation at low zoom** — eliminated by proportional column/padding scaling and lower font floor
- **Zoom reset on tab refresh** — matrix tabs now re-apply zoom to all rebuilt brand containers unconditionally

---

## [2.3.6] - 2026-04-16

### Fixed
- **Undo/redo UI freeze** — undo and redo operations now run on the worker pool instead of the main thread, so the window stays fully responsive during the operation
- **Undo/redo real-time refresh** — after an undo/redo, the currently visible tab (inventory, matrix, transactions, analytics) now refreshes in place; you no longer need to switch tabs and come back to see the changes
- **Undo/redo button responsiveness** — undo/redo buttons re-enable immediately after the DB operation completes, before the view refresh; chained undos feel instant
- **Header truncation at low zoom** — header labels (`MIN-VORRAT`, `BESTELLUNG`, `DIFFERENZ`, `BESTAND`) now stay fully visible when zooming out; column widths measured against the new font and padded with a generous 48px buffer

### Changed
- **Thread-safe undo commands** — all undo/redo command lambdas are now DB-only (no UI calls from worker threads); main-thread refresh handled centrally in `_on_undo_done`
- **Inventory filter on undo** — debounce disabled for the post-undo refresh so the product table updates instantly

---

## [2.3.5] - 2026-04-16

### Added
- **Per-brand matrix sections** — "All Brands" view shows separate sections per brand, each with its own correct part-type columns; outer scroll with full-sized sections and sticky headers
- **No Colors option** — "No Colors" button in color picker removes all colour variants for a model, keeping only the base product
- **Expanded colour palette** — added Red, Pink, Yellow, Orange to available colours in settings and matrix picker

### Fixed
- **Brand display cleanup** — Samsung/Xiaomi no longer show Apple-only part types (stale inventory rows cleaned on startup)

---

## [2.3.4] - 2026-04-12

### Added
- **Sticky model column** — frozen left-side table for model names stays visible when scrolling horizontally in the matrix
- **Part-type banner bar** — colour-coded part-type names displayed above column headers via synced QScrollArea
- **Excel-like zoom** — Ctrl+Scroll / Ctrl+Plus/Minus zoom (50–200%) with compact footer slider, auto-reset on page switch, hidden on non-table pages
- **Per-model product colours** — right-click any model row in the matrix to select which colours (Black, Silver, Gold…) per model; same toggle UI in settings Admin → Part Types → Model Colors section (double-click to edit)
- **Series separators** — thin visible divider lines between model series groups (X-series, 11-series, A0x, A1x, S2x) for easier reading
- **Collapsible matrix toolbar** — inventory-style clickable section header to hide/show brand filter and legend chips
- **Auto-fit model column** — frozen model column width auto-sizes to the longest model name
- **Live clock** — footer timestamp updates every second automatically
- **Professional splash screen** — geometric inventory cube icon drawn with QPainter, dynamic version badge from `APP_VERSION`, rounded card with emerald glow
- **Custom app icon** — isometric cube icon as `.ico` (multi-resolution 16–256px) and `.png`, used for window, taskbar, installer, and README
- **Full actions toolbar** — New Product, Export CSV, Import CSV, Report, Bulk Edit, Refresh buttons in inventory dashboard
- **Model reorder** — move up/down buttons in Admin → Models panel (same style as part types)
- **Per-model colours in settings** — Admin → Part Types → Model Colors card shows all models with their colour overrides; double-click to edit
- **Import CSV** — toolbar button opens file picker and imports inventory data directly

### Fixed
- **Theme toggle persistence** — toggling theme now saves to database; closing admin no longer reverts to old theme
- **Theme toggle UI** — sidebar, header, footer, matrix legend chips, inventory section headers all update correctly
- **Zoom separators** — separator rows stay at fixed 3px height during zoom
- **Worker pool crash** — wrapped signal emit in try/except to handle widget deletion during background tasks
- **QFont warning** — suppressed harmless `QFont::setPointSize` Qt warning via `qInstallMessageHandler`
- **UAC rejection** — `launch_installer()` returns `bool`; app only quits if UAC was accepted
- **Download cancel** — cancel button on update download progress dialog
- **Installer cache** — downloaded installer stored in persistent `%LOCALAPPDATA%` cache instead of temp dir
- **Cached installer reuse** — if installer already downloaded and SHA256 matches, skip re-download
- **CSV export** — now opens file save dialog instead of crashing on missing `file_path` argument
- **Quick action undo** — +1/-1 buttons now show undo toast (same as full stock dialog)
- **Quick action detail sync** — +1/-1 updates the detail bar instantly (stock count, status badge)
- **Model reorder** — fixed `reorder()` to preserve brand-specific sort_order base; `get_all()` now sorts by `sort_order` instead of re-sorting naturally
- **Per-model colour removal** — unselected colours now properly deleted from ALL part types, not just one

### Changed
- **Schema V14** — 5 new performance indexes on `inventory_items` (active, stock, part_type_id, model+pt, model+pt+color)
- **Connection pooling** — thread-local cached connections instead of new `sqlite3.connect()` per query
- **SQLite optimised** — `synchronous=NORMAL`, `cache_size=20MB`, `temp_store=MEMORY` pragmas
- **Batch inserts** — `_ensure_all_entries()` uses `executemany()` instead of per-row INSERT (10-50x faster)
- **Deferred health checks** — `run_startup_checks()` moved to background thread after 2s delay
- **Lazy theme loading** — only generates QSS for active theme at startup, not all 4
- **Matrix rendering** — pre-indexed item_map for O(1) model lookup; `setUpdatesEnabled(False)` during bulk cell creation
- **Slim dropdown style** — all QComboBox across the app use minimal bottom-line style (transparent, no box border)
- **Compact filter bar** — 26px controls, no container frame, category inline, icon-only reset button
- **Compact actions bar** — 36px toolbar with 6 action buttons, keyboard hints, themed styles
- **Version unified** — `main.py` and splash screen import `APP_VERSION` from `version.py`
- **Pre-release version parsing** — strips `-rc1`, `-beta` suffixes before comparing
- **Manifest validation** — validates URL format, SHA256 hex, version parseability
- **min_version enforcement** — `check_for_update()` respects `min_version` field
- **CI/CD pipeline** — release branch → PR → auto-merge to main with retry
- **CI version stamping** — auto-stamps `version.py`, `file_version_info.txt`, `.iss`, `README.md` badge

---

## [2.3.3] - 2026-04-11

### Fixed
- German button and column header text no longer truncated (removed hard pixel width caps)
- Product name column now stretches to fill available space in inventory list
- Collapsible inventory sections (Overview, Filters, Selected Item) give table more space when hidden

### Changed
- Release workflow now auto-extracts changelog entry and publishes it to GitHub Release

---

## [2.3.2] - 2026-04-11

### Fixed
- Update manifest URL corrected — auto-update banner now works for all users
- GitHub Actions workflow now pushes manifest to `main` branch so the app can find it

---

## [2.3.1] - 2026-04-11

### Fixed
- German text no longer truncated in matrix table column headers (Stamm-Zahl, Best-Bung, Bestand, Bestellung)
- German button labels no longer clipped in the detail bar (Anpassen → was "Anpass", Bearbeiten → was "Bearbei")
- Removed `setMaximumWidth` caps on all action buttons in the product detail bar

### Changed
- Product name column is now left-aligned and always fills available table width
- Column widths applied via `Interactive` mode — a long barcode no longer steals space from the name column
- Inventory page sections (Overview, Filters, Selected Item) are now individually collapsible — hiding a section gives that space to the product table
- Product table list expands to fill all freed space when sections are collapsed

---

## [2.3.0] - 2026-04-06

### Added
- Full business module suite: Suppliers, Purchase Orders, Sales, Returns, Customers
- Price Lists with margin analysis
- Audit Log with full transaction history
- Analytics dashboard with charts and KPIs
- Multi-location inventory support
- Async background engine with worker pool
- Controller architecture for clean separation of concerns
- Web server interface (Flask) for remote access
- Auto-update system with in-app banner and one-click installer download

### Changed
- Complete UI overhaul with PRO_DARK and PRO_LIGHT themes
- Matrix inventory view with per-model stock tracking
- Sidebar navigation with collapsible sections

---

## [2.2.0] - 2026-02-15

### Added
- Barcode scanning and generation
- RTL layout support for Arabic language
- German (DE) full translation

### Fixed
- Database migration stability improvements

---

## [2.1.0] - 2026-01-10

### Added
- Category-based matrix view for phone repair shops
- Theme system with DARK / LIGHT / PRO_DARK / PRO_LIGHT presets
- i18n framework with EN / DE / AR support

---

## [2.0.0] - 2025-12-01

### Added
- Initial public release
- SQLite inventory with full CRUD
- PyInstaller Windows build
