# Stock Manager Pro - Professional Design Guide

A comprehensive design system for transforming the Stock Manager Pro PyQt6 application into a modern, professional desktop app

---

## 1. Color System new addtional themes 

### Primary Palette (5 Colors Maximum)

#### Dark Theme (Recommended Default)
```python
DARK_THEME = {
    # Background hierarchy
    "background_primary": "#0A0A0A",      # Main window background
    "background_secondary": "#141414",    # Panels, cards, sidebars
    "background_tertiary": "#1F1F1F",     # Elevated elements, hover states
    "background_input": "#1A1A1A",        # Input fields, dropdowns
    
    # Text hierarchy
    "text_primary": "#FFFFFF",            # Headings, important text
    "text_secondary": "#A3A3A3",          # Body text, labels
    "text_muted": "#666666",              # Placeholders, disabled
    
    # Accent colors
    "accent_primary": "#10B981",          # Emerald green - Primary actions, success
    "accent_hover": "#059669",            # Darker emerald for hover
    "accent_secondary": "#3B82F6",        # Blue - Links, info states
    
    # Status colors
    "success": "#10B981",                 # Green - Stock in, positive
    "warning": "#F59E0B",                 # Amber - Low stock alerts
    "error": "#EF4444",                   # Red - Stock out, errors
    "info": "#3B82F6",                    # Blue - Information
    
    # Borders
    "border_subtle": "#262626",           # Subtle dividers
    "border_default": "#333333",          # Default borders
    "border_focus": "#10B981",            # Focus rings
}
```

#### Light Theme
```python
LIGHT_THEME = {
    # Background hierarchy
    "background_primary": "#FFFFFF",
    "background_secondary": "#F5F5F5",
    "background_tertiary": "#E5E5E5",
    "background_input": "#FFFFFF",
    
    # Text hierarchy
    "text_primary": "#171717",
    "text_secondary": "#525252",
    "text_muted": "#A3A3A3",
    
    # Same accent and status colors work for both themes
    "accent_primary": "#10B981",
    "accent_hover": "#059669",
    "accent_secondary": "#3B82F6",
    
    "success": "#10B981",
    "warning": "#D97706",
    "error": "#DC2626",
    "info": "#2563EB",
    
    "border_subtle": "#E5E5E5",
    "border_default": "#D4D4D4",
    "border_focus": "#10B981",
}
```

### Updated PyQt Stylesheet Generator

Replace your current `generate_stylesheet` method with this improved version:

