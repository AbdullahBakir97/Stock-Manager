"""app/ui/dialogs/help_dialog.py — In-app help / user guide dialog."""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTextBrowser, QSplitter, QWidget,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor, QPainter

from app.core.theme import THEME, _rgba
from app.core.i18n import t


class HelpDialog(QDialog):
    """Modal help dialog with sidebar navigation and rich-text content."""

    _SECTIONS = [
        ("help_getting_started",   "help_getting_started_body"),
        ("help_inventory_page",    "help_inventory_page_body"),
        ("help_products",          "help_products_body"),
        ("help_product_images",    "help_product_images_body"),
        ("help_categories",        "help_categories_body"),
        ("help_part_types",        "help_part_types_body"),
        ("help_stock_ops",         "help_stock_ops_body"),
        ("help_quick_scan",        "help_quick_scan_body"),
        ("help_transactions",      "help_transactions_body"),
        ("help_barcode_gen",       "help_barcode_gen_body"),
        ("help_reports",           "help_reports_body"),
        ("help_analytics",         "help_analytics_body"),
        ("help_admin",             "help_admin_body"),
        ("help_import_export",     "help_import_export_body"),
        ("help_backup",            "help_backup_body"),
        ("help_shortcuts",         "help_shortcuts_body"),
        ("help_about",             "help_about_body"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("help_title"))
        self.setMinimumSize(820, 560)
        self.setModal(True)
        self._build()
        self._apply_style()
        # Select first section
        self._nav.setCurrentRow(0)

    def paintEvent(self, _ev):
        tk = THEME.tokens
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(tk.grad_top))
        p.end()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(12)

        # Header
        hdr_row = QHBoxLayout()
        hdr = QLabel(t("help_title"))
        hdr.setFont(QFont("Segoe UI", 16, QFont.Weight.DemiBold))
        hdr.setStyleSheet(f"color:{THEME.tokens.t1};")
        close_btn = QPushButton("×")
        close_btn.setObjectName("btn_close_x")
        close_btn.setFixedSize(32, 32)
        close_btn.clicked.connect(self.close)
        hdr_row.addWidget(hdr)
        hdr_row.addStretch()
        hdr_row.addWidget(close_btn)
        root.addLayout(hdr_row)

        # Splitter: nav list + content
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Navigation list
        self._nav = QListWidget()
        self._nav.setFixedWidth(200)
        self._nav.setSpacing(2)
        for title_key, _ in self._SECTIONS:
            item = QListWidgetItem(t(title_key))
            item.setSizeHint(QSize(170, 40))
            self._nav.addItem(item)
        self._nav.currentRowChanged.connect(self._show_section)

        # Content browser
        self._content = QTextBrowser()
        self._content.setOpenExternalLinks(True)
        self._content.setReadOnly(True)

        splitter.addWidget(self._nav)
        splitter.addWidget(self._content)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        # Close button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close = QPushButton(t("btn_close"))
        close.setObjectName("btn_ghost")
        close.setMinimumHeight(36)
        close.clicked.connect(self.close)
        btn_row.addWidget(close)
        root.addLayout(btn_row)

    def _show_section(self, index: int):
        if index < 0 or index >= len(self._SECTIONS):
            return
        title_key, body_key = self._SECTIONS[index]
        tk = THEME.tokens
        body = t(body_key)
        # Convert markdown-lite bold to HTML
        import re
        html = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', body)
        html = html.replace("\n\n", "<br><br>").replace("\n•", "<br>•")
        styled = (
            f"<div style='color:{tk.t1}; font-family:Segoe UI; font-size:13px; "
            f"line-height:1.6;'>"
            f"<h2 style='color:{tk.t1}; margin-bottom:12px;'>{t(title_key)}</h2>"
            f"{html}</div>"
        )
        self._content.setHtml(styled)

    def _apply_style(self):
        tk = THEME.tokens
        self._nav.setStyleSheet(
            f"QListWidget {{ background:{tk.card}; border:1px solid {tk.border};"
            f"border-radius:8px; color:{tk.t1}; font-size:12px; }}"
            f"QListWidget::item {{ padding:8px 12px; border-radius:6px; }}"
            f"QListWidget::item:selected {{ background:{_rgba(tk.green, '30')};"
            f"color:{tk.green}; font-weight:600; }}"
            f"QListWidget::item:hover {{ background:{_rgba(tk.t1, '08')}; }}"
        )
        self._content.setStyleSheet(
            f"QTextBrowser {{ background:{tk.card}; border:1px solid {tk.border};"
            f"border-radius:8px; padding:16px; color:{tk.t1}; }}"
        )
        THEME.register(self)
        self.setStyleSheet(THEME.stylesheet())
