# Changelog

All notable changes to **Stock Manager Pro** are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

> Add your next changes here before tagging a release.

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
