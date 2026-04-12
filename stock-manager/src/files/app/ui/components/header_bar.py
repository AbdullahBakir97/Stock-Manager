"""
app/ui/components/header_bar.py — Top header bar with search, lang, alerts, settings.
"""
from __future__ import annotations

import os

from PyQt6.QtWidgets import (
    QWidget, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap

from app.core.config import ShopConfig
from app.core.theme import THEME
from app.core.i18n import t, LANG
from app.core.icon_utils import get_button_icon
from app.ui.components.barcode_line_edit import BarcodeLineEdit
from app.ui.components.theme_toggle import ThemeToggle
from app.ui.components.language_switcher import LanguageSwitcher


class HeaderBar(QFrame):
    """56px top bar: hamburger, logo, title, search, lang, alerts, settings."""

    # Signals for parent to connect
    sidebar_toggled = pyqtSignal()
    lang_changed    = pyqtSignal(str)
    alerts_clicked  = pyqtSignal()
    refresh_clicked = pyqtSignal()
    theme_toggled   = pyqtSignal()
    admin_clicked   = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("header_bar")
        self.setFixedHeight(56)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._build()

    # ── Build ────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        hdr_lay = QHBoxLayout(self)
        hdr_lay.setContentsMargins(16, 0, 16, 0)
        hdr_lay.setSpacing(0)

        cfg = ShopConfig.get()
        _title = cfg.name if cfg.name else t("app_title")

        # ── Left: hamburger + logo + title (fixed width = sidebar 240px − left margin 16px) ──
        left_container = QWidget()
        left_container.setFixedWidth(224)   # aligns search with the content area at x=240
        left_container.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        left = QHBoxLayout(left_container)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(8)

        self.sidebar_toggle = QPushButton("☰")
        self.sidebar_toggle.setObjectName("header_icon")
        self.sidebar_toggle.setFixedSize(34, 34)
        self.sidebar_toggle.setToolTip(t("tooltip_toggle_sidebar"))
        self.sidebar_toggle.clicked.connect(self.sidebar_toggled.emit)
        left.addWidget(self.sidebar_toggle)

        self.logo_lbl = self._build_logo()
        if self.logo_lbl:
            left.addWidget(self.logo_lbl)

        self.title_lbl = QLabel(_title)
        self.title_lbl.setObjectName("app_title")
        left.addWidget(self.title_lbl)
        left.addStretch()
        hdr_lay.addWidget(left_container)

        # ── Search bar — left edge flush with content area (x=240) ─────────
        self.search = BarcodeLineEdit()
        self.search.setObjectName("search_bar")
        self.search.setFixedWidth(300)
        self.search.setFixedHeight(34)
        hdr_lay.addWidget(self.search)

        hdr_lay.addStretch()  # push right controls to far right

        # ── Right: lang, bell, refresh, theme, admin ─────────────────────
        right = QHBoxLayout(); right.setSpacing(8)

        # Language switcher — professional dropdown
        self._lang_switcher = LanguageSwitcher(current_lang=LANG)
        self._lang_switcher.lang_changed.connect(self.lang_changed.emit)
        right.addWidget(self._lang_switcher)
        right.addSpacing(4)

        # Notification bell
        self.notif_btn = QPushButton("🔔")
        self.notif_btn.setObjectName("header_icon")
        self.notif_btn.setFixedSize(34, 34)
        self.notif_btn.setToolTip(t("dlg_alerts_title"))
        self.notif_btn.clicked.connect(self.alerts_clicked.emit)
        self.notif_badge = QLabel("0", self.notif_btn)
        self.notif_badge.setObjectName("notif_badge")
        self.notif_badge.setFixedSize(18, 18)
        self.notif_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notif_badge.move(18, -2)
        self.notif_badge.hide()
        right.addWidget(self.notif_btn)

        # Refresh
        self.refresh_btn = QPushButton()
        self.refresh_btn.setObjectName("header_icon")
        self.refresh_btn.setFixedSize(34, 34)
        self.refresh_btn.setIcon(get_button_icon("refresh"))
        self.refresh_btn.setIconSize(QSize(16, 16))
        self.refresh_btn.setToolTip(t("tooltip_refresh"))
        self.refresh_btn.clicked.connect(self.refresh_clicked.emit)
        right.addWidget(self.refresh_btn)

        # Theme toggle
        self.theme_toggle = ThemeToggle()
        self.theme_toggle.theme_toggled.connect(self.theme_toggled.emit)
        right.addWidget(self.theme_toggle)

        # Admin/Settings
        self.admin_btn = QPushButton()
        self.admin_btn.setObjectName("header_icon")
        self.admin_btn.setFixedSize(34, 34)
        self.admin_btn.setIcon(get_button_icon("settings"))
        self.admin_btn.setIconSize(QSize(16, 16))
        self.admin_btn.setToolTip(t("tooltip_admin"))
        self.admin_btn.clicked.connect(self.admin_clicked.emit)
        right.addWidget(self.admin_btn)

        hdr_lay.addLayout(right)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _build_logo(self) -> QLabel | None:
        cfg = ShopConfig.get()
        path = cfg.logo_path
        if not path or not os.path.isfile(path):
            return None
        px = QPixmap(path)
        if px.isNull():
            return None
        lbl = QLabel()
        lbl.setPixmap(px.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation))
        lbl.setFixedSize(40, 40)
        return lbl

    def update_lang_buttons(self, lang: str) -> None:
        """Update the language switcher to reflect the newly active language."""
        self._lang_switcher.set_lang(lang)

    def retranslate(self) -> None:
        cfg = ShopConfig.get()
        _title = cfg.name if cfg.name else t("app_title")
        self.title_lbl.setText(_title)
        self.refresh_btn.setToolTip(t("tooltip_refresh"))
        self.admin_btn.setToolTip(t("tooltip_admin"))
        self.theme_toggle.setToolTip(t("tooltip_theme"))
        self.search.setPlaceholderText(t("search_placeholder"))
