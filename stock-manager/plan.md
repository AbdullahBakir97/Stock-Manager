STOCK MANAGER PRO
Development Plan & Gap Analysis

──────────────────────────────────────────────────

Version 1.0  |  April 02, 2026  |  Prepared by Claude AI

Table of Contents
1.  Executive Summary
2.  Current State Assessment
3.  Feature Audit: What Has Been Done
4.  Gap Analysis: What Is Missing
5.  Technical Debt & Code Quality
6.  Improvement Recommendations
7.  New Feature Suggestions
8.  Prioritized Roadmap
9.  Estimated Effort & Timeline
10.  Appendix: Architecture Diagram

1. Executive Summary
Stock Manager Pro is a well-architected desktop inventory management application built with Python (PyQt6) and SQLite. The app is at version 1.0.0 and has successfully delivered core inventory features including product CRUD, stock operations, barcode scanning, multilingual support (EN/DE/AR with RTL), and a professional 4-theme UI system.
This document provides a comprehensive audit of the current implementation, identifies gaps between the README specifications and the actual codebase, catalogues technical debt, and presents a prioritized roadmap of improvements and new features.
Key Findings at a Glance
Metric
Value
Total Python Modules
52 files across 7 layers
Lines of Code
~10,785 lines
Database Schema Version
V5 (5 migrations)
Features Fully Implemented
14 major features
Features Partially Done
3 areas (Phase C refactoring, data migration, export)
Missing Features
10+ potential additions identified
Technical Debt Items
6 items requiring attention


2. Current State Assessment
2.1 Technology Stack
Layer
Technology
Status
UI Framework
PyQt6 6.10.2
Excellent
Database
SQLite 3 (stdlib)
Solid
Barcode
python-barcode 0.16.1
Good
PDF Export
fpdf2 2.8.7 + PyMuPDF 1.27
Good
Image Processing
Pillow 12.1.1
Good
Packaging
PyInstaller 6.19.0
Mature

2.2 Architecture Quality
The codebase follows a clean Repository + Service pattern with 7 well-separated layers: Core, Models, Repositories, Services, UI Components, Dialogs, and Pages. This is a mature architecture for a desktop application of this scale.
Aspect
Rating
Notes
Separation of Concerns
Strong
Clean layer boundaries between UI, services, and data
Code Organization
Strong
52 modules logically organized into 7 packages
Database Access
Good
Repository pattern with base class and connection management
Migration System
Good
5-version migration chain with forward compatibility
UI Architecture
Needs Work
main_window.py at 2,263 lines needs decomposition
Testing
Missing
No unit tests or integration tests found


3. Feature Audit: What Has Been Done
Below is a complete inventory of all implemented features mapped against the README specifications and discovered through code analysis.
3.1 Core Inventory Management
Status
Feature
Details
DONE
Add / Edit / Delete products
Full CRUD with brand, type, color, barcode, min stock
DONE
Matrix inventory
Phone model x Part type grid for displays, batteries, cases
DONE
Stock In / Out / Adjust
All 3 operations with validation, notes, and audit trail
DONE
Barcode scanner support
USB scanner intercept with Code39/Code128 format
DONE
Low stock alerts
Configurable per-product threshold with status badges
DONE
Transaction history
Complete audit log, paginated to 500 records
DONE
Search & filter
Cross-inventory search by name, barcode, model, part type

3.2 Barcode & Quick Scan
Status
Feature
Details
DONE
Barcode generation
Automatic Code39/Code128 with PDF export
DONE
PDF barcode sheets
Scoped by category, model, or part type with command barcodes
DONE
Barcode assignment
UI for assigning barcodes to inventory items
DONE
Quick Scan mode
3-command workflow: INSERT/TAKEOUT → scan items → CONFIRM
DONE
Batch commit
Pending items display with qty increments and stock prediction
DONE
Custom command barcodes
Configurable CMD-INSERT, CMD-TAKEOUT, CMD-CONFIRM

3.3 Admin & Configuration
Status
Feature
Details
DONE
Setup wizard
3-page first-run wizard (language, shop config, data seeding)
DONE
Admin panel (5 tabs)
Shop settings, categories, part types, models, scan config
DONE
PIN-gated admin
Optional admin PIN protection
DONE
Logo upload
Custom shop logo support
DONE
Currency config
Symbol with prefix/suffix position