```python
def generate_stylesheet(self) -> str:
    c = self.colors  # Your color dictionary
    
    return f'''
    /* ========================================
       GLOBAL STYLES
       ======================================== */
    
    QMainWindow, QDialog {{
        background-color: {c['background_primary']};
        color: {c['text_primary']};
    }}
    
    QWidget {{
        font-family: "Segoe UI", "SF Pro Display", -apple-system, sans-serif;
        font-size: 13px;
        color: {c['text_primary']};
    }}
    
    /* ========================================
       TYPOGRAPHY
       ======================================== */
    
    QLabel {{
        color: {c['text_primary']};
        background: transparent;
    }}
    
    QLabel[heading="true"] {{
        font-size: 18px;
        font-weight: 600;
        letter-spacing: -0.02em;
    }}
    
    QLabel[subheading="true"] {{
        font-size: 14px;
        font-weight: 500;
        color: {c['text_secondary']};
    }}
    
    QLabel[muted="true"] {{
        color: {c['text_muted']};
        font-size: 12px;
    }}
    
    /* ========================================
       BUTTONS
       ======================================== */
    
    QPushButton {{
        background-color: {c['background_tertiary']};
        color: {c['text_primary']};
        border: 1px solid {c['border_default']};
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 500;
        font-size: 13px;
        min-height: 20px;
    }}
    
    QPushButton:hover {{
        background-color: {c['background_secondary']};
        border-color: {c['border_focus']};
    }}
    
    QPushButton:pressed {{
        background-color: {c['background_primary']};
    }}
    
    QPushButton:disabled {{
        background-color: {c['background_secondary']};
        color: {c['text_muted']};
        border-color: {c['border_subtle']};
    }}
    
    /* Primary Button */
    QPushButton[primary="true"] {{
        background-color: {c['accent_primary']};
        color: #FFFFFF;
        border: none;
        font-weight: 600;
    }}
    
    QPushButton[primary="true"]:hover {{
        background-color: {c['accent_hover']};
    }}
    
    /* Danger Button */
    QPushButton[danger="true"] {{
        background-color: transparent;
        color: {c['error']};
        border: 1px solid {c['error']};
    }}
    
    QPushButton[danger="true"]:hover {{
        background-color: {c['error']};
        color: #FFFFFF;
    }}
    
    /* Ghost Button */
    QPushButton[ghost="true"] {{
        background-color: transparent;
        border: none;
        color: {c['text_secondary']};
    }}
    
    QPushButton[ghost="true"]:hover {{
        background-color: {c['background_tertiary']};
        color: {c['text_primary']};
    }}
    
    /* ========================================
       INPUTS
       ======================================== */
    
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background-color: {c['background_input']};
        color: {c['text_primary']};
        border: 1px solid {c['border_default']};
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 13px;
        selection-background-color: {c['accent_primary']};
    }}
    
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
        border-color: {c['accent_primary']};
        outline: none;
    }}
    
    QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{
        background-color: {c['background_secondary']};
        color: {c['text_muted']};
    }}
    
    QLineEdit::placeholder {{
        color: {c['text_muted']};
    }}
    
    /* ComboBox dropdown */
    QComboBox::drop-down {{
        border: none;
        width: 30px;
    }}
    
    QComboBox::down-arrow {{
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid {c['text_secondary']};
        margin-right: 10px;
    }}
    
    QComboBox QAbstractItemView {{
        background-color: {c['background_secondary']};
        border: 1px solid {c['border_default']};
        border-radius: 6px;
        padding: 4px;
        selection-background-color: {c['accent_primary']};
    }}
    
    /* SpinBox arrows */
    QSpinBox::up-button, QSpinBox::down-button,
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
        background-color: transparent;
        border: none;
        width: 20px;
    }}
    
    /* ========================================
       TABLES (Matrix Widget)
       ======================================== */
    
    QTableWidget, QTableView {{
        background-color: {c['background_secondary']};
        alternate-background-color: {c['background_tertiary']};
        border: 1px solid {c['border_default']};
        border-radius: 8px;
        gridline-color: {c['border_subtle']};
        selection-background-color: {c['accent_primary']};
        selection-color: #FFFFFF;
    }}
    
    QTableWidget::item, QTableView::item {{
        padding: 12px 16px;
        border-bottom: 1px solid {c['border_subtle']};
    }}
    
    QTableWidget::item:hover {{
        background-color: {c['background_tertiary']};
    }}
    
    QTableWidget::item:selected {{
        background-color: {c['accent_primary']};
        color: #FFFFFF;
    }}
    
    /* Table Headers */
    QHeaderView::section {{
        background-color: {c['background_primary']};
        color: {c['text_secondary']};
        font-weight: 600;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 12px 16px;
        border: none;
        border-bottom: 1px solid {c['border_default']};
    }}
    
    QHeaderView::section:hover {{
        background-color: {c['background_tertiary']};
        color: {c['text_primary']};
    }}
    
    /* ========================================
       TAB WIDGET (Category Tabs)
       ======================================== */
    
    QTabWidget::pane {{
        background-color: {c['background_secondary']};
        border: 1px solid {c['border_default']};
        border-radius: 8px;
        margin-top: -1px;
    }}
    
    QTabBar::tab {{
        background-color: transparent;
        color: {c['text_secondary']};
        padding: 12px 20px;
        margin-right: 4px;
        border: none;
        border-bottom: 2px solid transparent;
        font-weight: 500;
    }}
    
    QTabBar::tab:hover {{
        color: {c['text_primary']};
        background-color: {c['background_tertiary']};
    }}
    
    QTabBar::tab:selected {{
        color: {c['accent_primary']};
        border-bottom: 2px solid {c['accent_primary']};
        background-color: transparent;
    }}
    
    /* ========================================
       SCROLLBARS
       ======================================== */
    
    QScrollBar:vertical {{
        background-color: transparent;
        width: 10px;
        margin: 0;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {c['border_default']};
        border-radius: 5px;
        min-height: 30px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: {c['text_muted']};
    }}
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
        height: 0;
    }}
    
    QScrollBar:horizontal {{
        background-color: transparent;
        height: 10px;
        margin: 0;
    }}
    
    QScrollBar::handle:horizontal {{
        background-color: {c['border_default']};
        border-radius: 5px;
        min-width: 30px;
    }}
    
    /* ========================================
       DIALOGS
       ======================================== */
    
    QDialog {{
        background-color: {c['background_primary']};
        border-radius: 12px;
    }}
    
    QDialog QLabel[title="true"] {{
        font-size: 20px;
        font-weight: 600;
        margin-bottom: 8px;
    }}
    
    /* ========================================
       FRAMES & CARDS
       ======================================== */
    
    QFrame[card="true"] {{
        background-color: {c['background_secondary']};
        border: 1px solid {c['border_default']};
        border-radius: 8px;
        padding: 16px;
    }}
    
    QFrame[card="true"]:hover {{
        border-color: {c['border_focus']};
    }}
    
    /* Summary Cards */
    QFrame[summary-card="true"] {{
        background-color: {c['background_secondary']};
        border: 1px solid {c['border_default']};
        border-radius: 12px;
        padding: 20px;
    }}
    
    /* ========================================
       SIDEBAR / NAVIGATION
       ======================================== */
    
    QFrame[sidebar="true"] {{
        background-color: {c['background_secondary']};
        border-right: 1px solid {c['border_default']};
    }}
    
    QPushButton[nav-item="true"] {{
        background-color: transparent;
        color: {c['text_secondary']};
        border: none;
        border-radius: 6px;
        padding: 10px 16px;
        text-align: left;
        font-weight: 500;
    }}
    
    QPushButton[nav-item="true"]:hover {{
        background-color: {c['background_tertiary']};
        color: {c['text_primary']};
    }}
    
    QPushButton[nav-item="true"][active="true"] {{
        background-color: {c['accent_primary']};
        color: #FFFFFF;
    }}
    
    /* ========================================
       STATUS INDICATORS
       ======================================== */
    
    QLabel[status="success"] {{
        color: {c['success']};
    }}
    
    QLabel[status="warning"] {{
        color: {c['warning']};
    }}
    
    QLabel[status="error"] {{
        color: {c['error']};
    }}
    
    QLabel[status="info"] {{
        color: {c['info']};
    }}
    
    /* Stock level badges */
    QLabel[badge="true"] {{
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
    }}
    
    QLabel[badge-success="true"] {{
        background-color: rgba(16, 185, 129, 0.15);
        color: {c['success']};
    }}
    
    QLabel[badge-warning="true"] {{
        background-color: rgba(245, 158, 11, 0.15);
        color: {c['warning']};
    }}
    
    QLabel[badge-error="true"] {{
        background-color: rgba(239, 68, 68, 0.15);
        color: {c['error']};
    }}
    
    /* ========================================
       TOOLTIPS
       ======================================== */
    
    QToolTip {{
        background-color: {c['background_tertiary']};
        color: {c['text_primary']};
        border: 1px solid {c['border_default']};
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 12px;
    }}
    
    /* ========================================
       MENU BAR
       ======================================== */
    
    QMenuBar {{
        background-color: {c['background_primary']};
        color: {c['text_primary']};
        border-bottom: 1px solid {c['border_default']};
        padding: 4px 8px;
    }}
    
    QMenuBar::item {{
        background-color: transparent;
        padding: 6px 12px;
        border-radius: 4px;
    }}
    
    QMenuBar::item:selected {{
        background-color: {c['background_tertiary']};
    }}
    
    QMenu {{
        background-color: {c['background_secondary']};
        border: 1px solid {c['border_default']};
        border-radius: 8px;
        padding: 4px;
    }}
    
    QMenu::item {{
        padding: 8px 24px 8px 12px;
        border-radius: 4px;
    }}
    
    QMenu::item:selected {{
        background-color: {c['accent_primary']};
        color: #FFFFFF;
    }}
    
    QMenu::separator {{
        height: 1px;
        background-color: {c['border_default']};
        margin: 4px 8px;
    }}
    
    /* ========================================
       GROUP BOX
       ======================================== */
    
    QGroupBox {{
        background-color: {c['background_secondary']};
        border: 1px solid {c['border_default']};
        border-radius: 8px;
        margin-top: 16px;
        padding-top: 24px;
        font-weight: 600;
    }}
    
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 16px;
        top: 8px;
        color: {c['text_secondary']};
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    
    /* ========================================
       PROGRESS BAR
       ======================================== */
    
    QProgressBar {{
        background-color: {c['background_tertiary']};
        border: none;
        border-radius: 4px;
        height: 8px;
        text-align: center;
    }}
    
    QProgressBar::chunk {{
        background-color: {c['accent_primary']};
        border-radius: 4px;
    }}
    '''
```

