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

        # Main vertical layout (search bar + advanced row stacked)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        container = QFrame()
        container.setObjectName("filter_bar_container")
        container.setStyleSheet(f"""
            QFrame#filter_bar_container {{
                background: {tk.card};
                border: 1px solid {tk.border};
                border-radius: 10px;
            }}
        """)

        row = QHBoxLayout(container)
        row.setContentsMargins(12, 8, 12, 8)
        row.setSpacing(12)

        # ── Search Input (stretch=3) ────────────────────────
        self._search = QLineEdit()
        self._search.setObjectName("filter_search_input")
        self._search.setPlaceholderText(f"🔍 {t('filter_search_placeholder')}")
        self._search.setMinimumHeight(38)
        self._search.setMaximumHeight(38)
        self._search.setStyleSheet(f"""
            QLineEdit#filter_search_input {{
                background: {tk.card2};
                color: {tk.t1};
                border: 1px solid {tk.border};
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 13px;
                font-family: "Segoe UI", "Helvetica", sans-serif;
            }}
            QLineEdit#filter_search_input:focus {{
                border: 2px solid {tk.blue};
                padding: 7px 13px;
                background: {tk.card2};
            }}
            QLineEdit#filter_search_input::placeholder {{
                color: {tk.t3};
            }}
        """)
        row.addWidget(self._search, stretch=3)

        # ── Status Filter Dropdown (fixed 150px) ────────────
        self._status = QComboBox()
        self._status.setObjectName("filter_status_combo")
        self._status.setMinimumWidth(150)
        self._status.setMaximumWidth(150)
        self._status.setMinimumHeight(38)
        self._status.setMaximumHeight(38)
        self._populate_status()
        self._style_combo(self._status)
        row.addWidget(self._status, stretch=0)

        # ── Sort By Dropdown (fixed 160px) ──────────────────
        self._sort = QComboBox()
        self._sort.setObjectName("filter_sort_combo")
        self._sort.setMinimumWidth(160)
        self._sort.setMaximumWidth(160)
        self._sort.setMinimumHeight(38)
        self._sort.setMaximumHeight(38)
        self._populate_sort()
        self._style_combo(self._sort)
        row.addWidget(self._sort, stretch=0)

        # ── Advanced toggle button ────────────────────────────
        self._adv_toggle = QPushButton(t("filter_advanced"))
        self._adv_toggle.setObjectName("filter_adv_toggle")
        self._adv_toggle.setMinimumHeight(38)
        self._adv_toggle.setMaximumHeight(38)
        self._adv_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._adv_toggle.setCheckable(True)
        self._adv_toggle.setStyleSheet(f"""
            QPushButton#filter_adv_toggle {{
                background: transparent;
                color: {tk.t2};
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#filter_adv_toggle:hover {{
                background: {_rgba(tk.blue, '10')};
                color: {tk.blue};
            }}
            QPushButton#filter_adv_toggle:checked {{
                background: {_rgba(tk.blue, '15')};
                color: {tk.blue};
            }}
        """)
        row.addWidget(self._adv_toggle, stretch=0)

        # ── Reset Button (subtle, active when filters set) ───
        self._reset_btn = QPushButton()
        self._reset_btn.setObjectName("filter_reset_btn")
        self._reset_btn.setText(t("filter_reset"))
        self._reset_btn.setMinimumHeight(38)
        self._reset_btn.setMaximumHeight(38)
        self._reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset_btn.setStyleSheet(f"""
            QPushButton#filter_reset_btn {{
                background: transparent;
                color: {tk.t2};
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#filter_reset_btn:hover {{
                background: {_rgba(tk.red, '10')};
                color: {tk.red};
            }}
            QPushButton#filter_reset_btn:pressed {{
                background: {_rgba(tk.red, '20')};
            }}
        """)
        row.addWidget(self._reset_btn, stretch=0)

        # ── Active Filter Count Badge ───────────────────────
        self._count_badge = QLabel()
        self._count_badge.setObjectName("filter_count_badge")
        font = QFont()
        font.setPointSize(10)
        font.setWeight(QFont.Weight.Bold)
        self._count_badge.setFont(font)
        self._count_badge.setStyleSheet(f"""
            QLabel#filter_count_badge {{
                background: {_rgba(tk.blue, '25')};
                color: {tk.blue};
                border-radius: 12px;
                padding: 4px 10px;
                min-width: 32px;
                text-align: center;
            }}
        """)
        self._count_badge.setMinimumHeight(24)
        self._count_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._count_badge.hide()
        row.addWidget(self._count_badge, stretch=0)

        layout.addWidget(container)

        # ── Advanced filter row (collapsible) ──────────────────
        self._adv_frame = QFrame()
        self._adv_frame.setObjectName("filter_adv_container")
        self._adv_frame.setStyleSheet(f"""
            QFrame#filter_adv_container {{
                background: {tk.card};
                border: 1px solid {tk.border};
                border-radius: 10px;
                margin-top: 6px;
            }}
        """)
        self._adv_frame.hide()

        adv_row = QHBoxLayout(self._adv_frame)
        adv_row.setContentsMargins(16, 10, 16, 10)
        adv_row.setSpacing(0)

        # ── Category group ──
        cat_group = QHBoxLayout()
        cat_group.setSpacing(8)

        cat_lbl = QLabel(t("filter_category_label"))
        cat_lbl.setObjectName("filter_adv_label")
        cat_lbl.setStyleSheet(f"""
            color: {tk.t2}; font-size: 12px; font-weight: 600;
        """)
        cat_group.addWidget(cat_lbl)
        self._cat_lbl = cat_lbl

        self._category = QComboBox()
        self._category.setObjectName("filter_cat_combo")
        self._category.setMinimumWidth(150)
        self._category.setMinimumHeight(36)
        self._category.setMaximumHeight(36)
        self._populate_categories()
        self._style_combo(self._category)
        cat_group.addWidget(self._category)

        adv_row.addLayout(cat_group)
        adv_row.addSpacing(24)

        # ── Separator ──
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {tk.border};")
        sep.setFixedHeight(28)
        adv_row.addWidget(sep)
        adv_row.addSpacing(24)

        # ── Price range group ──
        price_group = QHBoxLayout()
        price_group.setSpacing(8)

        price_lbl = QLabel(t("filter_price_label"))
        price_lbl.setObjectName("filter_adv_price_label")
        price_lbl.setStyleSheet(f"""
            color: {tk.t2}; font-size: 12px; font-weight: 600;
        """)
        price_group.addWidget(price_lbl)
        self._price_lbl = price_lbl

        spin_style = f"""
            QDoubleSpinBox {{
                background: {tk.card2};
                color: {tk.t1};
                border: 1px solid {tk.border};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
            }}
            QDoubleSpinBox:focus {{
                border: 2px solid {tk.blue};
            }}
        """

        self._price_min = QDoubleSpinBox()
        self._price_min.setRange(0, 99999)
        self._price_min.setValue(0)
        self._price_min.setDecimals(0)
        self._price_min.setPrefix(t("filter_price_from") + " ")
        self._price_min.setSpecialValueText(t("filter_price_min"))
        self._price_min.setMinimumHeight(36)
        self._price_min.setMaximumHeight(36)
        self._price_min.setMinimumWidth(120)
        self._price_min.setStyleSheet(spin_style)
        price_group.addWidget(self._price_min)

        dash_lbl = QLabel("–")
        dash_lbl.setStyleSheet(f"color: {tk.t3}; font-size: 16px; font-weight: 600;")
        dash_lbl.setFixedWidth(16)
        dash_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        price_group.addWidget(dash_lbl)

        self._price_max = QDoubleSpinBox()
        self._price_max.setRange(0, 99999)
        self._price_max.setValue(0)
        self._price_max.setDecimals(0)
        self._price_max.setPrefix(t("filter_price_to") + " ")
        self._price_max.setSpecialValueText(t("filter_price_max"))
        self._price_max.setMinimumHeight(36)
        self._price_max.setMaximumHeight(36)
        self._price_max.setMinimumWidth(120)
        self._price_max.setStyleSheet(spin_style)
        price_group.addWidget(self._price_max)

        adv_row.addLayout(price_group)
        adv_row.addStretch()

        layout.addWidget(self._adv_frame)

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
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 12px;
                font-family: "Segoe UI", "Helvetica", sans-serif;
            }}
            QComboBox:hover {{
                border: 1px solid {tk.blue};
                background: {_rgba(tk.card2, '80')};
            }}
            QComboBox:focus {{
                border: 2px solid {tk.blue};
                padding: 5px 11px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
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
        self._search.setPlaceholderText(f"🔍 {t('filter_search_placeholder')}")
        self._reset_btn.setText(t("filter_reset"))
        self._adv_toggle.setText(t("filter_advanced"))
        self._cat_lbl.setText(t("filter_category_label"))
        self._price_lbl.setText(t("filter_price_label"))
        self._price_min.setPrefix(t("filter_price_from") + " ")
        self._price_min.setSpecialValueText(t("filter_price_min"))
        self._price_max.setPrefix(t("filter_price_to") + " ")
        self._price_max.setSpecialValueText(t("filter_price_max"))

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