3.4 UI & Theming
Status
Feature
Details
DONE
4 theme presets
Dark, Light, Pro Dark, Pro Light with live switching
DONE
Multilingual (EN/DE/AR)
100+ translated strings with live switching and RTL
DONE
Sidebar navigation
Professional layout with gradient backgrounds
DONE
Dashboard cards
Total products, total units, low stock, out-of-stock, value
DONE
Status badges
Color-coded OK / LOW / CRITICAL / OUT indicators
DONE
Keyboard shortcuts
Ctrl+N, Ctrl+I, Ctrl+O, Ctrl+F, Del, F5


4. Gap Analysis: What Is Missing
The following gaps were identified by comparing the README specifications, analyzing the codebase for incomplete features, and identifying common inventory management capabilities that users would expect.
4.1 Partially Implemented Features
Status
Feature
Description
Priority
PARTIAL
Phase C UI Refactoring
Products tab still uses legacy ProductDialog instead of unified InventoryItem. Compatibility aliases (product_stock_in, product_stock_out) bridge old and new API.
Medium
PARTIAL
Database Consolidation
V4 introduced unified inventory_items table, but legacy products and stock_entries tables still exist. Both old and new tables receive writes (redundant).
High
PARTIAL
Data Export
Only barcode PDF export works. No CSV/Excel export for inventory data, no database backup/restore, no bulk import.
High

4.2 Completely Missing Features
Status
Feature
Impact
Priority
MISSING
CSV / Excel Import
No way to bulk-import products from spreadsheets. Users must add items one by one.
P0
MISSING
Inventory Export (CSV/Excel)
Cannot export current inventory to spreadsheet format for reporting or backup.
P0
MISSING
Database Backup & Restore
No built-in backup mechanism. Users risk data loss if the SQLite file is corrupted.
P0
MISSING
Unit / Integration Tests
Zero test coverage. No pytest, no test directory, no CI pipeline.
P1
MISSING
Print Support
No direct printing of inventory lists, transaction reports, or barcode sheets.
P1
MISSING
Inventory Reports
No stock value report, reorder report, movement summary, or profit/loss tracking.
P1
MISSING
Undo / Transaction Rollback
Stock operations are permanent. No undo for accidental stock-out or wrong quantity.
P2
MISSING
User Manual / Help System
No in-app help, tooltips, or user documentation beyond the README.
P2
MISSING
Auto-Update Mechanism
No way to check for or install app updates.
P3
MISSING
Logging / Error Reporting
No application logging. Errors may go unreported in production builds.
P1


5. Technical Debt & Code Quality
5.1 High-Priority Debt
main_window.py Monolith
Problem: At 2,263 lines, the main window file handles too many concerns: sidebar, tabs, toolbar, dashboard, product table, detail panel, and all navigation logic. This makes maintenance difficult and increases the risk of regressions.
Solution: Extract into separate widget classes: SidebarWidget, DashboardWidget, ProductTableWidget, DetailPanelWidget. Target: no file over 500 lines.
Dual-Write to Legacy Tables
Problem: Database writes go to both legacy tables (products, stock_entries, stock_transactions) and new unified tables (inventory_items, inventory_transactions). This doubles write operations and creates data consistency risks.
Solution: Complete migration to unified tables. Drop legacy tables in V6 migration. Remove all compatibility aliases in repositories and services.
Zero Test Coverage
Problem: No tests exist for any layer: services, repositories, UI, or integration. Any refactoring carries high regression risk.
Solution: Add pytest with fixtures for SQLite in-memory DB. Target 80%+ coverage on services and repositories. Add basic UI smoke tests with pytest-qt.
No Application Logging
Problem: Production builds have no logging infrastructure. Errors are silently swallowed, making debugging impossible for end users.
Solution: Add Python logging module with rotating file handler. Log to %LOCALAPPDATA%\StockPro\StockManagerPro\logs\.
Hardcoded Demo Data
Problem: Demo categories and phone models in demo_data.py are English-first. Translations are incomplete for demo content.
Solution: Make demo data fully trilingual (EN/DE/AR) and allow customization via admin panel.
No Error Boundaries in UI
Problem: Unhandled exceptions in dialog callbacks or service calls can crash the application.
Solution: Add try/except wrappers around service calls in UI layer. Show user-friendly error dialogs instead of crashes. Log all exceptions.