---

## 2. Typography

### Font Stack
```python
# Primary font - Use system fonts for best performance
FONT_FAMILY = '"Segoe UI", "SF Pro Display", -apple-system, "Helvetica Neue", sans-serif'

# For Arabic (RTL) support
FONT_FAMILY_ARABIC = '"Segoe UI", "SF Arabic", "Arial", sans-serif'

# Monospace for data/numbers
FONT_FAMILY_MONO = '"JetBrains Mono", "SF Mono", "Consolas", monospace'
```

### Font Sizes
```python
FONT_SIZES = {
    "xs": 11,      # Badges, timestamps
    "sm": 12,      # Secondary text, labels
    "base": 13,    # Body text, inputs
    "md": 14,      # Emphasized body
    "lg": 16,      # Section headings
    "xl": 18,      # Page headings
    "2xl": 24,     # Main titles
    "3xl": 30,     # Hero numbers (dashboard stats)
}
```

### Font Weights
```python
FONT_WEIGHTS = {
    "normal": 400,
    "medium": 500,
    "semibold": 600,
    "bold": 700,
}
```

---

## 3. Spacing System

Use consistent spacing based on a 4px grid:

```python
SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 20,
    "2xl": 24,
    "3xl": 32,
    "4xl": 48,
}

# Component-specific spacing
PADDING = {
    "button": (8, 16),      # (vertical, horizontal)
    "input": (8, 12),
    "card": (20, 20),
    "dialog": (24, 24),
    "table_cell": (12, 16),
}

BORDER_RADIUS = {
    "sm": 4,
    "md": 6,
    "lg": 8,
    "xl": 12,
    "full": 9999,
}
```

