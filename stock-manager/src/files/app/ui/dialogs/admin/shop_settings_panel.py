"""
app/ui/dialogs/admin/shop_settings_panel.py — Professional shop settings with card-based sections.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QFrame,
    QLineEdit, QComboBox, QPushButton, QLabel, QFileDialog,
    QScrollArea, QSizePolicy, QSpinBox, QCheckBox,
)
from PyQt6.QtCore import pyqtSignal, Qt

from app.core.config import ShopConfig
from app.core.theme import THEME
from app.core.i18n import t
from app.services.backup_service import BackupService

_backup_svc = BackupService()


# ── Reusable form card ──────────────────────────────────────────────────────

class _FormCard(QFrame):
    """Card container for a group of form fields."""

    def __init__(self, title: str, description: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("admin_form_card")
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(20, 16, 20, 16)
        self._lay.setSpacing(4)

        self._title = QLabel(title)
        self._title.setObjectName("admin_form_card_title")
        self._lay.addWidget(self._title)

        if description:
            desc = QLabel(description)
            desc.setObjectName("admin_form_card_desc")
            desc.setWordWrap(True)
            self._lay.addWidget(desc)

        self._form = QFormLayout()
        self._form.setSpacing(10)
        self._form.setContentsMargins(0, 8, 0, 0)
        self._lay.addLayout(self._form)

    @property
    def form(self) -> QFormLayout:
        return self._form

    def add_widget(self, widget: QWidget) -> None:
        self._lay.addWidget(widget)


# ── Panel ───────────────────────────────────────────────────────────────────

class ShopSettingsPanel(QWidget):
    """Professional shop settings with grouped card sections."""

    settings_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setObjectName("analytics_scroll")
        inner = QWidget()
        scroll.setWidget(inner)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        outer = QVBoxLayout(inner)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(16)

        # ── Header ──
        hdr_frame = QFrame()
        hdr_frame.setObjectName("admin_panel_header")
        hdr_lay = QHBoxLayout(hdr_frame)
        hdr_lay.setContentsMargins(0, 0, 0, 0)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel(t("admin_tab_shop"))
        title.setObjectName("admin_content_title")
        title_col.addWidget(title)
        subtitle = QLabel(
            t("shop_panel_desc")
            if t("shop_panel_desc") != "shop_panel_desc"
            else "Configure your shop identity, currency, language, and security"
        )
        subtitle.setObjectName("admin_content_desc")
        title_col.addWidget(subtitle)
        hdr_lay.addLayout(title_col)
        hdr_lay.addStretch()

        self._save_btn = QPushButton(f"  {t('shop_btn_save')}")
        self._save_btn.setObjectName("admin_action_btn")
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.clicked.connect(self._save)
        hdr_lay.addWidget(self._save_btn)
        outer.addWidget(hdr_frame)

        # ── Card: Business Information ──
        biz_card = _FormCard(
            t("shop_card_business") if t("shop_card_business") != "shop_card_business"
            else "Business Information",
            t("shop_card_business_desc") if t("shop_card_business_desc") != "shop_card_business_desc"
            else "Your shop name, logo, and contact details",
        )
        self._name = QLineEdit()
        self._name.setPlaceholderText(t("shop_lbl_name"))
        biz_card.form.addRow(t("shop_lbl_name"), self._name)

        logo_row = QHBoxLayout()
        logo_row.setSpacing(6)
        self._logo = QLineEdit()
        self._logo.setPlaceholderText(t("shop_lbl_logo"))
        browse_btn = QPushButton(t("shop_lbl_browse"))
        browse_btn.setObjectName("btn_ghost")
        browse_btn.setFixedWidth(110)
        browse_btn.clicked.connect(self._browse_logo)
        logo_row.addWidget(self._logo)
        logo_row.addWidget(browse_btn)
        biz_card.form.addRow(t("shop_lbl_logo"), logo_row)

        self._contact = QLineEdit()
        self._contact.setPlaceholderText(t("shop_lbl_contact"))
        biz_card.form.addRow(t("shop_lbl_contact"), self._contact)
        outer.addWidget(biz_card)

        # ── Card: Regional & Display ──
        regional_card = _FormCard(
            t("shop_card_regional") if t("shop_card_regional") != "shop_card_regional"
            else "Regional & Display",
            t("shop_card_regional_desc") if t("shop_card_regional_desc") != "shop_card_regional_desc"
            else "Currency, language, and theme preferences",
        )
        self._currency = QLineEdit()
        self._currency.setMaxLength(4)
        self._currency.setPlaceholderText("€")
        regional_card.form.addRow(t("shop_lbl_currency"), self._currency)

        self._cur_pos = QComboBox()
        self._cur_pos.addItem(t("shop_cur_prefix"), "prefix")
        self._cur_pos.addItem(t("shop_cur_suffix"), "suffix")
        regional_card.form.addRow(t("shop_lbl_cur_pos"), self._cur_pos)

        self._lang = QComboBox()
        for code, label in (("EN", "English"), ("DE", "Deutsch"), ("AR", "العربية")):
            self._lang.addItem(label, code)
        regional_card.form.addRow(t("shop_lbl_language"), self._lang)

        self._theme = QComboBox()
        self._theme.addItem(t("shop_theme_pro_dark"), "pro_dark")
        self._theme.addItem(t("shop_theme_pro_light"), "pro_light")
        self._theme.addItem(t("shop_theme_dark"), "dark")
        self._theme.addItem(t("shop_theme_light"), "light")
        self._theme.currentIndexChanged.connect(self._preview_theme)
        regional_card.form.addRow(t("shop_lbl_theme"), self._theme)

        # ── UI Scale (whole-app size, requires restart) ──
        self._ui_scale = QComboBox()
        self._ui_scale.addItem("Small (85%)", "small")
        self._ui_scale.addItem("Normal (100%)", "normal")
        self._ui_scale.addItem("Large (115%)", "large")
        self._ui_scale.addItem("Extra Large (130%)", "xlarge")
        self._ui_scale.setToolTip(
            "Overall app size — sidebar, header, footer, and base font.\n"
            "Takes effect after restarting the application."
        )
        regional_card.form.addRow("UI Scale", self._ui_scale)

        # ── Show sell totals (matrix) ──
        # When off, the TOTAL column in the matrix table and the value
        # portion of the part-type cards + the grand-total card are hidden,
        # so shop assistants can see stock without seeing valuation.
        # Cost totals have their own separate PIN-gated toggle (COST column).
        self._show_sell_totals = QCheckBox()
        self._show_sell_totals.setToolTip(
            "Show the TOTAL column and value on part-type cards in matrix tabs.\n"
            "Turn off to hide sell valuations from shop assistants.\n"
            "Units / stock counts stay visible either way."
        )
        regional_card.form.addRow(
            "Show sell totals in matrix", self._show_sell_totals
        )

        # Theme preview swatch
        self._preview_frame = QFrame()
        self._preview_frame.setFixedHeight(48)
        self._preview_frame.setObjectName("theme_preview_swatch")
        preview_lay = QHBoxLayout(self._preview_frame)
        preview_lay.setContentsMargins(12, 6, 12, 6)
        preview_lay.setSpacing(8)
        self._prev_bg = QLabel()
        self._prev_bg.setFixedSize(28, 28)
        self._prev_accent = QLabel()
        self._prev_accent.setFixedSize(28, 28)
        self._prev_text = QLabel()
        self._prev_text.setFixedSize(28, 28)
        self._prev_label = QLabel()
        self._prev_label.setObjectName("admin_form_card_desc")
        preview_lay.addWidget(self._prev_bg)
        preview_lay.addWidget(self._prev_accent)
        preview_lay.addWidget(self._prev_text)
        preview_lay.addWidget(self._prev_label, 1)
        regional_card.add_widget(self._preview_frame)
        outer.addWidget(regional_card)

        # ── Card: Security ──
        sec_card = _FormCard(
            t("shop_card_security") if t("shop_card_security") != "shop_card_security"
            else "Security",
            t("shop_card_security_desc") if t("shop_card_security_desc") != "shop_card_security_desc"
            else "Admin PIN protects access to these settings",
        )
        self._pin = QLineEdit()
        self._pin.setEchoMode(QLineEdit.EchoMode.Password)
        self._pin.setPlaceholderText("····")
        sec_card.form.addRow(t("shop_lbl_pin"), self._pin)
        outer.addWidget(sec_card)

        # ── Card: Auto-Backup ──
        backup_card = _FormCard(
            t("shop_card_backup"),
            t("shop_card_backup_desc"),
        )
        self._backup_enabled = QCheckBox()
        backup_card.form.addRow(t("shop_lbl_backup_enabled"), self._backup_enabled)

        self._backup_interval = QSpinBox()
        self._backup_interval.setRange(1, 168)   # 1 h – 1 week
        self._backup_interval.setSuffix(" h")
        self._backup_interval.setValue(24)
        backup_card.form.addRow(t("shop_lbl_backup_interval"), self._backup_interval)

        self._backup_retain = QSpinBox()
        self._backup_retain.setRange(1, 100)
        self._backup_retain.setValue(10)
        backup_card.form.addRow(t("shop_lbl_backup_retain"), self._backup_retain)

        backup_dir_row = QHBoxLayout()
        backup_dir_row.setSpacing(6)
        self._backup_dir = QLineEdit()
        self._backup_dir.setPlaceholderText(t("shop_lbl_backup_dir"))
        browse_backup_btn = QPushButton(t("shop_lbl_browse"))
        browse_backup_btn.setObjectName("btn_ghost")
        browse_backup_btn.setFixedWidth(110)
        browse_backup_btn.clicked.connect(self._browse_backup_dir)
        backup_dir_row.addWidget(self._backup_dir)
        backup_dir_row.addWidget(browse_backup_btn)
        backup_card.form.addRow(t("shop_lbl_backup_dir"), backup_dir_row)

        # Manual trigger button + last-backup label
        backup_btn_row = QHBoxLayout()
        backup_btn_row.setSpacing(8)
        self._backup_now_btn = QPushButton(t("shop_backup_now"))
        self._backup_now_btn.setObjectName("btn_secondary")
        self._backup_now_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._backup_now_btn.clicked.connect(self._do_backup_now)
        self._last_backup_lbl = QLabel()
        self._last_backup_lbl.setObjectName("admin_kpi_sub")
        backup_btn_row.addWidget(self._backup_now_btn)
        backup_btn_row.addWidget(self._last_backup_lbl, 1)
        backup_card.add_widget(self._wrap(backup_btn_row))
        outer.addWidget(backup_card)

        # ── Feedback ──
        self._feedback = QLabel("")
        self._feedback.setObjectName("admin_kpi_sub")
        outer.addWidget(self._feedback)

        outer.addStretch()

    # ── Data ────────────────────────────────────────────────────────────────

    @staticmethod
    def _wrap(layout) -> QWidget:
        """Wrap a QLayout in a QWidget for embedding inside add_widget()."""
        w = QWidget()
        w.setLayout(layout)
        return w

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
        self._original_theme = cfg.theme  # remember for revert on cancel
        self._preview_theme()
        # UI Scale
        idx = self._ui_scale.findData(cfg.ui_scale or "normal")
        self._ui_scale.setCurrentIndex(max(0, idx))
        self._original_ui_scale = cfg.ui_scale or "normal"
        # Show sell totals
        self._show_sell_totals.setChecked(cfg.is_show_sell_totals)
        self._pin.setText(cfg.admin_pin)
        self._contact.setText(cfg.contact_info)
        # Auto-backup
        self._backup_enabled.setChecked(cfg.is_auto_backup_enabled)
        self._backup_interval.setValue(cfg.auto_backup_interval_hours_int)
        self._backup_retain.setValue(cfg.auto_backup_retain_int)
        self._backup_dir.setText(cfg.auto_backup_dir)
        self._refresh_last_backup_label()

    def _preview_theme(self) -> None:
        """Show a live color swatch when the theme dropdown changes."""
        from app.core.theme import THEMES
        theme_key = self._theme.currentData()
        if not theme_key:
            return
        tokens = THEMES.get(theme_key)
        if not tokens:
            return
        # Apply live preview to main window
        THEME.set_theme(theme_key)
        main_win = self.window()
        if main_win:
            THEME.apply(main_win)
        # Update color swatches
        self._prev_bg.setStyleSheet(
            f"background: {tokens.card}; border-radius: 4px; border: 1px solid {tokens.border};"
        )
        self._prev_accent.setStyleSheet(
            f"background: {tokens.green}; border-radius: 4px;"
        )
        self._prev_text.setStyleSheet(
            f"background: {tokens.t1}; border-radius: 4px;"
        )
        names = {"pro_dark": "Pro Dark", "pro_light": "Pro Light",
                 "dark": "Classic Dark", "light": "Classic Light"}
        self._prev_label.setText(
            f"{names.get(theme_key, theme_key)} — "
            f"BG: {tokens.card}  |  Accent: {tokens.green}"
        )

    def _browse_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("shop_lbl_logo"), "",
            "Images (*.png *.jpg *.jpeg *.ico *.bmp *.svg)",
        )
        if path:
            self._logo.setText(path)

    def _save(self) -> None:
        cfg = ShopConfig()
        cfg.name = self._name.text().strip()
        cfg.logo_path = self._logo.text().strip()
        cfg.currency = self._currency.text().strip() or "€"
        cfg.currency_position = self._cur_pos.currentData()
        cfg.default_language = self._lang.currentData()
        cfg.theme = self._theme.currentData()
        cfg.ui_scale = self._ui_scale.currentData()
        cfg.show_sell_totals = "1" if self._show_sell_totals.isChecked() else "0"
        cfg.admin_pin = self._pin.text()
        cfg.contact_info = self._contact.text().strip()
        # Auto-backup
        cfg.auto_backup_enabled = "1" if self._backup_enabled.isChecked() else "0"
        cfg.auto_backup_interval_hours = str(self._backup_interval.value())
        cfg.auto_backup_retain = str(self._backup_retain.value())
        cfg.auto_backup_dir = self._backup_dir.text().strip()
        # Detect UI scale change — requires restart
        ui_scale_changed = (
            self._ui_scale.currentData()
            != getattr(self, "_original_ui_scale", "normal")
        )
        cfg.save()
        ShopConfig.invalidate()
        if ui_scale_changed:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self, "UI Scale changed",
                "The new UI Scale will take effect after restarting the application.",
            )
            self._original_ui_scale = self._ui_scale.currentData()
        self._feedback.setText(
            t("shop_saved") if t("shop_saved") != "shop_saved" else "✓ Settings saved"
        )
        self.settings_saved.emit()

    def _browse_backup_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, t("shop_lbl_backup_dir"),
            self._backup_dir.text() or "",
        )
        if path:
            self._backup_dir.setText(path)

    def _do_backup_now(self) -> None:
        """Manual 'Back Up Now' trigger from UI."""
        cfg = ShopConfig.get()
        retain = cfg.auto_backup_retain_int
        backup_dir = self._backup_dir.text().strip() or None
        try:
            _backup_svc.auto_backup(retain=retain, backup_dir=backup_dir)
            self._feedback.setText(t("shop_backup_done"))
            self._refresh_last_backup_label()
        except Exception as exc:
            self._feedback.setText(f"{t('shop_backup_fail')}: {exc}")

    def _refresh_last_backup_label(self) -> None:
        last = _backup_svc.get_last_backup_time()
        if last:
            ts = last.strftime("%Y-%m-%d %H:%M")
            self._last_backup_lbl.setText(t("shop_backup_last", ts=ts))
        else:
            self._last_backup_lbl.setText(t("shop_backup_never"))

    def reload(self) -> None:
        self._load()
        self._feedback.setText("")
