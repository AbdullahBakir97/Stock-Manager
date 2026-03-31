"""
app/ui/dialogs/admin/admin_dialog.py — Tabbed admin settings container.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QInputDialog, QMessageBox,
)
from PyQt6.QtCore import pyqtSignal

from app.core.config import ShopConfig
from app.ui.dialogs.admin.shop_settings_panel  import ShopSettingsPanel
from app.ui.dialogs.admin.categories_panel     import CategoriesPanel
from app.ui.dialogs.admin.part_types_panel     import PartTypesPanel
from app.ui.dialogs.admin.models_panel         import ModelsPanel
from app.ui.dialogs.admin.scan_settings_panel  import ScanSettingsPanel
from app.core.theme import THEME
from app.core.i18n import t


class AdminDialog(QDialog):
    """
    Modal admin dialog with four tabs:
    Shop Settings | Categories | Part Types | Models
    Emits settings_changed when anything is saved.
    """

    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("admin_title"))
        self.setModal(True)
        self.resize(720, 540)
        THEME.apply(self)
        self._build_ui()

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()

        self._shop_panel  = ShopSettingsPanel()
        self._cat_panel   = CategoriesPanel()
        self._pt_panel    = PartTypesPanel()
        self._mdl_panel   = ModelsPanel()
        self._scan_panel  = ScanSettingsPanel()

        self._tabs.addTab(self._shop_panel,  t("admin_tab_shop"))
        self._tabs.addTab(self._cat_panel,   t("admin_tab_categories"))
        self._tabs.addTab(self._pt_panel,    t("admin_tab_part_types"))
        self._tabs.addTab(self._mdl_panel,   t("admin_tab_models"))
        self._tabs.addTab(self._scan_panel,  t("admin_tab_scan"))

        lay.addWidget(self._tabs)

        # Propagate change signals outward
        self._shop_panel.settings_saved.connect(self.settings_changed)
        self._cat_panel.categories_changed.connect(self._on_cat_changed)

        # When switching to Part Types tab, reload its category list
        self._tabs.currentChanged.connect(self._on_tab_switch)

    def _on_cat_changed(self) -> None:
        self._pt_panel.reload()
        self._mdl_panel.reload()
        self.settings_changed.emit()

    def _on_tab_switch(self, index: int) -> None:
        if index == 2:    # Part Types tab
            self._pt_panel.reload()
        elif index == 3:  # Models tab
            self._mdl_panel.reload()


def open_admin(parent=None) -> bool:
    """
    PIN-gate check then open admin dialog.
    Returns True if dialog was opened (PIN OK or no PIN set).
    """
    cfg = ShopConfig.get()
    if cfg.admin_pin:
        pin, ok = QInputDialog.getText(
            parent, t("pin_title"), t("pin_prompt"),
            echo=QInputDialog.InputMode.Password if hasattr(QInputDialog, "InputMode")
            else __import__("PyQt6.QtWidgets", fromlist=["QLineEdit"]).QLineEdit.EchoMode.Password,
        )
        if not ok:
            return False
        if pin != cfg.admin_pin:
            QMessageBox.warning(parent, t("pin_title"), t("pin_wrong"))
            return False

    dlg = AdminDialog(parent)
    dlg.exec()
    return True