---

## 4. Component Redesigns

### 4.1 Matrix Widget (Stock Grid)

**Current Issues:**
- Dense, hard-to-scan data
- Poor visual hierarchy
- Missing hover states

**Improvements:**

```python
class MatrixWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Visual improvements
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)  # Use row separators instead
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        # Better sizing
        self.verticalHeader().setDefaultSectionSize(48)  # Taller rows
        self.horizontalHeader().setDefaultSectionSize(120)
        
        # Remove borders for cleaner look
        self.setFrameShape(QFrame.NoFrame)
        
        # Enable smooth scrolling
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
```

**Cell Formatting for Stock Levels:**

```python
def format_stock_cell(self, quantity: int, min_stock: int) -> QWidget:
    """Create a styled stock cell with visual indicators"""
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(12, 8, 12, 8)
    
    # Stock number
    label = QLabel(str(quantity))
    label.setFont(QFont(FONT_FAMILY_MONO, 14, QFont.Bold))
    
    # Color based on stock level
    if quantity == 0:
        label.setStyleSheet(f"color: {COLORS['error']};")
        badge_style = "badge-error"
    elif quantity <= min_stock:
        label.setStyleSheet(f"color: {COLORS['warning']};")
        badge_style = "badge-warning"
    else:
        label.setStyleSheet(f"color: {COLORS['success']};")
        badge_style = "badge-success"
    
    layout.addWidget(label)
    
    # Optional: Add trend indicator
    # trend_icon = QLabel("↑" if positive_trend else "↓")
    # layout.addWidget(trend_icon)
    
    return container
```

