# Changelog

All notable changes to **Stock Manager Pro** are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

## [2.3.10] - 2026-04-20


> Add your next changes here before tagging a release.

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

### Performance
- **Startup freeze fixed** — `rebuild_matrix_tabs()` is now deferred via `QTimer.singleShot(0, …)` so the main window paints and becomes interactive immediately after the splash, instead of blocking for several seconds while every matrix tab runs its first DB query synchronously.
- **Settings-close freeze fixed** — the whole post-admin-dialog chain (`ensure_matrix_entries` → `rebuild_matrix_tabs` → `apply_theme_to_matrix_tabs` → `_retranslate` → `nav_ctrl.go(saved)`) is now deferred to the next event-loop tick. Closing settings returns control to the user instantly; the rebuild runs on the next frame.
- **MatrixTab.refresh()** refactored to dispatch every DB query through `worker_pool.POOL.submit(…)`. In all-brands mode this replaced up to 12 synchronous `_item_repo.get_matrix_items()` / `_model_repo.get_all()` hits per refresh with one pooled async fetch; the UI thread no longer touches the DB during brand-combo changes, cost-toggle flips, or post-edit refreshes.
- `_add_brand_section` / `_reload_brand_container` accept pre-fetched `models=` / `item_map=` kwargs so the worker can feed every brand section at once (fallback to sync is preserved for legacy callers).

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
