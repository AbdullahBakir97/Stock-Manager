"""
app/ui/components/filter_bar.py — Professional modern filter bar with search, status, sort, and active filter count.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox, QPushButton,
    QLabel, QFrame, QDoubleSpinBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from app.core.theme import THEME, _rgba
from app.core.i18n import t, LANG
from app.repositories.category_repo import CategoryRepository


class FilterBar(QWidget):
    """
    Professional modern filter bar with:
    - Debounced search input (stretch=3) with search icon placeholder
    - Status filter dropdown (fixed 150px) with 5 states
    - Sort dropdown (fixed 160px) with 7 sort options
    - Reset button (appears prominent when filters active)
    - Active filter count badge

    Signals:
        filters_changed(dict): Emitted when any filter changes.
            Keys: search (str), status (str), sort_by (str)
    """

    filters_changed = pyqtSignal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(300)
        self._debounce.timeout.connect(self._on_search_debounce)
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        tk = THEME.tokens

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # ── Main row: search + dropdowns + buttons (no container frame) ──
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        _H = 26

        # Search (compact, no border frame)
        self._search = QLineEdit()
        self._search.setObjectName("search_bar")
        self._search.setPlaceholderText(t("filter_search_placeholder"))
        self._search.setFixedHeight(_H)
        self._search.setMaximumWidth(280)
        row.addWidget(self._search, stretch=1)

        # Status
        self._status = QComboBox()
        self._status.setObjectName("filter_combo")
        self._status.setFixedHeight(_H)
        self._populate_status()
        row.addWidget(self._status)

        # Sort
        self._sort = QComboBox()
        self._sort.setObjectName("filter_combo")
        self._sort.setFixedHeight(_H)
        self._populate_sort()
        row.addWidget(self._sort)

        # Category
        self._category = QComboBox()
        self._category.setObjectName("filter_combo")
        self._category.setFixedHeight(_H)
        self._populate_categories()
        row.addWidget(self._category)

        row.addStretch()

        # Reset (visible text button)
        self._reset_btn = QPushButton(t("filter_reset"))
        self._reset_btn.setObjectName("btn_ghost")
        self._reset_btn.setFixedHeight(_H)
        self._reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        row.addWidget(self._reset_btn)

        layout.addLayout(row)

        # ── Hidden advanced toggle (keep for compat but not shown) ──
        self._adv_toggle = QPushButton()
        self._adv_toggle.hide()
        self._adv_toggle.setCheckable(True)

        # ── Active filter count badge (hidden — for compat) ──
        self._count_badge = QLabel()
        self._count_badge.hide()

        # ── Hidden advanced frame (for compat) ──
        self._adv_frame = QFrame()
        self._adv_frame.hide()

        # ── Price range (hidden spinboxes — for compat with get_filters) ──
        self._price_min = QDoubleSpinBox()
        self._price_min.setRange(0, 99999)
        self._price_min.setValue(0)
        self._price_min.setDecimals(0)
        self._price_min.hide()

        self._price_max = QDoubleSpinBox()
        self._price_max.setRange(0, 99999)
        self._price_max.setValue(0)
        self._price_max.setDecimals(0)
        self._price_max.hide()

    def _populate_categories(self) -> None:
        """Populate category dropdown from database."""
        self._category.addItem(t("filter_all_categories"), "all")
        self._category.addItem(t("filter_products_only"), "products")
        try:
            cats = CategoryRepository().get_all_active()
            for cat in cats:
                self._category.addItem(cat.name(LANG), f"cat_{cat.key}")
        except Exception:
            pass

    def _populate_status(self) -> None:
        """Populate status dropdown with all 5 states."""
        self._status.addItem(t("filter_all_status"), "all")
        self._status.addItem(f"✓ {t('filter_status_in_stock')}", "in_stock")
        self._status.addItem(f"⚠ {t('filter_status_low_stock')}", "low_stock")
        self._status.addItem(f"🔴 {t('filter_status_critical')}", "critical")
        self._status.addItem(f"⛔ {t('filter_status_out_of_stock')}", "out_of_stock")

    def _populate_sort(self) -> None:
        """Populate sort dropdown with 7 sort options."""
        self._sort.addItem(t("filter_sort_name_asc"), "name_asc")
        self._sort.addItem(t("filter_sort_name_desc"), "name_desc")
        self._sort.addItem(t("filter_sort_stock_asc"), "stock_asc")
        self._sort.addItem(t("filter_sort_stock_desc"), "stock_desc")
        self._sort.addItem(t("filter_sort_price_asc"), "price_asc")
        self._sort.addItem(t("filter_sort_price_desc"), "price_desc")
        self._sort.addItem(t("filter_sort_updated_desc"), "updated_desc")

    def _style_combo(self, combo: QComboBox) -> None:
        """Apply consistent modern styling to combo boxes."""
        tk = THEME.tokens
        combo.setStyleSheet(f"""
            QComboBox {{
                background: {tk.card2};
                color: {tk.t1};
                border: 1px solid {tk.border};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
            }}
            QComboBox:hover {{
                border: 1px solid {tk.blue};
            }}
            QComboBox:focus {{
                border: 1px solid {tk.blue};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
                image: none;
            }}
            QComboBox::down-arrow {{
                image: none;
            }}
            QComboBox QAbstractItemView {{
                background: {tk.card};
                color: {tk.t1};
                border: 1px solid {tk.border};
                border-radius: 6px;
                selection-background-color: {_rgba(tk.blue, '25')};
                selection-color: {tk.blue};
                outline: none;
                padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 6px 12px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background: {_rgba(tk.blue, '15')};
            }}
            QComboBox QAbstractItemView::item:selected {{
                background: {_rgba(tk.blue, '25')};
            }}
        """)

    def _connect_signals(self) -> None:
        """Connect all signals."""
        self._search.textChanged.connect(self._on_search_changed)
        self._status.currentIndexChanged.connect(self._on_filter_changed)
        self._sort.currentIndexChanged.connect(self._on_filter_changed)
        self._category.currentIndexChanged.connect(self._on_filter_changed)
        self._price_min.valueChanged.connect(self._on_price_changed)
        self._price_max.valueChanged.connect(self._on_price_changed)
        self._reset_btn.clicked.connect(self.reset)
        self._adv_toggle.toggled.connect(self._toggle_advanced)

    def _toggle_advanced(self, checked: bool) -> None:
        """Show/hide the advanced filter row."""
        self._adv_frame.setVisible(checked)

    def _on_price_changed(self) -> None:
        """Handle price range change with short debounce."""
        self._debounce.stop()
        self._debounce.start()

    def _on_search_changed(self) -> None:
        """Handle search text change with debounce."""
        self._debounce.stop()
        self._debounce.start()

    def _on_search_debounce(self) -> None:
        """Debounced search emission."""
        self._update_active_count()
        self.filters_changed.emit(self.get_filters())

    def _on_filter_changed(self) -> None:
        """Handle status or sort change (no debounce)."""
        self._update_active_count()
        self.filters_changed.emit(self.get_filters())

    def _update_active_count(self) -> None:
        """Update the active filter count badge."""
        active = 0
        if self._search.text().strip():
            active += 1
        if self._status.currentData() != "all":
            active += 1
        if self._category.currentData() != "all":
            active += 1
        if self._price_min.value() > 0:
            active += 1
        if self._price_max.value() > 0:
            active += 1

        if active > 0:
            self._count_badge.setText(str(active))
            self._count_badge.show()
        else:
            self._count_badge.hide()

    # ── Public API ──────────────────────────────────────────

    def get_filters(self) -> dict:
        """Return current filter state as a dict."""
        return {
            "search": self._search.text().strip(),
            "status": self._status.currentData(),
            "sort_by": self._sort.currentData(),
            "category": self._category.currentData(),
            "price_min": self._price_min.value(),
            "price_max": self._price_max.value(),
        }

    def reset(self) -> None:
        """Clear all filters and reset to defaults."""
        for w in (self._search, self._status, self._sort,
                  self._category, self._price_min, self._price_max):
            w.blockSignals(True)

        self._search.clear()
        self._status.setCurrentIndex(0)
        self._sort.setCurrentIndex(0)
        self._category.setCurrentIndex(0)
        self._price_min.setValue(0)
        self._price_max.setValue(0)

        for w in (self._search, self._status, self._sort,
                  self._category, self._price_min, self._price_max):
            w.blockSignals(False)

        self._update_active_count()
        self.filters_changed.emit(self.get_filters())

    def set_search(self, text: str) -> None:
        """Set search text programmatically."""
        self._search.setText(text)

    def retranslate(self) -> None:
        """Update all text for language change. Called from main_window."""
        self._search.setPlaceholderText(t("filter_search_placeholder"))
        self._reset_btn.setText(t("filter_reset"))

        for combo, data_attr, populate_fn in [
            (self._status, "currentData", self._populate_status),
            (self._sort, "currentData", self._populate_sort),
            (self._category, "currentData", self._populate_categories),
        ]:
            current = combo.currentData()
            combo.blockSignals(True)
            combo.clear()
            populate_fn()
            idx = combo.findData(current)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            combo.blockSignals(False)