### 4.2 Summary Cards (Dashboard)

Replace your current stats display with modern cards:

```python
class SummaryCard(QFrame):
    def __init__(self, title: str, value: str, subtitle: str = "", 
                 status: str = "default", parent=None):
        super().__init__(parent)
        self.setProperty("summary-card", True)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # Title
        title_label = QLabel(title)
        title_label.setProperty("subheading", True)
        layout.addWidget(title_label)
        
        # Value (large number)
        value_label = QLabel(value)
        value_label.setFont(QFont(FONT_FAMILY, 30, QFont.Bold))
        if status == "success":
            value_label.setProperty("status", "success")
        elif status == "warning":
            value_label.setProperty("status", "warning")
        elif status == "error":
            value_label.setProperty("status", "error")
        layout.addWidget(value_label)
        
        # Subtitle
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setProperty("muted", True)
            layout.addWidget(subtitle_label)
        
        self.setFixedSize(200, 120)
```

**Usage:**
```python
# In your main window
stats_layout = QHBoxLayout()
stats_layout.addWidget(SummaryCard(
    title="Total Stock Items",
    value="1,234",
    subtitle="Across all categories"
))
stats_layout.addWidget(SummaryCard(
    title="Low Stock Alerts",
    value="12",
    subtitle="Need attention",
    status="warning"
))
stats_layout.addWidget(SummaryCard(
    title="Out of Stock",
    value="3",
    subtitle="Critical",
    status="error"
))
```

### 4.3 Modern Dialogs

```python
class ModernDialog(QDialog):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        
        # Remove default title bar for custom header
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Main container with rounded corners
        self.container = QFrame(self)
        self.container.setProperty("card", True)
        
        # Shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.container.setGraphicsEffect(shadow)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(self.container)
        
        self.content_layout = QVBoxLayout(self.container)
        self.content_layout.setSpacing(16)
        self.content_layout.setContentsMargins(24, 24, 24, 24)
        
        # Header
        header = QHBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setProperty("heading", True)
        header.addWidget(self.title_label)
        header.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setProperty("ghost", True)
        close_btn.setFixedSize(32, 32)
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn)
        
        self.content_layout.addLayout(header)
```

### 4.4 Modern Form Layout

```python
class FormField(QWidget):
    """Consistent form field with label"""
    def __init__(self, label: str, widget: QWidget, 
                 required: bool = False, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(6)
        
        # Label row
        label_row = QHBoxLayout()
        label_widget = QLabel(label)
        label_widget.setProperty("subheading", True)
        label_row.addWidget(label_widget)
        
        if required:
            required_indicator = QLabel("*")
            required_indicator.setStyleSheet(f"color: {COLORS['error']};")
            label_row.addWidget(required_indicator)
        
        label_row.addStretch()
        layout.addLayout(label_row)
        
        # Input widget
        layout.addWidget(widget)
```

**Usage:**
```python
# In your dialog
form = QVBoxLayout()
form.addWidget(FormField("Phone Model", QComboBox(), required=True))
form.addWidget(FormField("Part Type", QComboBox(), required=True))
form.addWidget(FormField("Quantity", QSpinBox(), required=True))
form.addWidget(FormField("Notes", QTextEdit()))
```

---

## 5. Layout Recommendations

### 5.1 Main Window Structure

