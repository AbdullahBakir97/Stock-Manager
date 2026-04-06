"""
app/ui/components/filter_bar.py — Professional filter bar with search, category, status, and sort.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox,
    QPushButton, QLabel, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from app.core.theme import THEME, _rgba
from app.core.i18n import t


class FilterBar(QWidget):
    """
    Professional filter bar with debounced search, category/status dropdowns, and reset.

    Signals:
        filters_changed(dict): Emitted when any filter changes.
            Keys: search (str), status (str|None), sort_by (str)
    """

    filters_changed = pyqtSignal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(300)  # 300ms debounce for search
        self._debounce.timeout.connect(self._emit_filters)
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        tk = THEME.tokens

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Container frame with styling
        container = QFrame()
        container.setObjectName("filter_bar")
        container.setStyleSheet(f"""
            QFrame#filter_bar {{
                background: {tk.card};
                border: 1px solid {tk.border};
                border-radius: 10px;
                padding: 8px;
            }}
        """)

        row = QHBoxLayout(container)
        row.setContentsMargins(12, 8, 12, 8)
        row.setSpacing(10)

        # ── Search Input ────────────────────────────────────
        self._search = QLineEdit()
        self._search.setPlaceholderText(t("filter_search_placeholder"))
        self._search.setMinimumHeight(36)
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background: {tk.card2};
                color: {tk.t1};
                border: 1px solid {tk.border};
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {tk.blue};
                background: {tk.card};
            }}
            QLineEdit::placeholder {{
                color: {tk.t3};
            }}
        """)
        row.addWidget(self._search, stretch=3)

        # ── Status Filter ───────────────────────────────────
        self._status = QComboBox()
        self._status.setMinimumHeight(36)
        self._status.setMinimumWidth(130)
        self._status.addItem(t("filter_all_status"), "all")
        self._status.addItem("✓ OK", "ok")
        self._status.addItem("⚠ Low Stock", "low")
        self._status.addItem("🔴 Critical", "critical")
        self._status.addItem("⛔ Out of Stock", "out")
        self._style_combo(self._status)
        row.addWidget(self._status)

        # ── Sort By ─────────────────────────────────────────
        self._sort = QComboBox()
        self._sort.setMinimumHeight(36)
        self._sort.setMinimumWidth(140)
        self._sort.addItem("Sort: Name (A→Z)", "name_asc")
        self._sort.addItem("Sort: Name (Z→A)", "name_desc")
        self._sort.addItem("Sort: Stock (Low→High)", "stock_asc")
        self._sort.addItem("Sort: Stock (High→Low)", "stock_desc")
        self._sort.addItem("Sort: Price (Low→High)", "price_asc")
        self._sort.addItem("Sort: Price (High→Low)", "price_desc")
        self._sort.addItem("Sort: Updated (Recent)", "updated_desc")
        self._style_combo(self._sort)
        row.addWidget(self._sort)

        # ── Reset Button ────────────────────────────────────
        self._reset_btn = QPushButton(t("filter_reset"))
        self._reset_btn.setMinimumHeight(36)
        self._reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {tk.t2};
                border: 1px solid {tk.border};
                border-radius: 8px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {_rgba(tk.red, '15')};
                border-color: {tk.red};
                color: {tk.red};
            }}
        """)
        row.addWidget(self._reset_btn)

        # ── Active Filters Count ────────────────────────────
        self._count_lbl = QLabel()
        self._count_lbl.setStyleSheet(f"color: {tk.t3}; font-size: 11px;")
        self._count_lbl.hide()
        row.addWidget(self._count_lbl)

        main_layout.addWidget(container)

    def _style_combo(self, combo: QComboBox) -> None:
        tk = THEME.tokens
        combo.setStyleSheet(f"""
            QComboBox {{
                background: {tk.card2};
                color: {tk.t1};
                border: 1px solid {tk.border};
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
            }}
            QComboBox:hover {{
                border-color: {tk.blue};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background: {tk.card};
                color: {tk.t1};
                border: 1px solid {tk.border};
                selection-background-color: {_rgba(tk.blue, '30')};
                outline: none;
                padding: 4px;
            }}
        """)

    def _connect_signals(self) -> None:
        self._search.textChanged.connect(lambda: self._debounce.start())
        self._status.currentIndexChanged.connect(self._emit_filters)
        self._sort.currentIndexChanged.connect(self._emit_filters)
        self._reset_btn.clicked.connect(self.reset)

    def _emit_filters(self) -> None:
        active = 0
        if self._search.text().strip():
            active += 1
        if self._status.currentData() != "all":
            active += 1

        if active > 0:
            self._count_lbl.setText(f"{active} filter{'s' if active > 1 else ''} active")
            self._count_lbl.show()
        else:
            self._count_lbl.hide()

        self.filters_changed.emit(self.get_filters())

    # ── Public API ──────────────────────────────────────────

    def get_filters(self) -> dict:
        """Return current filter state as a dict."""
        return {
            "search": self._search.text().strip(),
            "status": self._status.currentData(),
            "sort_by": self._sort.currentData(),
        }

    def reset(self) -> None:
        """Clear all filters and reset to defaults."""
        self._search.clear()
        self._status.setCurrentIndex(0)
        self._sort.setCurrentIndex(0)
        self._count_lbl.hide()
        self._emit_filters()

    def set_search(self, text: str) -> None:
        """Set search text programmatically."""
        self._search.setText(text)

    def retranslate(self) -> None:
        """Update all text for language change. Called from main_window."""
        self._search.setPlaceholderText(t("filter_search_placeholder"))
        self._reset_btn.setText(t("filter_reset"))

        # Re-populate status combo while preserving selection
        current_status = self._status.currentData()
        self._status.clear()
        self._status.addItem(t("filter_all_status"), "all")
        self._status.addItem("✓ OK", "ok")
        self._status.addItem("⚠ Low Stock", "low")
        self._status.addItem("🔴 Critical", "critical")
        self._status.addItem("⛔ Out of Stock", "out")
        # Restore selection
        idx = self._status.findData(current_status)
        if idx >= 0:
            self._status.setCurrentIndex(idx)
