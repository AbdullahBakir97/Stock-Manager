"""
app/ui/components/sidebar.py — Navigation sidebar with dynamic category tabs.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QScrollArea, QLabel,
    QPushButton, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal

from app.core.config import ShopConfig
from app.core.i18n import t, LANG
from app.core.icon_utils import load_svg_icon
from app.repositories.category_repo import CategoryRepository
from app.ui.components.collapsible_section import CollapsibleSection

_cat_repo = CategoryRepository()


class Sidebar(QFrame):
    """240px fixed sidebar with main nav + collapsible category tabs."""

    nav_clicked = pyqtSignal(str)  # emits nav key like "nav_inventory" or "cat_displays"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(240)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        self._nav_btns: list[QPushButton] = []
        self._nav_keys: list[str] = []
        self._cat_nav_btns: list[QPushButton] = []
        self._current_nav = "nav_inventory"

        self._build()

    # ── Build ────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)

        sb_scroll = QScrollArea()
        sb_scroll.setWidgetResizable(True)
        sb_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sb_scroll.setFrameShape(QFrame.Shape.NoFrame)
        sb_scroll.setObjectName("sidebar_scroll")

        sb_inner = QWidget()
        sb_lay = QVBoxLayout(sb_inner)
        sb_lay.setContentsMargins(0, 0, 0, 0); sb_lay.setSpacing(0)

        # ── Main navigation ──────────────────────────────────────────────
        nav_section = QWidget()
        nav_lay = QVBoxLayout(nav_section)
        nav_lay.setContentsMargins(8, 12, 8, 4); nav_lay.setSpacing(2)

        nav_items = [
            ("nav_inventory",       "📦"),
            ("nav_transactions",    "📋"),
            ("nav_quick_scan",      "⚡"),
            ("nav_sales",           "💰"),
            ("nav_customers",       "👥"),
            ("nav_purchase_orders", "🛒"),
            ("nav_returns",         "↩"),
            ("nav_suppliers",       "🏭"),
            ("nav_audit",           "📝"),
            ("nav_price_lists",     "💲"),
            ("nav_barcode_gen",     "🏷"),
            ("nav_reports",         "📊"),
            ("nav_analytics",       "📈"),
        ]
        _tips = {
            "nav_inventory":       "Browse, add, and edit products",
            "nav_transactions":    "View all stock movement history",
            "nav_quick_scan":      "Scan barcodes for quick operations",
            "nav_sales":           "Point of sale and sales history",
            "nav_customers":       "Manage customer contacts and CRM",
            "nav_purchase_orders": "Create and manage purchase orders",
            "nav_returns":         "Process and track product returns",
            "nav_suppliers":       "Manage suppliers and contacts",
            "nav_audit":           "Inventory audit and stocktake",
            "nav_price_lists":     "Price lists and margin analysis",
            "nav_barcode_gen":     "Generate and print barcode labels",
            "nav_reports":         "Generate PDF reports and audit sheets",
            "nav_analytics":       "Dashboard with charts and KPIs",
        }
        for key, icon in nav_items:
            btn = QPushButton(f"  {icon}   {t(key)}")
            btn.setObjectName("sidebar_btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(_tips.get(key, ""))
            btn.clicked.connect(lambda _, k=key: self.nav_clicked.emit(k))
            nav_lay.addWidget(btn)
            self._nav_btns.append(btn)
            self._nav_keys.append(key)
        sb_lay.addWidget(nav_section)

        # ── Separator + collapsible categories ───────────────────────────
        self._cat_sep = QFrame()
        self._cat_sep.setObjectName("sidebar_divider")
        self._cat_sep.setFixedHeight(1)
        sb_lay.addWidget(self._cat_sep)

        self._cat_section = CollapsibleSection("CATEGORIES")
        self._build_category_buttons()
        sb_lay.addWidget(self._cat_section)

        # Help button
        help_div = QFrame()
        help_div.setObjectName("sidebar_divider")
        help_div.setFixedHeight(1)
        sb_lay.addWidget(help_div)

        self._help_btn = QPushButton(f"  ❓   {t('nav_help')}")
        self._help_btn.setObjectName("sidebar_btn")
        self._help_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._help_btn.setToolTip("Open help guide (F1)")
        self._help_btn.clicked.connect(lambda: self.nav_clicked.emit("nav_help"))
        sb_lay.addWidget(self._help_btn)

        sb_lay.addStretch()
        sb_scroll.setWidget(sb_inner)
        outer.addWidget(sb_scroll, 1)

        # ── Bottom: shop info ────────────────────────────────────────────
        btm_div = QFrame()
        btm_div.setObjectName("sidebar_divider")
        btm_div.setFixedHeight(1)
        outer.addWidget(btm_div)

        cfg = ShopConfig.get()
        if cfg.name:
            shop_frame = QFrame()
            shop_frame.setObjectName("sidebar_user_info")
            sf_lay = QVBoxLayout(shop_frame)
            sf_lay.setContentsMargins(12, 10, 12, 10); sf_lay.setSpacing(2)
            self._shop_name_lbl = QLabel(cfg.name)
            self._shop_name_lbl.setObjectName("sidebar_shop_name")
            sf_lay.addWidget(self._shop_name_lbl)
            if cfg.contact_info:
                self._shop_meta_lbl = QLabel(cfg.contact_info)
                self._shop_meta_lbl.setObjectName("sidebar_shop_meta")
                sf_lay.addWidget(self._shop_meta_lbl)
            else:
                self._shop_meta_lbl = None
            outer.addWidget(shop_frame)
        else:
            self._shop_name_lbl = None
            self._shop_meta_lbl = None

        # Hidden alert button (for compatibility with alert status tracking)
        self.alert_btn = QPushButton()
        self.alert_btn.setObjectName("alert_ok")
        self.alert_btn.hide()

    # ── Category buttons ─────────────────────────────────────────────────────

    def _build_category_buttons(self) -> None:
        for cat in _cat_repo.get_all_active():
            icon = load_svg_icon(cat.icon) if cat.icon else "📁"
            btn = QPushButton(f"  {icon}   {cat.name(LANG)}")
            btn.setObjectName("sidebar_btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, k=cat.key: self.nav_clicked.emit(f"cat_{k}"))
            self._cat_section.add_widget(btn)
            self._cat_nav_btns.append(btn)
            self._nav_btns.append(btn)
            self._nav_keys.append(f"cat_{cat.key}")

    def rebuild_categories(self) -> None:
        """Remove and re-create dynamic category buttons."""
        for btn in self._cat_nav_btns:
            btn.deleteLater()
        for btn in self._cat_nav_btns:
            if btn in self._nav_btns:
                idx = self._nav_btns.index(btn)
                self._nav_btns.pop(idx)
                self._nav_keys.pop(idx)
        self._cat_nav_btns.clear()
        self._build_category_buttons()
        self.update_styles(self._current_nav)

    # ── Style / retranslate ──────────────────────────────────────────────────

    def update_styles(self, current_key: str) -> None:
        self._current_nav = current_key
        for btn, key in zip(self._nav_btns, self._nav_keys):
            btn.setObjectName("sidebar_btn_active" if key == current_key else "sidebar_btn")
            btn.style().unpolish(btn); btn.style().polish(btn)

    def retranslate(self) -> None:
        nav_items = [
            ("nav_inventory",       "📦"),
            ("nav_transactions",    "📋"),
            ("nav_quick_scan",      "⚡"),
            ("nav_sales",           "💰"),
            ("nav_customers",       "👥"),
            ("nav_purchase_orders", "🛒"),
            ("nav_returns",         "↩"),
            ("nav_suppliers",       "🏭"),
            ("nav_audit",           "📝"),
            ("nav_price_lists",     "💲"),
            ("nav_barcode_gen",     "🏷"),
            ("nav_reports",         "📊"),
            ("nav_analytics",       "📈"),
        ]
        for i, (key, icon) in enumerate(nav_items):
            if i < len(self._nav_btns):
                self._nav_btns[i].setText(f"  {icon}   {t(key)}")

        cats = _cat_repo.get_all_active()
        for i, btn in enumerate(self._cat_nav_btns):
            if i < len(cats):
                cat = cats[i]
                icon = load_svg_icon(cat.icon) if cat.icon else "📁"
                btn.setText(f"  {icon}   {cat.name(LANG)}")

        cfg = ShopConfig.get()
        if self._shop_name_lbl and cfg.name:
            self._shop_name_lbl.setText(cfg.name)
        if self._shop_meta_lbl and cfg.contact_info:
            self._shop_meta_lbl.setText(cfg.contact_info)