```
┌─────────────────────────────────────────────────────────────┐
│  [Logo]    Stock Manager Pro              [Search]  [⚙️]   │  <- Header (60px)
├─────────────────────────────────────────────────────────────┤
│ ┌──────┐ ┌─────────────────────────────────────────────────┐│
│ │      │ │ Summary Cards                                   ││
│ │ Side │ │ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ││
│ │ bar  │ │ │ Total   │ │ Low     │ │ Out     │ │ Recent  │ ││
│ │      │ │ │ 1,234   │ │ 12      │ │ 3       │ │ 45      │ ││
│ │ 200px│ │ └─────────┘ └─────────┘ └─────────┘ └─────────┘ ││
│ │      │ ├─────────────────────────────────────────────────┤│
│ │  📦  │ │ Category Tabs                                   ││
│ │ Stock│ │ [Displays] [Batteries] [Screens] [Accessories]  ││
│ │      │ ├─────────────────────────────────────────────────┤│
│ │  📊  │ │                                                 ││
│ │ Stats│ │           Matrix Grid                           ││
│ │      │ │                                                 ││
│ │  ⚙️  │ │   Model    │ LCD │ Touch │ Battery │ Back     ││
│ │ Sett │ │  ─────────────────────────────────────────     ││
│ │      │ │  iPhone 15 │  23 │   18  │    45   │  12      ││
│ │      │ │  iPhone 14 │  15 │   22  │    38   │   8      ││
│ │      │ │  Samsung.. │  12 │   19  │    25   │  15      ││
│ │      │ │                                                 ││
│ └──────┘ └─────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│  Ready  │  Items: 1,234  │  Last sync: 2 min ago    [v2.0] │  <- Status bar
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Sidebar Navigation

```python
class Sidebar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("sidebar", True)
        self.setFixedWidth(200)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 16, 8, 16)
        layout.setSpacing(4)
        
        # Navigation items
        self.nav_items = []
        
        nav_data = [
            ("📦", "Inventory", "inventory"),
            ("📊", "Analytics", "analytics"),
            ("📜", "Transactions", "transactions"),
            ("⚠️", "Alerts", "alerts"),
            ("⚙️", "Settings", "settings"),
        ]
        
        for icon, label, key in nav_data:
            btn = QPushButton(f"  {icon}  {label}")
            btn.setProperty("nav-item", True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self.on_nav_click(k))
            layout.addWidget(btn)
            self.nav_items.append((key, btn))
        
        layout.addStretch()
        
        # User info at bottom
        user_frame = QFrame()
        user_layout = QHBoxLayout(user_frame)
        user_layout.setContentsMargins(8, 8, 8, 8)
        
        avatar = QLabel("👤")
        user_layout.addWidget(avatar)
        
        user_info = QVBoxLayout()
        name = QLabel("Admin User")
        name.setProperty("subheading", True)
        user_info.addWidget(name)
        
        role = QLabel("Administrator")
        role.setProperty("muted", True)
        user_info.addWidget(role)
        
        user_layout.addLayout(user_info)
        layout.addWidget(user_frame)
    
    def set_active(self, key: str):
        for nav_key, btn in self.nav_items:
            btn.setProperty("active", nav_key == key)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
```

---

## 6. RTL (Arabic) Support

### Layout Direction

```python
def setup_rtl_support(self, language: str):
    """Configure RTL layout for Arabic"""
    if language == "ar":
        self.setLayoutDirection(Qt.RightToLeft)
        
        # Update font for Arabic
        arabic_font = QFont("Segoe UI", 13)
        arabic_font.setStyleHint(QFont.SansSerif)
        self.setFont(arabic_font)
    else:
        self.setLayoutDirection(Qt.LeftToRight)
```

### RTL-Aware Margins

```python
def get_directional_margins(self, left: int, top: int, 
                            right: int, bottom: int) -> tuple:
    """Return margins that respect RTL direction"""
    if QApplication.layoutDirection() == Qt.RightToLeft:
        return (right, top, left, bottom)
    return (left, top, right, bottom)
```

---

## 7. Icons

### Recommended Icon Set

Use **Lucide Icons** (MIT licensed) or **Feather Icons** for consistency.

For PyQt6, convert SVG icons to QIcon:

```python
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtGui import QIcon, QPixmap, QPainter

def svg_icon(svg_path: str, size: int = 24, color: str = "#FFFFFF") -> QIcon:
    """Create QIcon from SVG with custom color"""
    renderer = QSvgRenderer(svg_path)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    
    return QIcon(pixmap)
