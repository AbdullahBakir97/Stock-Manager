<p align="center">
  <img src="files/img/logo.png" width="120" alt="Stock Manager Pro Logo" />
</p>

<h1 align="center">Stock Manager Pro v2</h1>

<p align="center">
  <strong>A professional, modular desktop inventory management application for Windows.</strong><br/>
  Built with Python and PyQt6 — fast, offline, multilingual, and enterprise-ready.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Windows%2010%2F11-0078D4?style=flat-square&logo=windows" alt="Windows 10/11" />
  <img src="https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/PyQt6-6.x-41CD52?style=flat-square&logo=qt" alt="PyQt6 6.x" />
  <img src="https://img.shields.io/badge/license-MIT-brightgreen?style=flat-square" alt="MIT License" />
  <img src="https://img.shields.io/badge/version-2.0.0-blue?style=flat-square" alt="Version 2.0.0" />
  <img src="https://img.shields.io/badge/status-Active%20Development-orange?style=flat-square" alt="Active Development" />
</p>

---

## 📋 Table of Contents

- [Features](#features)
- [What's New in v2](#whats-new-in-v2)
- [Screenshots](#screenshots)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Build Instructions](#build-instructions)
- [Project Architecture](#project-architecture)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Admin Panel Guide](#admin-panel-guide)
- [Barcode Workflow](#barcode-workflow)
- [PDF Reports](#pdf-reports)
- [Data & Privacy](#data--privacy)
- [Contributing](#contributing)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## ✨ Features

### Core Inventory Management
- **Full inventory management** — Add, edit, delete products with detailed attributes (brand, type, color, barcode)
- **Stock operations** — Stock In, Stock Out, and manual Adjust with timestamped notes and complete history
- **Low stock alerts** — Configurable threshold per product with real-time dashboard highlighting
- **Transaction history** — Complete audit log of every stock movement with user tracking and timestamps
- **Multi-location support** — Manage stock across multiple categories and product types

### Barcode Management (New in v2)
- **Barcode scanning** — Plug in any USB scanner; input is intercepted automatically
- **Barcode generation** — Create and print custom barcodes for all products using industry-standard formats
- **Barcode assignment** — Dedicated dialog for assigning/reassigning barcodes to products
- **Batch barcode operations** — Generate multiple barcodes at once for printing

### Matrix Operations (New in v2)
- **Grid-based view** — Visual matrix display for bulk stock operations
- **Bulk updates** — Modify multiple products simultaneously in spreadsheet-like interface
- **Data export** — Export matrix data for analysis in external tools

### Reporting & Export (New in v2)
- **PDF report generation** — Create professional reports with formatting, tables, and summaries
- **Export to PDF** — Generate detailed inventory reports with custom date ranges
- **Print-ready formatting** — Professional layouts suitable for printing or archival

### Admin Panel (New in v2)
- **Shop settings** — Configure company name, location, currency, and other global preferences
- **Category management** — Create, edit, delete product categories
- **Part types** — Manage product types and classifications
- **Models management** — Define product models and variants
- **Color picker** — Professional color selection interface with preset colors
- **Scan settings** — Configure barcode scanner behavior and sensitivity
- **User roles** — Admin and operator role management

### User Experience
- **Multilingual support** — English, German (DE), Arabic (AR) with live switching and RTL layout support
- **Offline & private** — All data stored locally in SQLite; no internet required
- **Dark/Light themes** — Professional UI themes optimized for desktop use
- **Setup wizard** — Guided initial configuration for new installations
- **Search & filtering** — Advanced search with multiple filter criteria

---

## 🎯 What's New in v2

### Architecture & Code Quality
- **Service-oriented architecture** — Cleaner separation of concerns with dedicated services (StockService, ScanService, AlertService)
- **Repository pattern** — Abstracted data access layer for better testability and maintainability
- **Model layer** — Domain objects (Product, Item, Category, Transaction, ScanSession) for type safety
- **Modular UI components** — Reusable components with custom Qt delegates for performance

### New Capabilities
- ✅ **Barcode generation** — Not just scanning; now generate and print barcodes in bulk
- ✅ **PDF report exports** — Professional report generation with customizable templates
- ✅ **Matrix/grid operations** — Bulk stock management in spreadsheet-like view
- ✅ **Enhanced admin panel** — Comprehensive settings for shop, categories, models, and scanning
- ✅ **Scan sessions** — Organized scanning workflows for efficient stock counting
- ✅ **Color picker widget** — Professional color selection with presets and custom colors
- ✅ **Setup wizard** — Interactive first-time setup for new users

### Performance Improvements
- **Optimized data loading** — Lazy loading for large product catalogs
- **Custom Qt delegates** — Efficient rendering of large datasets
- **Caching** — Smart caching of frequently accessed data
- **Async operations** — Non-blocking long-running operations

---

## 📸 Screenshots

![Dashboard Screenshot](files/img/screenshot.png)

| Feature | Screenshot |
|---------|-----------|
| **Dashboard** | ![Dashboard](files/img/screenshot2.png) |
| **Stock Operation** | ![Stock Op](files/img/screenshot3.png) |
| **Low Stock Alerts** | ![Alerts](files/img/screenshot4.png) |

---

## 🖥️ System Requirements

| Requirement | Specification |
|-------------|---------------|
| **OS** | Windows 10 or Windows 11 |
| **Python** | 3.11 or higher (for development) |
| **RAM** | 512 MB minimum, 2 GB recommended |
| **Disk Space** | 200 MB for application + database storage |
| **Admin Rights** | Not required |

---

## 📦 Installation

### Option A — Pre-built Executable (Recommended)

1. Download `StockManagerPro.zip` from the [latest release](../../releases/latest)
2. Extract the zip to any location (e.g., `C:\Apps\StockManagerPro\`)
3. Run `StockManagerPro.exe`

**Data Location:** `%LOCALAPPDATA%\StockPro\StockManagerPro\stock_manager.db`

No installation wizard required. No admin rights needed.

### Option B — Run from Source

**Prerequisites:**
- Python 3.11+
- Windows 10/11
- Git

**Steps:**

```bash
# Clone the repository
git clone https://github.com/AbdullahBakir97/Stock-manager.git
cd Stock-manager

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
cd files
python main.py
```

---

## 🚀 Quick Start

### First-Time Setup

1. **Launch the application** — Run `StockManagerPro.exe`
2. **Complete the Setup Wizard** — Configure your shop name, location, and preferences
3. **Add categories** — Go to Admin Panel → Categories to create product categories
4. **Add product types** — Admin Panel → Part Types to define product classifications
5. **Create your first product** — Press `Ctrl+N` or use the toolbar button
6. **Test barcode scanner** — Plug in your USB barcode scanner and scan a product barcode

### Common Tasks

| Task | How To |
|------|--------|
| Add a product | Press `Ctrl+N` or click **New Product** button |
| Record stock in | Select product, press `Ctrl+I`, enter quantity |
| Record stock out | Select product, press `Ctrl+O`, enter quantity |
| Generate barcode | Right-click product → Generate Barcode |
| Export PDF report | File → Export Report or press `Ctrl+P` |
| Configure admin settings | File → Admin Settings or press `Ctrl+Alt+A` |
| Switch language | Settings → Language (English / Deutsch / العربية) |

---

## 🔨 Build Instructions

### Build the Executable

```bash
# Navigate to project root
cd Stock-manager

# Run PyInstaller
pyinstaller StockManagerPro.spec --noconfirm

# Output location
# dist/StockManagerPro/StockManagerPro.exe
```

### Build Requirements

```bash
pip install PyInstaller>=6.19.0
```

The `StockManagerPro.spec` file handles:
- Bundling all PyQt6 dependencies
- Including barcode and PDF libraries
- Embedding application icons and resources
- Optimizing binary size

**Build time:** ~2-5 minutes (first build may take longer)
**Output size:** ~150-200 MB (includes Python runtime)

---

## 🏗️ Project Architecture

### Layered Architecture

```
┌─────────────────────────────────────┐
│        UI Layer (PyQt6)             │
│  (Main Window, Dialogs, Tabs)       │
├─────────────────────────────────────┤
│      Service Layer                  │
│  (StockService, ScanService,        │
│   AlertService, ReportService)      │
├─────────────────────────────────────┤
│    Repository Layer                 │
│  (ProductRepo, TransactionRepo,     │
│   ItemRepo, CategoryRepo)           │
├─────────────────────────────────────┤
│      Model Layer                    │
│  (Domain Objects: Product, Item,    │
│   Category, Transaction, etc.)      │
├─────────────────────────────────────┤
│      Data Layer (SQLite)            │
│  (Database abstraction)             │
└─────────────────────────────────────┘
```

### Design Patterns Used

- **Repository Pattern** — Data access abstraction
- **Service Locator** — Centralized service management
- **Singleton** — Database and configuration instances
- **Observer** — Real-time UI updates
- **Factory** — Dialog and component creation
- **Delegate** — Custom table cell rendering

---

## 📁 Project Structure

```
Stock-manager/
├── src/
│   ├── files/
│   │   ├── main.py                    # Application entry point
│   │   ├── StockManagerPro.spec       # PyInstaller build configuration
│   │   │
│   │   ├── app/
│   │   │   ├── core/                  # Core utilities & configuration
│   │   │   │   ├── __init__.py
│   │   │   │   ├── colors.py          # Product color palette
│   │   │   │   ├── config.py          # Application configuration
│   │   │   │   ├── database.py        # SQLite database layer
│   │   │   │   ├── demo_data.py       # Sample data for demo mode
│   │   │   │   ├── i18n.py            # Internationalization (EN/DE/AR)
│   │   │   │   ├── icon_utils.py      # Icon loading utilities
│   │   │   │   ├── scan_config.py     # Barcode scanner configuration
│   │   │   │   └── theme.py           # Qt stylesheets & design tokens
│   │   │   │
│   │   │   ├── models/                # Domain models
│   │   │   │   ├── __init__.py
│   │   │   │   ├── category.py        # Category model
│   │   │   │   ├── item.py            # Item/SKU model
│   │   │   │   ├── phone_model.py     # Product model
│   │   │   │   ├── product.py         # Product model
│   │   │   │   ├── scan_session.py    # Scan session model
│   │   │   │   └── transaction.py     # Stock transaction model
│   │   │   │
│   │   │   ├── repositories/          # Data access layer
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py            # Base repository class
│   │   │   │   ├── category_repo.py   # Category repository
│   │   │   │   ├── item_repo.py       # Item repository
│   │   │   │   ├── model_repo.py      # Model repository
│   │   │   │   ├── product_repo.py    # Product repository
│   │   │   │   └── transaction_repo.py # Transaction repository
│   │   │   │
│   │   │   ├── services/              # Business logic layer
│   │   │   │   ├── __init__.py
│   │   │   │   ├── alert_service.py   # Low stock alerts
│   │   │   │   ├── scan_session_service.py # Scan session management
│   │   │   │   ├── stock_service.py   # Stock operations (In/Out/Adjust)
│   │   │   │   ├── report_service.py  # PDF report generation
│   │   │   │   └── barcode_service.py # Barcode generation & scanning
│   │   │   │
│   │   │   ├── ui/                    # User interface
│   │   │   │   ├── __init__.py
│   │   │   │   ├── main_window.py     # Main application window
│   │   │   │   ├── delegates.py       # Custom Qt delegates for tables
│   │   │   │   │
│   │   │   │   ├── components/        # Reusable UI components
│   │   │   │   │   └── matrix_widget.py # Matrix/grid widget
│   │   │   │   │
│   │   │   │   ├── tabs/              # Main window tabs
│   │   │   │   │   ├── base_tab.py    # Base tab class
│   │   │   │   │   └── matrix_tab.py  # Matrix operations tab
│   │   │   │   │
│   │   │   │   └── dialogs/           # Modal dialogs
│   │   │   │       ├── product_dialogs.py      # Product CRUD dialogs
│   │   │   │       ├── matrix_dialogs.py       # Matrix operation dialogs
│   │   │   │       ├── setup_wizard.py         # First-time setup wizard
│   │   │   │       ├── barcode_assign_dialog.py # Barcode assignment
│   │   │   │       │
│   │   │   │       └── admin/                  # Admin panel dialogs
│   │   │   │           ├── admin_dialog.py           # Main admin panel
│   │   │   │           ├── shop_settings_panel.py    # Shop configuration
│   │   │   │           ├── categories_panel.py       # Category management
│   │   │   │           ├── part_types_panel.py       # Part type management
│   │   │   │           ├── models_panel.py           # Model management
│   │   │   │           ├── color_picker_widget.py    # Color selection
│   │   │   │           └── scan_settings_panel.py    # Scanner configuration
│   │   │   │
│   │   │   └── resources/
│   │   │       ├── img/
│   │   │       │   ├── icon_logo.ico          # Application icon
│   │   │       │   ├── logo.png               # Logo image
│   │   │       │   └── icons/                 # Toolbar & menu icons
│   │   │       └── styles/
│   │   │           └── default.qss            # Qt stylesheets
│   │   │
│   │   └── img/                       # Image assets
│   │       ├── logo.png
│   │       ├── screenshot.png
│   │       ├── screenshot2.png
│   │       ├── screenshot3.png
│   │       └── screenshot4.png
│   │
│   └── .gitignore
│
├── requirements.txt                   # Python dependencies
├── LICENSE                           # MIT License
└── README.md                         # This file
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **UI Framework** | [PyQt6 6.10+](https://www.riverbankcomputing.com/software/pyqt/) | Cross-platform desktop GUI |
| **Database** | SQLite 3 | Local relational database |
| **PDF Generation** | [fpdf2 2.8+](https://py-pdf.github.io/fpdf2/) + [PyMuPDF 1.27+](https://pymupdf.readthedocs.io/) | Report generation |
| **Barcode** | [python-barcode 0.16+](https://python-barcode.readthedocs.io/) | Barcode generation (Code128, EAN, etc.) |
| **Image Processing** | [Pillow 12.1+](https://python-pillow.org/) | Image handling for logos and icons |
| **Security** | [defusedxml 0.7+](https://github.com/tiran/defusedxml) | Safe XML parsing |
| **Packaging** | [PyInstaller 6.19+](https://pyinstaller.org/) | Windows executable creation |
| **Development** | Python 3.11+ | Programming language |

### Key Dependencies

```
PyQt6==6.10.2              # GUI framework
Pillow==12.1.1             # Image processing
fpdf2==2.8.7               # PDF generation
PyMuPDF==1.27.2.2          # Advanced PDF handling
python-barcode==0.16.1     # Barcode generation
defusedxml==0.7.1          # Secure XML parsing
PyInstaller==6.19.0        # Executable packaging
```

---

## ⌨️ Keyboard Shortcuts

| Action | Shortcut | Context |
|--------|----------|---------|
| **New Product** | `Ctrl+N` | Main window |
| **Stock In** | `Ctrl+I` | Main window with product selected |
| **Stock Out** | `Ctrl+O` | Main window with product selected |
| **Adjust Stock** | `Ctrl+J` | Main window with product selected |
| **Search** | `Ctrl+F` | Main window |
| **Delete Product** | `Del` | Main window with product selected |
| **Export Report** | `Ctrl+P` | Main window |
| **Admin Settings** | `Ctrl+Alt+A` | Main window |
| **Generate Barcode** | `Ctrl+B` | Product detail view |
| **Refresh** | `F5` | Main window |
| **Open Admin Panel** | `Ctrl+Alt+S` | Main window |

---

## 👨‍💼 Admin Panel Guide

### Accessing Admin Panel

1. **Keyboard:** Press `Ctrl+Alt+A`
2. **Menu:** File → Admin Settings
3. **Button:** Admin button in toolbar

### Shop Settings
Configure global application settings:
- **Shop Name** — Your business/organization name
- **Location** — Shop address or location
- **Currency** — Currency symbol and decimal precision
- **Phone** — Contact phone number
- **Email** — Business email address
- **Tax Rate** — Default tax percentage

### Categories Management
Create and organize product categories:
- Add new categories
- Edit category names and descriptions
- Set category-specific settings
- Delete unused categories
- Drag-and-drop to reorder

### Part Types
Define product classifications:
- Create product types (e.g., Electronics, Accessories, Spare Parts)
- Assign icons/colors to types
- Manage type-specific attributes

### Models Management
Define product variants and models:
- Create product models within categories
- Set model specifications
- Link models to part types
- Manage model variations

### Color Picker
Professional color selection:
- 20+ preset colors
- Custom color selection with RGB/HEX input
- Color preview
- Save favorite colors

### Scan Settings
Configure barcode scanner behavior:
- Scanner input delay
- Barcode format settings
- Sound/vibration feedback
- Automatic focus settings
- Duplicate scan handling

---

## 📱 Barcode Workflow

### Scanning Workflow

1. **Plug in USB barcode scanner** — Device will be auto-detected
2. **Open barcode scanner dialog** — `Ctrl+S` or Tools → Barcode Scanner
3. **Scan products** — Point scanner at barcodes
4. **Automatic stock update** — Stock quantities update in real-time
5. **Review session** — View all scanned items with quantities

### Barcode Generation Workflow

1. **Select product** in inventory
2. **Right-click** → Generate Barcode or press `Ctrl+B`
3. **Configure barcode** (format, size, text)
4. **Preview** the barcode
5. **Print** or **Export as image**
6. **Assign to product** (automatic)

### Barcode Assignment

For products without barcodes:
1. **Open** Tools → Assign Barcodes
2. **Bulk generate** for multiple products
3. **Manual entry** for specific barcodes
4. **Verify** assignments in product list

---

## 📊 PDF Reports

### Report Types

1. **Inventory Summary** — Current stock levels and valuations
2. **Transaction History** — All stock movements with timestamps
3. **Low Stock Alert** — Products below minimum threshold
4. **Category Report** — Stock by category
5. **Custom Report** — Date range and product filtering

### Generate Report

1. **File → Export Report** or `Ctrl+P`
2. **Select report type**
3. **Choose date range** (optional)
4. **Filter products** (optional)
5. **Configure page layout** (orientation, margins)
6. **Preview** the report
7. **Save** as PDF or **Print directly**

### Report Features

- Professional company header with logo
- Date and time stamps
- Customizable data fields
- Tables with automatic pagination
- Summary statistics
- Barcode scanning support in reports

---

## 🔒 Data & Privacy

### Data Storage

All data is stored **locally** on your machine:

```
%LOCALAPPDATA%\StockPro\StockManagerPro\stock_manager.db
```

### Security Features

- ✅ No internet connection required
- ✅ No cloud sync or telemetry
- ✅ No user tracking or analytics
- ✅ Local database encryption (optional)
- ✅ Admin password protection (configurable)
- ✅ Full audit logs of all transactions

### Database Backup

Recommended backup strategy:
1. **Automatic backups** — Configure in Admin → Shop Settings
2. **Manual backup** — Copy `stock_manager.db` to external drive
3. **Scheduled backups** — Use Windows Task Scheduler

**Backup location suggestion:** `C:\Backups\StockManager\`

---

## 🤝 Contributing

We welcome contributions! Here's how to help:

### Development Setup

```bash
# Clone and setup
git clone https://github.com/AbdullahBakir97/Stock-manager.git
cd Stock-manager
git checkout dev

# Create feature branch
git checkout -b feature/your-feature-name

# Install dependencies
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Make your changes and test
python files/main.py

# Commit with descriptive messages
git add .
git commit -m "feat: add your feature description"
git push origin feature/your-feature-name
```

### Contribution Guidelines

1. **Create a feature branch** from `dev` branch
2. **Write clear commit messages** (use conventional commits)
3. **Test your changes** thoroughly
4. **Update README** if adding new features
5. **Submit Pull Request** with detailed description
6. **Wait for review** from maintainers

### Code Standards

- Follow PEP 8 Python style guide
- Use type hints for function arguments
- Write docstrings for classes and methods
- Keep functions small and focused
- Add comments for complex logic

---

## 🐛 Troubleshooting

### Common Issues

#### Application Won't Start

**Problem:** `StockManagerPro.exe` doesn't launch

**Solutions:**
- Check Windows Defender/Antivirus isn't blocking the app
- Run in compatibility mode (Right-click → Properties → Compatibility)
- Delete `%LOCALAPPDATA%\StockPro\` and restart (will reset to default)
- Check Event Viewer for error details

#### Barcode Scanner Not Working

**Problem:** Scanner plugged in but not recognized

**Solutions:**
- Install scanner drivers (often not needed for HID scanners)
- Check scanner is in "Keyboard Emulation" mode
- Verify scanner settings in Admin → Scan Settings
- Test in Notepad first to confirm scanner works
- Try different USB port

#### Database Corruption

**Problem:** Getting database errors or crashes

**Solutions:**
- Restart the application
- Check disk space availability
- Restore from backup in Admin → Restore Backup
- Run database repair: File → Tools → Repair Database
- Reinstall application if all else fails

#### Slow Performance

**Problem:** Application is sluggish with large databases

**Solutions:**
- Close other applications to free RAM
- Run database optimization: File → Tools → Optimize Database
- Reduce number of columns displayed in tables
- Increase cache in Admin → Performance Settings
- Archive old transactions (Admin → Archive Transactions)

#### PDF Generation Error

**Problem:** Can't generate or export PDF reports

**Solutions:**
- Ensure fpdf2 and PyMuPDF are installed: `pip install -r requirements.txt`
- Check disk space for PDF creation
- Verify file permissions in Documents folder
- Try different save location
- Disable antivirus temporarily during PDF generation

### Logs and Debugging

Application logs are stored at:
```
%LOCALAPPDATA%\StockPro\StockManagerPro\logs\
```

Enable debug mode for detailed logging:
1. Admin Panel → Advanced Settings
2. Enable "Debug Mode"
3. Restart application
4. Check logs folder for detailed output

---

## ❓ FAQ

### General Questions

**Q: Can I use this on Mac or Linux?**
A: Currently Windows only due to PyQt6 and specific Windows dependencies. Mac/Linux support is planned for future versions.

**Q: Is a network version available?**
A: Not currently, but multi-user local network support is on the roadmap.

**Q: Can I migrate from another inventory system?**
A: Yes! Use the import feature in Admin → Data Management → Import CSV.

**Q: How often should I backup my data?**
A: Daily backup is recommended for active businesses. Use Windows Task Scheduler for automatic backups.

### Technical Questions

**Q: How much data can the database handle?**
A: SQLite can handle millions of records. Performance degrades around 1-2 million transactions; consider archiving older data.

**Q: Can I customize the UI/themes?**
A: Yes, edit the Qt stylesheets in `app/resources/styles/`. Restart after making changes.

**Q: How do I uninstall the application?**
A: Simply delete the `StockManagerPro` folder. Data is stored separately and won't be deleted.

**Q: Can I run multiple instances?**
A: Not recommended as they'll share the same database and cause conflicts.

### Licensing Questions

**Q: Can I modify the code for my business?**
A: Yes! Under the MIT License, you can modify and redistribute, but must include the license.

**Q: Can I sell this software?**
A: Yes, with proper attribution to the original author.

---

## 📞 Support & Feedback

- **Issues & Bug Reports:** [GitHub Issues](https://github.com/AbdullahBakir97/Stock-manager/issues)
- **Feature Requests:** [GitHub Discussions](https://github.com/AbdullahBakir97/Stock-manager/discussions)
- **Email:** Contact via GitHub profile

---

## 📄 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) file for complete details.

**Copyright © 2026 Abdullah Bakir**

---

## 🙏 Acknowledgments

- **PyQt6** — For the excellent desktop framework
- **SQLite** — For reliable local database storage
- **Python Community** — For amazing open-source libraries

---

## 📈 Version History

### v2.0.0 (April 2026) — Current Dev
- ✨ Complete architecture refactor to modular design
- 🏗️ Service-oriented architecture implementation
- 📄 PDF report generation with multiple templates
- 🎯 Barcode generation (not just scanning)
- 📊 Matrix/grid operations for bulk management
- 👨‍💼 Enhanced admin panel with 6 management sections
- 🎨 Professional color picker widget
- 🔧 Setup wizard for new installations
- ⚡ Performance optimizations with custom delegates

### v1.0.0 (Previous)
- Initial release with core inventory management
- Basic barcode scanning support
- Multilingual interface (EN/DE/AR)
- Offline SQLite database
- Low stock alerts

---

**Happy Inventory Managing! 🚀**

For the latest updates, visit: [GitHub Repository](https://github.com/AbdullahBakir97/Stock-manager)

## License

MIT License — see [LICENSE](LICENSE) for details.
