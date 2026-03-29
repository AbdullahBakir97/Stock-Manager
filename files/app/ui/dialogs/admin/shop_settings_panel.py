"""
app/ui/dialogs/admin/shop_settings_panel.py — Shop branding and config panel.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout,
    QLineEdit, QComboBox, QPushButton, QLabel, QFileDialog,
)
from PyQt6.QtCore import pyqtSignal

from app.core.config import ShopConfig
from app.core.i18n import t


class ShopSettingsPanel(QWidget):
    """Tab panel for shop name, logo, currency, language, theme, PIN, contact."""

    settings_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(12)
        form.setContentsMargins(0, 0, 0, 0)

        # Shop name
        self._name = QLineEdit()
        form.addRow(t("shop_lbl_name"), self._name)

        # Logo path + browse button
        logo_row = QHBoxLayout(); logo_row.setSpacing(6)
        self._logo = QLineEdit()
        browse_btn = QPushButton(t("shop_lbl_browse"))
        browse_btn.setFixedWidth(110)
        browse_btn.clicked.connect(self._browse_logo)
        logo_row.addWidget(self._logo)
        logo_row.addWidget(browse_btn)
        form.addRow(t("shop_lbl_logo"), logo_row)

        # Currency symbol
        self._currency = QLineEdit(); self._currency.setMaxLength(4)
        form.addRow(t("shop_lbl_currency"), self._currency)

        # Currency position
        self._cur_pos = QComboBox()
        self._cur_pos.addItem(t("shop_cur_prefix"), "prefix")
        self._cur_pos.addItem(t("shop_cur_suffix"), "suffix")
        form.addRow(t("shop_lbl_cur_pos"), self._cur_pos)

        # Default language
        self._lang = QComboBox()
        for code, label in (("EN", "English"), ("DE", "Deutsch"), ("AR", "العربية")):
            self._lang.addItem(label, code)
        form.addRow(t("shop_lbl_language"), self._lang)

        # Theme
        self._theme = QComboBox()
        self._theme.addItem(t("shop_theme_dark"), "dark")
        self._theme.addItem(t("shop_theme_light"), "light")
        form.addRow(t("shop_lbl_theme"), self._theme)

        # Admin PIN
        self._pin = QLineEdit(); self._pin.setEchoMode(QLineEdit.EchoMode.Password)
        self._pin.setPlaceholderText("····")
        form.addRow(t("shop_lbl_pin"), self._pin)

        # Contact info
        self._contact = QLineEdit()
        form.addRow(t("shop_lbl_contact"), self._contact)

        outer.addLayout(form)
        outer.addStretch()

        # Save button + feedback label
        btn_row = QHBoxLayout()
        self._save_btn = QPushButton(t("shop_btn_save"))
        self._save_btn.setObjectName("btn_primary")
        self._save_btn.clicked.connect(self._save)
        self._feedback = QLabel("")
        self._feedback.setObjectName("card_meta_dim")
        btn_row.addStretch()
        btn_row.addWidget(self._feedback)
        btn_row.addWidget(self._save_btn)
        outer.addLayout(btn_row)

    def _load(self) -> None:
        cfg = ShopConfig.get()
        self._name.setText(cfg.name)
        self._logo.setText(cfg.logo_path)
        self._currency.setText(cfg.currency)
        idx = self._cur_pos.findData(cfg.currency_position)
        self._cur_pos.setCurrentIndex(max(0, idx))
        idx = self._lang.findData(cfg.default_language)
        self._lang.setCurrentIndex(max(0, idx))
        idx = self._theme.findData(cfg.theme)
        self._theme.setCurrentIndex(max(0, idx))
        self._pin.setText(cfg.admin_pin)
        self._contact.setText(cfg.contact_info)

    def _browse_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("shop_lbl_logo"), "",
            "Images (*.png *.jpg *.jpeg *.ico *.bmp *.svg)"
        )
        if path:
            self._logo.setText(path)

    def _save(self) -> None:
        cfg = ShopConfig()
        cfg.name              = self._name.text().strip()
        cfg.logo_path         = self._logo.text().strip()
        cfg.currency          = self._currency.text().strip() or "€"
        cfg.currency_position = self._cur_pos.currentData()
        cfg.default_language  = self._lang.currentData()
        cfg.theme             = self._theme.currentData()
        cfg.admin_pin         = self._pin.text()
        cfg.contact_info      = self._contact.text().strip()
        cfg.save()
        ShopConfig.invalidate()
        self._feedback.setText(t("shop_saved"))
        self.settings_saved.emit()

    def reload(self) -> None:
        """Refresh from DB (called after external changes)."""
        self._load()
        self._feedback.setText("")