```

### Essential Icons for Stock Manager

```
- package (📦) - Inventory
- bar-chart-2 (📊) - Analytics
- file-text (📜) - Transactions
- alert-triangle (⚠️) - Alerts
- settings (⚙️) - Settings
- plus - Add item
- minus - Remove item
- edit-2 - Edit
- trash-2 - Delete
- search - Search
- filter - Filter
- download - Export
- upload - Import
- refresh-cw - Refresh
- check - Confirm
- x - Cancel/Close
- chevron-down - Dropdown
- chevron-right - Expand
- arrow-up - Increase
- arrow-down - Decrease
```

---

## 8. Animation & Transitions

### Hover Effects

```python
class AnimatedButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(100)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
    
    def enterEvent(self, event):
        # Subtle scale effect
        self.animation.setStartValue(self.geometry())
        new_rect = self.geometry().adjusted(-2, -1, 2, 1)
        self.animation.setEndValue(new_rect)
        self.animation.start()
        super().enterEvent(event)
```

### Loading States

```python
class SpinnerLabel(QLabel):
    """Animated loading spinner"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        
    def start(self):
        self.timer.start(50)
        
    def stop(self):
        self.timer.stop()
        
    def rotate(self):
        self.angle = (self.angle + 30) % 360
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(self.width()/2, self.height()/2)
        painter.rotate(self.angle)
        # Draw spinner arc
        painter.setPen(QPen(QColor(COLORS['accent_primary']), 3))
        painter.drawArc(-10, -10, 20, 20, 0, 270 * 16)
```

---

## 9. Accessibility

### Focus Indicators

```css
/* Already included in main stylesheet */
QLineEdit:focus, QPushButton:focus {
    border-color: {accent_primary};
    outline: none;
}
```

### Keyboard Navigation

```python
# Ensure all interactive elements are focusable
button.setFocusPolicy(Qt.StrongFocus)

# Add keyboard shortcuts
QShortcut(QKeySequence("Ctrl+N"), self, self.new_item)
QShortcut(QKeySequence("Ctrl+S"), self, self.save)
QShortcut(QKeySequence("Ctrl+F"), self, self.focus_search)
QShortcut(QKeySequence("F5"), self, self.refresh)
```

### Screen Reader Support

```python
# Set accessible names and descriptions
button.setAccessibleName("Add new stock item")
button.setAccessibleDescription("Opens dialog to add a new item to inventory")
table.setAccessibleName("Stock inventory matrix")
```

---

## 10. Quick Implementation Checklist

1. **Colors**: Replace your `colors.py` with the new palette
2. **Stylesheet**: Update `generate_stylesheet()` method
3. **Typography**: Set consistent fonts across all widgets
4. **Spacing**: Apply 4px grid spacing system
5. **Cards**: Replace stat displays with SummaryCard components
6. **Tables**: Style matrix with alternating rows, no grid lines
7. **Dialogs**: Use rounded corners with subtle shadows
8. **Buttons**: Add primary, danger, ghost button variants
9. **Navigation**: Implement sidebar with active states
10. **Icons**: Add consistent icon set

---

## Example: Before vs After

### Before (Current)
```
┌─────────────────────────────┐
│ Stock: 15                   │  <- Plain text, no visual hierarchy
│ [+] [-] [Edit]             │  <- Basic buttons
└─────────────────────────────┘
```

### After (Redesigned)
```
┌─────────────────────────────┐
│ ┌─────────────────────────┐ │
│ │  Stock Level            │ │  <- Subtle label
│ │  ██████████░░ 15       │ │  <- Visual bar + number
│ │  ↑ +3 from last week   │ │  <- Trend indicator
│ └─────────────────────────┘ │
│                             │
│  [+ Add]  [- Remove]  [✏️]  │  <- Styled buttons with icons
└─────────────────────────────┘
```

---

This design guide provides everything needed to transform Stock Manager Pro into a modern, professional application while main
functionality and RTL support.
