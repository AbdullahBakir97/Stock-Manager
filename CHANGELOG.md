# Changelog

All notable changes to **Stock Manager Pro** are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

> Add your next changes here before tagging a release.

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