6. Improvement Recommendations
These improvements target existing features that work but could be significantly better.
Area
Improvement
Description
Effort
UI/UX
Enhanced Dashboard
Add sparkline charts for stock trends (7-day movement), a "recently modified" section, and quick-action buttons for common operations. The current dashboard is functional but static.
Quick Win
UI/UX
Table Column Customization
Let users show/hide, reorder, and resize table columns. Persist preferences per user. Currently all columns are fixed.
Medium
Performance
Lazy Loading for Large Inventories
The product table loads all items at once. For inventories with 10,000+ items, implement virtual scrolling and paginated data loading.
Medium
Performance
Database Connection Pooling
Each repository creates its own connection. Implement a shared connection pool to reduce overhead and enable write batching.
Quick Win
Data
Enhanced Search
Add advanced filters: search by date range, stock status (low/out), category, price range. Support combined filters.
Medium
Data
Barcode Format Options
Currently limited to Code39/Code128. Add QR code support and EAN-13 for retail. Allow users to choose format per product.
Medium
i18n
Complete Arabic RTL
While RTL layout is supported, audit all dialogs and popups for proper RTL alignment. Ensure number formatting respects locale.
Quick Win
Admin
Data Validation Rules
Add configurable validation: required fields, barcode uniqueness enforcement, stock quantity limits, and price range validation.
Medium
Admin
Activity Log for Admin Actions
Track admin changes: category edits, part type deletions, model modifications. Currently only stock operations are logged.
Quick Win
Build
Installer (NSIS/Inno Setup)
Replace the zip distribution with a proper Windows installer. Add Start Menu shortcuts, uninstaller, and optional desktop icon.
Major


7. New Feature Suggestions
These are net-new features that would significantly increase the value of Stock Manager Pro for its target users (small-to-medium phone repair shops).
7.1 Tier 1 — High Impact, Near Term
Supplier Management
Track suppliers per product. Store supplier name, contact, lead time, and cost price. Enable purchase order generation and supplier performance tracking.
Implementation: New supplier table, supplier_products junction table, UI tab, and PO generation dialog.
Customer Sales Module
Basic point-of-sale: record sales transactions with customer name (optional), calculate total, print receipt. Track revenue alongside stock movements.
Implementation: New sales_transactions table, SalesDialog with item picker, receipt template (PDF/thermal).
Inventory Reporting Suite
Stock Valuation Report (cost vs. retail), Movement Report (top movers, dead stock), Reorder Report (items below minimum), and Monthly Summary. Export all to PDF/Excel.
Implementation: New ReportService, report templates, chart generation with matplotlib or PyQtChart.
Automatic Database Backup
Scheduled local backups (daily/weekly) with rotation. Manual backup/restore from Admin panel. Backup to external drive option. One-click restore with confirmation.
Implementation: BackupService with shutil, scheduler integration, AdminPanel backup tab.
7.2 Tier 2 — Medium Impact, Medium Term
Multi-Location / Warehouse Support
Track inventory across multiple locations (shop, warehouse, repair bench). Transfer stock between locations with full audit trail.
Expiry / Warranty Date Tracking
Add optional expiry/warranty date to products. Alert when items are nearing expiry. Useful for adhesives, batteries, and warranty parts.
Product Images
Attach photos to products. Show thumbnail in product table and full image in detail panel. Store in local folder alongside database.
Label / Receipt Printing
Print product labels (barcode + name + price) on label printers (Zebra/DYMO). Print receipts for stock operations on thermal printers.
Dashboard Analytics
Interactive charts: stock level trends, daily movement volume, category distribution, most active products. Use PyQtChart or matplotlib embedded in Qt.
7.3 Tier 3 — Future Vision
Feature
Description
Cloud Sync (Optional)
Optional sync to cloud storage (Google Drive / Dropbox) for multi-device access. End-to-end encrypted.
Web Dashboard
Read-only web interface for checking stock levels remotely. Flask/FastAPI micro-server running locally.
Mobile Companion App
Simple mobile app for quick stock checks and barcode scanning on the go. Could be a PWA.
Multi-User with Roles
Role-based access: Admin (full access), Manager (stock ops + reports), Staff (stock in/out only).
API Integration
REST API for integration with e-commerce platforms (Shopify, WooCommerce) for automatic stock sync.


8. Prioritized Roadmap
The following roadmap organizes all work items into 4 phases, ordered by business impact, technical dependency, and effort.
Phase 1: Stabilize & Complete (v1.1) — 4–6 weeks
#
Task
Details
Priority
1.1
Complete Phase C refactoring
Remove all compatibility aliases, unify on InventoryItem
P0
1.2
Drop legacy database tables
V6 migration: remove products, stock_entries, legacy transactions
P0
1.3
Add application logging
Python logging with rotating file handler + error boundaries
P0
1.4
CSV/Excel export
Export inventory and transactions to CSV and XLSX formats
P0
1.5
CSV/Excel import
Bulk import products from spreadsheet with mapping wizard
P0
1.6
Database backup & restore
Manual backup from Admin panel + one-click restore
P0
1.7
Basic test suite
pytest for services + repositories, 60%+ coverage target
P1

