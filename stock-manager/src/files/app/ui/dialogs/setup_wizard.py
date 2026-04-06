"""
app/ui/dialogs/setup_wizard.py — First-run setup wizard (3 pages).

Shown once on a fresh install. Non-closable until "Finish Setup" is pressed.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QLabel, QLineEdit, QComboBox, QRadioButton, QPushButton,
    QButtonGroup, QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.core.config import ShopConfig
from app.core.database import get_connection, load_demo_data
from app.core.theme import THEME
from app.core.i18n import t, set_lang


class SetupWizard(QDialog):
    """3-page first-run wizard. Non-closable until "Finish Setup" is clicked."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("wizard_welcome_title"))
        self.setModal(True)
        self.setMinimumSize(500, 380)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint
        )
        THEME.apply(self)
        self._build_ui()

    def closeEvent(self, event) -> None:
        """Prevent closing the wizard without completing setup."""
        event.ignore()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._page_welcome())
        self._stack.addWidget(self._page_shop())
        self._stack.addWidget(self._page_data())
        outer.addWidget(self._stack, 1)

        # Navigation buttons
        nav = QHBoxLayout(); nav.setContentsMargins(20, 12, 20, 16); nav.setSpacing(8)
        self._back_btn = QPushButton(t("wizard_btn_back"))
        self._back_btn.clicked.connect(self._go_back)
        self._next_btn = QPushButton(t("wizard_btn_start"))
        self._next_btn.setObjectName("btn_primary")
        self._next_btn.clicked.connect(self._go_next)
        nav.addWidget(self._back_btn)
        nav.addStretch()
        nav.addWidget(self._next_btn)
        outer.addLayout(nav)

        self._back_btn.hide()

    # ── Pages ──────────────────────────────────────────────────────────────────

    def _page_welcome(self) -> QWidget:
        from PyQt6.QtWidgets import QWidget
        page = QWidget()
        lay = QVBoxLayout(page); lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setContentsMargins(48, 40, 48, 20); lay.setSpacing(16)

        title = QLabel(t("wizard_welcome_title"))
        title.setObjectName("app_title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        lay.addWidget(title)

        sub = QLabel(t("wizard_welcome_sub"))
        sub.setObjectName("card_meta_dim")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(sub)
        return page

    def _page_shop(self) -> QWidget:
        from PyQt6.QtWidgets import QWidget, QFormLayout
        page = QWidget()
        lay = QVBoxLayout(page); lay.setContentsMargins(48, 30, 48, 20); lay.setSpacing(16)

        title = QLabel(t("wizard_shop_title"))
        title.setObjectName("dlg_header"); title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        form = QFormLayout(); form.setSpacing(12)
        self._shop_name = QLineEdit()
        self._shop_name.setPlaceholderText(t("wizard_shop_name_ph"))
        form.addRow(t("shop_lbl_name"), self._shop_name)

        self._shop_currency = QLineEdit("€"); self._shop_currency.setMaxLength(4)
        form.addRow(t("shop_lbl_currency"), self._shop_currency)

        self._shop_lang = QComboBox()
        for code, label in (("EN", "English"), ("DE", "Deutsch"), ("AR", "العربية")):
            self._shop_lang.addItem(label, code)
        form.addRow(t("shop_lbl_language"), self._shop_lang)

        lay.addLayout(form)
        lay.addStretch()
        return page

    def _page_data(self) -> QWidget:
        from PyQt6.QtWidgets import QWidget
        page = QWidget()
        lay = QVBoxLayout(page); lay.setContentsMargins(48, 30, 48, 20); lay.setSpacing(16)

        title = QLabel(t("wizard_data_title"))
        title.setObjectName("dlg_header"); title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        self._grp = QButtonGroup(self)
        self._opt_fresh = QRadioButton(t("wizard_opt_fresh"))
        self._opt_demo  = QRadioButton(t("wizard_opt_demo"))
        self._opt_fresh.setChecked(True)
        self._grp.addButton(self._opt_fresh)
        self._grp.addButton(self._opt_demo)

        lay.addWidget(self._opt_fresh)
        lay.addWidget(self._opt_demo)
        lay.addStretch()
        return page

    # ── Navigation ─────────────────────────────────────────────────────────────

    def _go_next(self) -> None:
        idx = self._stack.currentIndex()
        if idx == 0:
            self._stack.setCurrentIndex(1)
            self._back_btn.show()
            self._next_btn.setText(t("wizard_btn_start"))
        elif idx == 1:
            if not self._shop_name.text().strip():
                QMessageBox.warning(self, t("dlg_required_title"), t("shop_lbl_name"))
                return
            self._stack.setCurrentIndex(2)
            self._next_btn.setText(t("wizard_btn_finish"))
        elif idx == 2:
            self._finish()

    def _go_back(self) -> None:
        idx = self._stack.currentIndex()
        if idx == 1:
            self._stack.setCurrentIndex(0)
            self._back_btn.hide()
            self._next_btn.setText(t("wizard_btn_start"))
        elif idx == 2:
            self._stack.setCurrentIndex(1)
            self._next_btn.setText(t("wizard_btn_start"))

    def _finish(self) -> None:
        cfg = ShopConfig()
        cfg.name             = self._shop_name.text().strip() or t("wizard_default_name")
        cfg.currency         = self._shop_currency.text().strip() or "€"
        cfg.default_language = self._shop_lang.currentData()
        cfg.save()
        ShopConfig.invalidate()

        if self._opt_demo.isChecked():
            load_demo_data()

        with get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO app_config (key, value) VALUES ('setup_complete', '1')"
            )

        # Apply chosen language immediately
        set_lang(cfg.default_language)
        self.accept()
