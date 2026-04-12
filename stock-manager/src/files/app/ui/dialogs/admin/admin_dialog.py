"""
app/ui/dialogs/admin/admin_dialog.py — Professional sidebar-nav admin settings.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QStackedWidget, QScrollArea, QWidget,
    QInputDialog, QMessageBox, QSizePolicy,
)
from PyQt6.QtCore import pyqtSignal, Qt

from app.core.config import ShopConfig
from app.ui.dialogs.admin.shop_settings_panel import ShopSettingsPanel
from app.ui.dialogs.admin.categories_panel import CategoriesPanel
from app.ui.dialogs.admin.part_types_panel import PartTypesPanel
from app.ui.dialogs.admin.models_panel import ModelsPanel
from app.ui.dialogs.admin.scan_settings_panel import ScanSettingsPanel
from app.ui.dialogs.admin.backup_panel import BackupPanel
from app.ui.dialogs.admin.import_export_panel import ImportExportPanel
from app.ui.dialogs.admin.db_tools_panel import DatabaseToolsPanel
from app.ui.dialogs.admin.suppliers_panel import SuppliersPanel
from app.ui.dialogs.admin.locations_panel import LocationsPanel
from app.ui.dialogs.admin.customers_panel import CustomersPanel
from app.ui.dialogs.admin.about_panel import AboutPanel
from app.core.theme import THEME
from app.core.i18n import t


# ── Navigation structure ────────────────────────────────────────────────────

_NAV_GROUPS = [
    {
        "label_key": "admin_nav_general",
        "fallback": "GENERAL",
        "items": [
            {"key": "shop", "label_key": "admin_tab_shop", "icon": "⚙️"},
        ],
    },
    {
        "label_key": "admin_nav_inventory",
        "fallback": "INVENTORY",
        "items": [
            {"key": "categories", "label_key": "admin_tab_categories", "icon": "📁"},
            {"key": "part_types", "label_key": "admin_tab_part_types", "icon": "🏷"},
            {"key": "models",     "label_key": "admin_tab_models",     "icon": "📱"},
        ],
    },
    {
        "label_key": "admin_nav_operations",
        "fallback": "OPERATIONS",
        "items": [
            {"key": "customers",  "label_key": "admin_tab_customers",  "icon": "👥"},
            {"key": "suppliers",  "label_key": "admin_tab_suppliers",  "icon": "🏪"},
            {"key": "locations",  "label_key": "admin_tab_locations",  "icon": "📍"},
            {"key": "scan",       "label_key": "admin_tab_scan",       "icon": "📷"},
        ],
    },
    {
        "label_key": "admin_nav_system",
        "fallback": "SYSTEM",
        "items": [
            {"key": "backup",        "label_key": "admin_tab_backup",        "icon": "💾"},
            {"key": "import_export", "label_key": "admin_tab_import_export", "icon": "📊"},
            {"key": "db_tools",      "label_key": "admin_tab_db_tools",      "icon": "🔧"},
            {"key": "about",         "label_key": "admin_tab_about",         "icon": "ℹ️"},
        ],
    },
]


class AdminDialog(QDialog):
    """
    Professional admin dialog with sidebar navigation.
    Replaces the old tab-based layout with a modern sidebar + stacked content area.
    Emits settings_changed when anything is saved.
    """

    settings_changed         = pyqtSignal()
    preview_banner_requested = pyqtSignal(object)   # emits UpdateManifest

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("admin_dialog")
        self.setWindowTitle(t("admin_title"))
        self.setModal(True)
        self.resize(1100, 720)
        THEME.apply(self)
        self._nav_buttons: dict[str, QPushButton] = {}
        self._active_key: str = "shop"
        self._build_ui()
        self._connect_signals()
        self._select_nav("shop")

    # ── Build UI ────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ──
        sidebar = QFrame()
        sidebar.setObjectName("admin_sidebar")
        sidebar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(0, 0, 0, 0)
        sb_lay.setSpacing(0)

        # Sidebar header
        title = QLabel(t("admin_title"))
        title.setObjectName("admin_sidebar_title")
        sb_lay.addWidget(title)

        subtitle = QLabel(
            t("admin_sidebar_desc")
            if t("admin_sidebar_desc") != "admin_sidebar_desc"
            else "Configure your workspace"
        )
        subtitle.setObjectName("admin_sidebar_subtitle")
        sb_lay.addWidget(subtitle)

        # Separator
        sep = QFrame()
        sep.setObjectName("admin_nav_separator")
        sep.setFixedHeight(1)
        sb_lay.addWidget(sep)

        # Navigation scroll area
        nav_scroll = QScrollArea()
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        nav_scroll.setObjectName("analytics_scroll")
        nav_inner = QWidget()
        nav_lay = QVBoxLayout(nav_inner)
        nav_lay.setContentsMargins(0, 4, 0, 8)
        nav_lay.setSpacing(0)

        for group in _NAV_GROUPS:
            label_text = t(group["label_key"])
            if label_text == group["label_key"]:
                label_text = group["fallback"]
            grp_label = QLabel(label_text)
            grp_label.setObjectName("admin_nav_group")
            nav_lay.addWidget(grp_label)

            for item in group["items"]:
                btn = QPushButton(f"  {item['icon']}  {t(item['label_key'])}")
                btn.setObjectName("admin_nav_item")
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda _, k=item["key"]: self._select_nav(k))
                nav_lay.addWidget(btn)
                self._nav_buttons[item["key"]] = btn

        nav_lay.addStretch()
        nav_scroll.setWidget(nav_inner)
        sb_lay.addWidget(nav_scroll, 1)

        root.addWidget(sidebar)

        # ── Content area ──
        self._stack = QStackedWidget()
        self._stack.setObjectName("admin_content_stack")

        # Create panels
        self._panels: dict[str, QWidget] = {}
        self._shop_panel = ShopSettingsPanel()
        self._cat_panel = CategoriesPanel()
        self._pt_panel = PartTypesPanel()
        self._mdl_panel = ModelsPanel()
        self._cust_panel = CustomersPanel()
        self._sup_panel = SuppliersPanel()
        self._loc_panel = LocationsPanel()
        self._scan_panel = ScanSettingsPanel()
        self._backup_panel = BackupPanel()
        self._import_export_panel = ImportExportPanel()
        self._db_tools_panel = DatabaseToolsPanel()
        self._about_panel = AboutPanel()

        panel_map = {
            "shop": self._shop_panel,
            "categories": self._cat_panel,
            "part_types": self._pt_panel,
            "models": self._mdl_panel,
            "customers": self._cust_panel,
            "suppliers": self._sup_panel,
            "locations": self._loc_panel,
            "scan": self._scan_panel,
            "backup": self._backup_panel,
            "import_export": self._import_export_panel,
            "db_tools": self._db_tools_panel,
            "about": self._about_panel,
        }

        for key, panel in panel_map.items():
            self._stack.addWidget(panel)
            self._panels[key] = panel

        root.addWidget(self._stack, 1)

    # ── Navigation ──────────────────────────────────────────────────────────

    def _select_nav(self, key: str) -> None:
        """Switch to the panel identified by key and highlight the nav button."""
        # Update button styles
        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.setObjectName("admin_nav_active")
            else:
                btn.setObjectName("admin_nav_item")
            btn.setStyle(btn.style())  # Force QSS re-evaluation

        # Switch stacked widget
        panel = self._panels.get(key)
        if panel:
            self._stack.setCurrentWidget(panel)

        # Reload panel data when switching
        self._reload_panel(key)
        self._active_key = key

    def _reload_panel(self, key: str) -> None:
        """Reload data for the selected panel."""
        if key == "part_types":
            self._pt_panel.reload()
        elif key == "models":
            self._mdl_panel.reload()
        elif key == "customers":
            self._cust_panel.reload()
        elif key == "suppliers":
            self._sup_panel.reload()
        elif key == "locations":
            self._loc_panel.reload()

    # ── Signals ─────────────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        self._shop_panel.settings_saved.connect(self.settings_changed)
        self._cat_panel.categories_changed.connect(self._on_cat_changed)
        self._about_panel.preview_banner_requested.connect(self._on_preview_banner)

    def _on_cat_changed(self) -> None:
        self._pt_panel.reload()
        self._mdl_panel.reload()
        self.settings_changed.emit()

    def _on_preview_banner(self, manifest) -> None:
        """Re-emit the preview request, then close so the banner is visible."""
        self.preview_banner_requested.emit(manifest)
        self.accept()   # close the modal dialog so the banner can be seen


def open_admin(parent=None) -> bool:
    """
    PIN-gate check then open admin dialog.
    Returns True if dialog was opened (PIN OK or no PIN set).
    """
    cfg = ShopConfig.get()
    if cfg.admin_pin:
        from PyQt6.QtWidgets import QLineEdit
        pin, ok = QInputDialog.getText(
            parent, t("pin_title"), t("pin_prompt"),
            QLineEdit.EchoMode.Password,
        )
        if not ok:
            return False
        if pin != cfg.admin_pin:
            QMessageBox.warning(parent, t("pin_title"), t("pin_wrong"))
            return False

    dlg = AdminDialog(parent)
    dlg.exec()
    return True