Phase 2: Enhance & Polish (v1.5) — 6–8 weeks
#
Task
Details
Priority
2.1
Decompose main_window.py
Extract into SidebarWidget, DashboardWidget, etc.
P1
2.2
Inventory reporting suite
Valuation, movement, reorder, and monthly summary reports
P1
2.3
Enhanced dashboard
Sparkline charts, recent activity, quick actions
P1
2.4
Print support
Print inventory lists, transaction reports, barcode sheets
P1
2.5
Advanced search & filters
Date range, status, category, price range filters
P2
2.6
Product images
Photo attachment with thumbnail display
P2
2.7
Windows installer
NSIS or Inno Setup with Start Menu integration
P2
2.8
In-app help system
Tooltips, contextual help, and embedded user guide
P2

Phase 3: Expand Features (v2.0) — 8–12 weeks
#
Task
Details
Priority
3.1
Supplier management
Supplier database, cost prices, purchase orders
P2
3.2
Customer sales module
Basic POS, sales transactions, receipt printing
P2
3.3
Multi-location support
Track inventory across shop, warehouse, bench
P2
3.4
Dashboard analytics
Interactive charts with PyQtChart
P2
3.5
Label / thermal printing
Barcode labels on Zebra/DYMO, thermal receipts
P3
3.6
Expiry / warranty tracking
Date fields with expiry alerts
P3
3.7
Automatic scheduled backups
Daily/weekly with rotation and external drive option
P3

Phase 4: Future Vision (v3.0+)
#
Task
Details
4.1
Multi-user with roles
Admin, Manager, Staff access levels
4.2
Cloud sync (optional)
Google Drive / Dropbox backup with E2E encryption
4.3
Web dashboard
Read-only Flask/FastAPI interface for remote access
4.4
Mobile companion
PWA for quick stock checks and barcode scanning
4.5
E-commerce API
Shopify / WooCommerce stock sync integration
4.6
Auto-update system
Check for updates and in-app installation


9. Estimated Effort & Timeline
Effort estimates assume a single developer working part-time (~20 hours/week). Adjust proportionally for team size and availability.
Phase
Duration
Effort
Scope
Phase 1: Stabilize
4–6 weeks
80–120 hours
Critical bug-fix and foundation work
Phase 2: Enhance
6–8 weeks
120–160 hours
Polish, reporting, and UX improvements
Phase 3: Expand
8–12 weeks
160–240 hours
Major new features (suppliers, sales, analytics)
Phase 4: Vision
12+ weeks
240+ hours
Cloud, web, mobile, multi-user
TOTAL
30–38 weeks
600–760 hours
Full roadmap completion


10. Appendix: Architecture Overview
Current Layer Architecture
Layer
Modules
Responsibility
Layer 1
UI (main_window, dialogs, pages, tabs)
User interaction and display
Layer 2
Components (matrix_widget, delegates)
Reusable UI components
Layer 3
Services (stock, alert, barcode_gen, scan_session)
Business logic and orchestration
Layer 4
Repositories (product, item, category, model, transaction)
Data access and queries
Layer 5
Models (product, item, phone_model, category, transaction)
Data transfer objects
Layer 6
Core (database, config, theme, i18n, colors)
Infrastructure and utilities
Layer 7
Database (SQLite with V1–V5 migrations)
Persistence layer

Recommended Target Architecture (Post Phase 2)
After completing Phases 1 and 2, the architecture should consolidate into a cleaner structure: a single unified data model (InventoryItem), no legacy compatibility wrappers, main_window decomposed into focused widgets under 500 lines each, comprehensive logging throughout, and a test suite covering all service and repository layers.
File Structure After Refactoring
app/
├── core/          (database, config, i18n, theme, logging)
├── models/        (inventory_item, transaction, category — no legacy wrappers)
├── repositories/  (item_repo, category_repo, model_repo, transaction_repo)
├── services/      (stock, alert, barcode, scan, report, backup, import_export)
├── ui/
│   ├── widgets/   (sidebar, dashboard, product_table, detail_panel, search_bar)
│   ├── dialogs/   (product, stock_op, admin, import_wizard, report_viewer)
│   ├── pages/     (barcode_gen, reports, quick_scan)
│   └── tabs/      (matrix_tab, transactions_tab)
└── tests/         (test_services/, test_repos/, test_ui/, conftest.py)

──────────────────────────────────────────────────
End of Document  |  Generated April 02, 2026
