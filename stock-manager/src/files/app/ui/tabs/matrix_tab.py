"""
app/ui/tabs/matrix_tab.py — Generic matrix inventory tab.

One class drives every category tab: Displays, Batteries, Cases, Cameras,
Charging Ports, Back Covers — whatever is active in the DB.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QWidget,
    QPushButton, QDialog, QMessageBox, QFrame, QScrollArea,
    QInputDialog, QLineEdit, QToolButton,
)
from app.core.theme import THEME

from app.models.category import CategoryConfig
from app.repositories.category_repo import CategoryRepository
from app.repositories.model_repo import ModelRepository
from app.repositories.item_repo import ItemRepository
from app.ui.components.matrix_widget import FrozenMatrixContainer
from app.ui.dialogs.matrix_dialogs import AddModelDialog
from app.core.icon_utils import get_button_icon
from app.ui.tabs.base_tab import BaseTab
from app.core.i18n import t
from app.ui.workers.worker_pool import POOL

_cat_repo   = CategoryRepository()
_model_repo = ModelRepository()
_item_repo  = ItemRepository()


class _MatrixSectionHeader(QWidget):
    """Clickable row: label + chevron — click anywhere to expand/collapse.
    Same style as inventory page section headers."""

    toggled = pyqtSignal(bool)

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._expanded = True
        self.setFixedHeight(24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 0, 6, 0)
        lay.setSpacing(4)

        self._lbl = QLabel(title.upper())
        self._lbl.setObjectName("inv_section_lbl")
        lay.addWidget(self._lbl)
        lay.addStretch()

        self._btn = QPushButton("▾")
        self._btn.setObjectName("inv_section_btn")
        self._btn.setFixedSize(20, 20)
        self._btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._btn.clicked.connect(self._on_click)
        lay.addWidget(self._btn)

        self._apply_style()

    def _apply_style(self):
        tk = THEME.tokens
        self._lbl.setStyleSheet(
            f"font-size:10px; font-weight:700; color:{tk.t4}; letter-spacing:0.8px;"
        )
        self._btn.setStyleSheet(f"""
            QPushButton#inv_section_btn {{
                background: transparent; color: {tk.t4};
                border: none; font-size: 11px; border-radius: 4px;
            }}
            QPushButton#inv_section_btn:hover {{
                background: {tk.border}; color: {tk.t1};
            }}
        """)

    def _on_click(self):
        self._expanded = not self._expanded
        self._btn.setText("▾" if self._expanded else "▸")
        self.toggled.emit(self._expanded)

    def mousePressEvent(self, _event):
        self._on_click()

    def apply_theme(self):
        self._apply_style()


class MatrixTab(BaseTab):
    """
    Generic inventory tab for any part category.
    Instantiate with the DB category key: MatrixTab("displays").
    """

    #: Overridden per-instance in __init__ so each category has its own
    #: isolated POOL key-space (no collisions across parallel tabs).
    POOL_KEY_PREFIX: str = "matrix_tab"

    def __init__(self, category_key: str, parent=None):
        super().__init__(parent)
        self._cat_key = category_key
        self.POOL_KEY_PREFIX = f"matrix_{category_key}"
        # Lazy-refresh dirty flag — set when a refresh was skipped because
        # the tab wasn't visible; consumed on the next showEvent.
        self._dirty: bool = True
        self._cat: CategoryConfig | None = _cat_repo.get_by_key(category_key)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(4)

        # ── Collapsible "BRAND & LEGEND" section ──────────────────────────
        self._tb_header = _MatrixSectionHeader(
            t("disp_filter_brand").upper() + " & LEGEND"
        )
        self._tb_header.toggled.connect(self._on_toolbar_toggle)
        lay.addWidget(self._tb_header)

        # The collapsible body wraps BOTH the cards strip (top) AND the
        # brand filter row. Toggling the header hides/shows the whole block.
        self._toolbar_section = QWidget()
        section_lay = QVBoxLayout(self._toolbar_section)
        section_lay.setContentsMargins(4, 4, 4, 4)
        section_lay.setSpacing(6)

        # ── Row 1 (top): part-type info cards (name · units · value) ──
        self._cards_scroll = QScrollArea()
        self._cards_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._cards_scroll.setWidgetResizable(True)
        self._cards_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._cards_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._cards_scroll.setFixedHeight(72)

        self._cards_inner = QWidget()
        self._cards_row = QHBoxLayout(self._cards_inner)
        self._cards_row.setContentsMargins(0, 0, 0, 0)
        self._cards_row.setSpacing(8)
        self._cards_row.addStretch()
        self._cards_scroll.setWidget(self._cards_inner)

        section_lay.addWidget(self._cards_scroll)

        # ── Row 2: brand filter + Add Model + refresh ──────────────────
        self._toolbar_widget = QWidget()
        tb = QHBoxLayout(self._toolbar_widget)
        tb.setContentsMargins(0, 0, 0, 0)
        tb.setSpacing(8)

        self._brand_lbl = QLabel(t("disp_filter_brand"))
        self._brand_lbl.setObjectName("card_label")

        self._brand_combo = QComboBox()
        self._brand_combo.setMinimumHeight(32)
        self._brand_combo.setMinimumWidth(140)
        self._brand_combo.currentIndexChanged.connect(self.refresh)

        self._add_btn = QPushButton(t("disp_add_model"))
        self._add_btn.setObjectName("btn_primary")
        self._add_btn.setMaximumHeight(32)
        self._add_btn.clicked.connect(self._add_model)

        self._ref_btn = QPushButton(); self._ref_btn.setObjectName("btn_secondary")
        self._ref_btn.setIcon(get_button_icon("refresh"))
        self._ref_btn.setIconSize(QSize(14, 14))
        self._ref_btn.setMaximumHeight(32)
        self._ref_btn.clicked.connect(self.refresh)

        # ── Cost-visibility toggle (PIN-gated, owner-only) ──────────────
        # Flips the hidden PRICE (cost) + TOTAL columns AND switches the
        # top cards' valuation source from sell → cost. Requires the
        # admin PIN if ShopConfig.admin_pin is set.
        self._cost_toggle_btn = QToolButton()
        self._cost_toggle_btn.setObjectName("btn_cost_toggle")
        self._cost_toggle_btn.setText("\U0001F441")  # 👁
        self._cost_toggle_btn.setCheckable(True)
        self._cost_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cost_toggle_btn.setFixedHeight(32)
        self._cost_toggle_btn.setFixedWidth(36)
        self._cost_toggle_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._cost_toggle_btn.setToolTip(
            "Show cost / valuation columns (admin — PIN required if set)"
        )
        self._cost_toggle_btn.clicked.connect(self._on_cost_toggle_clicked)
        self._apply_cost_toggle_style(False)

        # Reflect the shared COST_VIS state on this tab's button — when
        # another tab flips the visibility, update this button too.
        from app.services.cost_visibility import COST_VIS
        COST_VIS.changed.connect(self._on_cost_visibility_changed)
        self._cost_toggle_btn.setChecked(COST_VIS.visible)
        self._apply_cost_toggle_style(COST_VIS.visible)

        tb.addWidget(self._brand_lbl)
        tb.addWidget(self._brand_combo)
        tb.addStretch()

        # Legend chips retained as an empty list for backward compatibility —
        # the professional info cards above now serve as the legend.
        self._legend_chips: list[QLabel] = []

        tb.addWidget(self._cost_toggle_btn)
        tb.addWidget(self._add_btn)
        tb.addWidget(self._ref_btn)

        section_lay.addWidget(self._toolbar_widget)
        lay.addWidget(self._toolbar_section)

        # Track all card widgets so we can rebuild on each refresh
        self._pt_cards: list[QFrame] = []

        # ── Content area ──────────────────────────────────────────────────────
        from PyQt6.QtWidgets import QStackedWidget

        self._content_stack = QStackedWidget()

        # Page 0: single brand — full height, table scrolls internally
        self._single_container = FrozenMatrixContainer(refresh_cb=self.refresh, parent=self)
        self._content_stack.addWidget(self._single_container)

        # Page 1: all brands — outer scroll, each section full-sized
        self._multi_scroll = QScrollArea()
        self._multi_scroll.setWidgetResizable(True)
        self._multi_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._multi_inner = QWidget()
        self._multi_lay = QVBoxLayout(self._multi_inner)
        self._multi_lay.setContentsMargins(0, 0, 0, 0)
        self._multi_lay.setSpacing(6)
        self._multi_scroll.setWidget(self._multi_inner)
        self._content_stack.addWidget(self._multi_scroll)

        self._brand_widgets: list[QWidget] = []
        # Cached brand containers for in-place refresh (no destroy/rebuild)
        self._brand_containers: list = []
        self._brand_order: list[str] = []
        self._container = self._single_container
        self._table = self._single_container.data_table
        lay.addWidget(self._content_stack, 1)

        self._populate_brand_combo()
        self.refresh()

    def _on_toolbar_toggle(self, expanded: bool) -> None:
        """Collapse/expand the BRAND & LEGEND body — cards + filter row together."""
        self._toolbar_section.setVisible(expanded)

    # ── Cost visibility (owner-only, PIN-gated) ──────────────────────────

    def _apply_cost_toggle_style(self, active: bool) -> None:
        """Accent-border pill when ON, muted when OFF."""
        tk = THEME.tokens
        if active:
            self._cost_toggle_btn.setText("\U0001F441\u200D\U0001F5E8")  # 👁‍🗨
            self._cost_toggle_btn.setStyleSheet(
                f"QToolButton#btn_cost_toggle {{"
                f"background: {tk.card}; color: {tk.green};"
                f"border: 1.5px solid {tk.green}; border-radius: 6px;"
                f"font-size: 13pt; font-weight: 700;"
                f"}}"
                f"QToolButton#btn_cost_toggle:hover {{"
                f"background: {tk.card2};"
                f"}}"
            )
        else:
            self._cost_toggle_btn.setText("\U0001F441")
            self._cost_toggle_btn.setStyleSheet(
                f"QToolButton#btn_cost_toggle {{"
                f"background: {tk.card}; color: {tk.t3};"
                f"border: 1px solid {tk.border}; border-radius: 6px;"
                f"font-size: 13pt;"
                f"}}"
                f"QToolButton#btn_cost_toggle:hover {{"
                f"background: {tk.card2}; color: {tk.t1};"
                f"border-color: {tk.t3};"
                f"}}"
            )

    def _on_cost_toggle_clicked(self) -> None:
        """Prompt for admin PIN (if configured), then flip COST_VIS."""
        from app.services.cost_visibility import COST_VIS
        from app.core.config import ShopConfig

        # If turning OFF, no PIN needed — owner can always hide again.
        target_visible = not COST_VIS.visible
        if target_visible:
            try:
                cfg = ShopConfig.get()
                admin_pin = getattr(cfg, "admin_pin", "") or ""
            except Exception:
                admin_pin = ""
            if admin_pin:
                try:
                    pin, ok = QInputDialog.getText(
                        self,
                        t("pin_title") if callable(t) else "Admin PIN",
                        t("pin_prompt") if callable(t) else "Enter admin PIN:",
                        QLineEdit.EchoMode.Password,
                    )
                except Exception:
                    pin, ok = "", False
                if not ok:
                    # Cancelled — keep button state in sync with current COST_VIS
                    self._cost_toggle_btn.setChecked(COST_VIS.visible)
                    return
                if pin != admin_pin:
                    try:
                        QMessageBox.warning(
                            self,
                            t("pin_title") if callable(t) else "Admin PIN",
                            t("pin_wrong") if callable(t) else "Incorrect PIN.",
                        )
                    except Exception:
                        pass
                    self._cost_toggle_btn.setChecked(COST_VIS.visible)
                    return
        # Flip — all subscribers (this tab + every matrix container) react.
        COST_VIS.set_visible(target_visible)

    def _on_cost_visibility_changed(self, visible: bool) -> None:
        """Mirror the shared COST_VIS state on this tab: button style + cards.

        Lazy-refresh: only the visible tab refreshes immediately. Other
        matrix tabs flip their button style and mark themselves dirty so
        they refresh when the user navigates to them — avoids a stampede
        of 5-6 parallel DB queries every time the owner toggles the eye.
        """
        self._cost_toggle_btn.blockSignals(True)
        self._cost_toggle_btn.setChecked(visible)
        self._cost_toggle_btn.blockSignals(False)
        self._apply_cost_toggle_style(visible)
        if self.isVisible():
            self.refresh()
        else:
            self._dirty = True

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _rebuild_cards(self, cat, item_map) -> None:
        """Rebuild the per-part-type info cards strip at the top of the tab.

        Each card: name (accent colour) · total units (pcs) · total value.
        When COST_VIS is OFF (default) — value is SELL-based: sum of
        stock × (sell_price || part_type.default_price).
        When COST_VIS is ON — value is COST-based: sum of stock × cost_price.
        A small "sell" / "cost" suffix on the value clarifies which is shown.
        """
        # Clear prior cards (keep final stretch)
        while self._cards_row.count() > 0:
            item = self._cards_row.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self._pt_cards.clear()

        if not cat or not cat.part_types:
            self._cards_row.addStretch()
            return

        # Currency formatter (safe fallback)
        try:
            from app.core.config import ShopConfig
            fmt_cur = ShopConfig.get().format_currency
        except Exception:
            fmt_cur = lambda v: f"{v:,.2f}"

        # Which metric is showing right now?
        from app.services.cost_visibility import COST_VIS
        cost_mode = COST_VIS.visible
        metric_suffix = "cost" if cost_mode else "sell"

        # Shop-wide setting — may hide the value portion of every card and
        # suppress the grand-total card entirely. Cost mode overrides it
        # (the owner has already PIN-unlocked the valuation data).
        try:
            from app.core.config import ShopConfig
            _cfg = ShopConfig.get()
            show_totals = _cfg.is_show_sell_totals or cost_mode
        except Exception:
            show_totals = True

        # Aggregate totals per part-type key
        totals: dict[str, tuple[int, float]] = {}
        dp_map = {pt.key: float(pt.default_price or 0.0) for pt in cat.part_types}
        if item_map:
            for (_mid, pt_key, _color), it in item_map.items():
                u, v = totals.get(pt_key, (0, 0.0))
                stk = int(getattr(it, "stock", 0) or 0)
                u += stk
                if cost_mode:
                    cp = getattr(it, "cost_price", None)
                    eff = cp if (cp and cp > 0) else 0.0
                else:
                    sp = getattr(it, "sell_price", None)
                    eff = sp if (sp and sp > 0) else dp_map.get(pt_key, 0.0)
                v += stk * (eff or 0.0)
                totals[pt_key] = (u, v)

        tk = THEME.tokens
        is_dark = tk.is_dark
        CARD_W, CARD_H = 180, 60

        for pt in cat.part_types:
            hdr_bg = QColor(pt.accent_color)
            if is_dark:
                r = int(0.28 * hdr_bg.red()   + 0.72 * 15)
                g = int(0.28 * hdr_bg.green() + 0.72 * 15)
                b = int(0.28 * hdr_bg.blue()  + 0.72 * 15)
                r_t, g_t, b_t = min(r + 14, 255), min(g + 14, 255), min(b + 14, 255)
                r_b, g_b, b_b = max(r - 10, 0), max(g - 10, 0), max(b - 10, 0)
                hair_a, muted = 26, "rgba(255,255,255,135)"
            else:
                r = int(0.32 * hdr_bg.red()   + 0.68 * 248)
                g = int(0.32 * hdr_bg.green() + 0.68 * 248)
                b = int(0.32 * hdr_bg.blue()  + 0.68 * 248)
                r_t, g_t, b_t = min(r + 8, 255), min(g + 8, 255), min(b + 8, 255)
                r_b, g_b, b_b = max(r - 6, 0), max(g - 6, 0), max(b - 6, 0)
                hair_a, muted = 70, "rgba(0,0,0,130)"

            units, value = totals.get(pt.key, (0, 0.0))
            try:
                val_text = fmt_cur(value)
            except Exception:
                val_text = f"{value:,.2f}"
            # Tag the metric so the owner always knows which valuation shows
            val_text = f"{val_text}  {metric_suffix}"

            card = QFrame()
            card.setFixedSize(CARD_W, CARD_H)
            card.setObjectName("pt_legend_card")
            card.setStyleSheet(
                "QFrame#pt_legend_card {"
                f"background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
                f"  stop:0 rgb({r_t},{g_t},{b_t}),"
                f"  stop:1 rgb({r_b},{g_b},{b_b}));"
                "border: none;"
                f"border-top: 1px solid rgba(255,255,255,{hair_a});"
                f"border-bottom: 2px solid {pt.accent_color};"
                "border-radius: 6px;"
                "}"
                "QFrame#pt_legend_card QLabel { background: transparent; border: none; }"
            )

            col = QVBoxLayout(card)
            col.setContentsMargins(10, 5, 10, 5)
            col.setSpacing(2)

            name_lbl = QLabel(pt.name)
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_f = QFont("Segoe UI", 10, QFont.Weight.DemiBold)
            name_f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 104)
            name_lbl.setFont(name_f)
            name_lbl.setStyleSheet(
                f"color: {pt.accent_color}; background: transparent;"
            )
            col.addWidget(name_lbl)

            metrics_row = QHBoxLayout()
            metrics_row.setContentsMargins(0, 0, 0, 0)
            metrics_row.setSpacing(4)

            units_lbl = QLabel(f"{units:,} pcs")
            units_lbl.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            units_f = QFont("Segoe UI", 8, QFont.Weight.Medium)
            units_lbl.setFont(units_f)
            units_lbl.setStyleSheet(f"color: {muted}; background: transparent;")

            metrics_row.addWidget(units_lbl, 1)
            if show_totals:
                # Full card — name + units + value. Value only rendered
                # when the owner has enabled sell-total display (or is in
                # PIN-unlocked cost mode).
                value_lbl = QLabel(val_text)
                value_lbl.setAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                val_f = QFont("Segoe UI", 9, QFont.Weight.Bold)
                value_lbl.setFont(val_f)
                value_lbl.setStyleSheet(
                    f"color: {pt.accent_color}; background: transparent;"
                )
                metrics_row.addWidget(value_lbl, 1)
            else:
                # Valuation hidden — right-align the units label so the
                # card doesn't look lopsided with a lone left-aligned count.
                units_lbl.setAlignment(
                    Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
                )
            col.addLayout(metrics_row)

            self._cards_row.addWidget(card)
            self._pt_cards.append(card)

        # ── Grand-total card ────────────────────────────────────────────
        # Skip entirely when sell totals are hidden shop-wide. In cost
        # mode the owner has already authenticated, so we keep it.
        if not show_totals:
            self._cards_row.addStretch()
            return

        # Sum across every part-type in the filter — at-a-glance roll-up
        # using the same sell/cost metric as the per-part-type cards.
        # Styled with the shop accent
        # (emerald) so it reads as the summary/anchor at the end of the strip.
        grand_units = sum(u for (u, _v) in totals.values())
        grand_value = sum(v for (_u, v) in totals.values())
        try:
            grand_val_text = fmt_cur(grand_value)
        except Exception:
            grand_val_text = f"{grand_value:,.2f}"
        grand_val_text = f"{grand_val_text}  {metric_suffix}"

        tk_g = THEME.tokens
        accent = tk_g.green if hasattr(tk_g, "green") else "#10B981"
        if tk_g.is_dark:
            g_top, g_bot = 36, 18
            g_hair = 32
            g_muted = "rgba(255,255,255,160)"
        else:
            g_top, g_bot = 232, 215
            g_hair = 80
            g_muted = "rgba(0,0,0,140)"

        total_card = QFrame()
        total_card.setFixedSize(220, 60)
        total_card.setObjectName("pt_total_card")
        total_card.setStyleSheet(
            "QFrame#pt_total_card {"
            f"background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            f"  stop:0 rgba(16,185,129,{g_top}),"
            f"  stop:1 rgba(16,185,129,{g_bot}));"
            "border: none;"
            f"border-top: 1px solid rgba(255,255,255,{g_hair});"
            f"border-bottom: 2px solid {accent};"
            "border-radius: 6px;"
            "}"
            "QFrame#pt_total_card QLabel { background: transparent; border: none; }"
        )

        gcol = QVBoxLayout(total_card)
        gcol.setContentsMargins(12, 5, 12, 5)
        gcol.setSpacing(2)

        g_name = QLabel("TOTAL")
        g_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        g_name_f = QFont("Segoe UI", 10, QFont.Weight.Bold)
        g_name_f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 110)
        g_name.setFont(g_name_f)
        g_name.setStyleSheet(f"color: {accent}; background: transparent;")
        gcol.addWidget(g_name)

        g_metrics_row = QHBoxLayout()
        g_metrics_row.setContentsMargins(0, 0, 0, 0)
        g_metrics_row.setSpacing(4)

        g_units = QLabel(f"{grand_units:,} pcs")
        g_units.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        g_units_f = QFont("Segoe UI", 8, QFont.Weight.Medium)
        g_units.setFont(g_units_f)
        g_units.setStyleSheet(f"color: {g_muted}; background: transparent;")

        g_value = QLabel(grand_val_text)
        g_value.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        g_value_f = QFont("Segoe UI", 10, QFont.Weight.Bold)
        g_value.setFont(g_value_f)
        g_value.setStyleSheet(f"color: {accent}; background: transparent;")

        g_metrics_row.addWidget(g_units, 1)
        g_metrics_row.addWidget(g_value, 1)
        gcol.addLayout(g_metrics_row)

        self._cards_row.addWidget(total_card)
        self._pt_cards.append(total_card)

        self._cards_row.addStretch()

    def _populate_brand_combo(self) -> None:
        self._brand_combo.blockSignals(True)
        prev = self._brand_combo.currentText()
        self._brand_combo.clear()
        self._brand_combo.addItem(t("disp_all_brands"), userData=None)
        for brand in _model_repo.get_brands():
            self._brand_combo.addItem(brand, userData=brand)
        idx = self._brand_combo.findText(prev)
        if idx >= 0:
            self._brand_combo.setCurrentIndex(idx)
        self._brand_combo.blockSignals(False)

    def _selected_brand(self) -> str | None:
        return self._brand_combo.currentData()

    def _add_model(self) -> None:
        brands = _model_repo.get_brands()
        dlg = AddModelDialog(brands, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        brand = dlg.brand()
        name  = dlg.model_name()
        if _model_repo.exists(name):
            QMessageBox.warning(
                self, t("dlg_required_title"),
                f"'{name}' " + t("disp_model_empty"),
            )
            return
        _model_repo.add(brand, name)
        self._populate_brand_combo()
        idx = self._brand_combo.findText(brand)
        if idx >= 0:
            self._brand_combo.setCurrentIndex(idx)
        else:
            self.refresh()

    # ── BaseTab interface ─────────────────────────────────────────────────────

    def showEvent(self, event):
        """Reconcile lazy refresh — if a COST_VIS flip or admin close
        occurred while this tab wasn't visible, run the deferred refresh
        now that we're back on screen. Uses QTimer.singleShot so the show
        transition paints first, then data arrives."""
        super().showEvent(event)
        if getattr(self, "_dirty", False):
            from PyQt6.QtCore import QTimer as _QT
            _QT.singleShot(0, self.refresh)

    def refresh(self) -> None:
        if not self._cat:
            self._cat = _cat_repo.get_by_key(self._cat_key)
        if not self._cat:
            return
        # Claim the dirty state — any subsequent COST_VIS flip while this
        # refresh is in-flight will flip the flag back on and showEvent
        # will reconcile on the next activation.
        self._dirty = False

        # Save scroll position (v-scroll of single mode, v-scroll of multi area)
        self._saved_v = self._single_container.data_table.verticalScrollBar().value()
        self._saved_v_multi = self._multi_scroll.verticalScrollBar().value()

        brand = self._selected_brand()
        cat_id = self._cat.id

        # ── Dispatch DB work to the worker pool ─────────────────────────
        # Every query (models, matrix items — up to 6 brands × 2 queries in
        # all-brands mode) runs off the UI thread. The main thread stays
        # responsive; _apply_refresh() receives the result and does the
        # pure widget updates synchronously.
        def _fetch():
            if brand:
                models = _model_repo.get_all(brand=brand)
                item_map = _item_repo.get_matrix_items(cat_id, brand=brand)
                return {
                    "mode": "single",
                    "brand": brand,
                    "models": models,
                    "item_map": item_map,
                }
            # All-brands — prefetch per-brand data so _apply_refresh never
            # needs to touch the DB on the UI thread.
            try:
                all_items = _item_repo.get_matrix_items(cat_id, brand=None)
            except Exception:
                all_items = {}
            brands_now = list(_model_repo.get_brands())
            per_brand = []
            for b in brands_now:
                try:
                    b_models = _model_repo.get_all(brand=b)
                    b_items = _item_repo.get_matrix_items(cat_id, brand=b)
                except Exception:
                    b_models, b_items = [], {}
                per_brand.append((b, b_models, b_items))
            return {
                "mode": "multi",
                "all_items": all_items,
                "brands_now": brands_now,
                "per_brand": per_brand,
            }

        # Per-tab key so rapid brand-combo changes collapse to one query
        pool_key = f"matrix_refresh_{self._cat_key}"

        def _on_error(msg: str):
            # Log visibly so silent worker exceptions don't leave the page blank.
            import logging as _lg
            _lg.getLogger(__name__).error(
                "MatrixTab[%s] refresh failed: %s", self._cat_key, msg
            )

        POOL.submit(pool_key, _fetch, self._apply_refresh, _on_error)

    def _apply_refresh(self, payload: dict) -> None:
        """Run widget updates with data pre-fetched by the worker pool.

        Synchronous application — we tried staggering brand sections across
        ticks to reduce the single-frame spike, but it opened race windows
        where a second refresh mid-chain left the page empty. Correctness
        over 200 ms of visual smoothness: build all sections inline.
        """
        if not payload or not self._cat:
            return
        from app.models.category import CategoryConfig

        if payload["mode"] == "single":
            self._content_stack.setCurrentIndex(0)
            models = payload["models"]
            item_map = payload["item_map"]
            used_pt_keys = {key[1] for key in item_map.keys()}
            filtered_pts = [pt for pt in self._cat.part_types if pt.key in used_pt_keys]
            # Hide model rows with no items left for this category — happens
            # when every (model, pt) combo for the model has been excluded
            # in Part Type Settings. Otherwise the row would render as "—"
            # cells (looks "disabled") instead of disappearing.
            models_with_items = {key[0] for key in item_map.keys()}
            filtered_models = [m for m in models if m.id in models_with_items]
            filtered_cat = CategoryConfig(
                id=self._cat.id, key=self._cat.key,
                name_en=self._cat.name_en, name_de=self._cat.name_de,
                name_ar=self._cat.name_ar, sort_order=self._cat.sort_order,
                icon=self._cat.icon, is_active=self._cat.is_active,
                part_types=filtered_pts or self._cat.part_types,
            )
            self._rebuild_cards(filtered_cat, item_map)
            self._single_container.load(filtered_cat, filtered_models, item_map)
            self._container = self._single_container
            self._table = self._single_container.data_table
        else:
            # All-brands mode
            self._content_stack.setCurrentIndex(1)
            self._rebuild_cards(self._cat, payload["all_items"])

            brands_now = payload["brands_now"]
            per_brand = payload["per_brand"]
            existing_brands = getattr(self, "_brand_order", [])

            if (existing_brands == brands_now
                    and len(self._brand_containers) == len(brands_now)):
                # Fast path — reuse containers, reload rows
                for (b, b_models, b_items), container in zip(
                        per_brand, self._brand_containers):
                    self._reload_brand_container(
                        b, container, models=b_models, item_map=b_items
                    )
            else:
                # Slow path — tear down, rebuild every section
                for w in self._brand_widgets:
                    w.deleteLater()
                self._brand_widgets.clear()
                self._brand_containers.clear()
                while self._multi_lay.count():
                    it = self._multi_lay.takeAt(0)
                    if it.widget():
                        it.widget().deleteLater()

                for (b, b_models, b_items) in per_brand:
                    self._add_brand_section(b, models=b_models, item_map=b_items)

                self._multi_lay.addStretch()
                self._brand_order = brands_now

        # Post-apply: zoom + scroll restore
        self._post_apply_refresh(single_mode=(payload["mode"] == "single"))

    def _post_apply_refresh(self, single_mode: bool) -> None:
        """Re-apply current zoom and restore the saved scroll position.

        Called by ``_apply_refresh`` on the UI thread once the fresh data
        is in the widgets. Kept separate for readability.
        """
        # Re-apply current zoom so rebuilt rows/banner keep the zoom factor.
        try:
            from app.services.zoom_service import ZOOM
            factor = ZOOM.factor
            if hasattr(self._single_container, "apply_zoom"):
                self._single_container.apply_zoom(factor)
            from app.ui.components.matrix_widget import FrozenMatrixContainer
            for w in getattr(self, "_brand_widgets", []):
                if isinstance(w, FrozenMatrixContainer):
                    w.apply_zoom(factor)
        except Exception:
            pass

        # ── Restore scroll position — robust against layout-timing races ──
        from PyQt6.QtCore import QTimer
        target = self._saved_v if single_mode else self._saved_v_multi
        if single_mode:
            scroll_bar = self._single_container.data_table.verticalScrollBar()
        else:
            scroll_bar = self._multi_scroll.verticalScrollBar()

        if target <= 0:
            return

        restored_flag = [False]

        def _restore():
            if restored_flag[0]:
                return
            sb = scroll_bar
            if sb.maximum() >= target or sb.value() == target:
                sb.setValue(target)
                restored_flag[0] = True
                try:
                    sb.rangeChanged.disconnect(_on_range)
                except (TypeError, RuntimeError):
                    pass

        def _on_range(_minval, _maxval):
            if _maxval >= target:
                _restore()

        scroll_bar.rangeChanged.connect(_on_range)
        for delay in (0, 30, 90, 180, 320, 500):
            QTimer.singleShot(delay, _restore)

    def _add_brand_section(self, brand: str, *,
                           models=None, item_map=None) -> None:
        """Add one full-sized brand section to the scrollable all-brands page.

        ``models`` and ``item_map`` can be pre-fetched (by the worker pool in
        ``refresh``) to avoid sync DB calls on the UI thread. When either is
        None we fall back to a synchronous fetch — safe for legacy callers.
        """
        from app.models.category import CategoryConfig

        if models is None:
            models = _model_repo.get_all(brand=brand)
        if not models:
            return
        if item_map is None:
            item_map = _item_repo.get_matrix_items(self._cat.id, brand=brand)
        used_pt_keys = {key[1] for key in item_map.keys()}
        filtered_pts = [pt for pt in self._cat.part_types if pt.key in used_pt_keys]
        models_with_items = {key[0] for key in item_map.keys()}
        filtered_models = [m for m in models if m.id in models_with_items]
        if not filtered_models:
            return

        filtered_cat = CategoryConfig(
            id=self._cat.id, key=self._cat.key,
            name_en=self._cat.name_en, name_de=self._cat.name_de,
            name_ar=self._cat.name_ar, sort_order=self._cat.sort_order,
            icon=self._cat.icon, is_active=self._cat.is_active,
            part_types=filtered_pts or self._cat.part_types,
        )

        # Brand header
        tk = THEME.tokens
        header = QLabel(f"  {brand}")
        header.setFixedHeight(28)
        header.setStyleSheet(
            f"background:{tk.card2}; color:{tk.t1}; "
            f"font-size:12px; font-weight:700; "
            f"border-left:3px solid {tk.green}; padding-left:10px;"
        )
        self._multi_lay.addWidget(header)
        self._brand_widgets.append(header)

        # Matrix container — large minimum height, scrolls internally
        # so banner + column headers stay STICKY at top of each section
        container = FrozenMatrixContainer(refresh_cb=self.refresh, parent=self)
        container.load(filtered_cat, filtered_models, item_map)

        # Set height: full content if small, or a generous minimum if large
        tbl = container.data_table
        banner_h = 30
        header_h = tbl.horizontalHeader().height()
        rows_h = sum(tbl.rowHeight(r) for r in range(tbl.rowCount()))
        content_h = banner_h + header_h + rows_h + 16

        # If content fits in 500px, show it all; otherwise cap at 500
        # and let internal scroll handle the rest (headers stay sticky)
        container.setFixedHeight(min(content_h, 500))

        self._multi_lay.addWidget(container)
        self._brand_widgets.append(container)
        self._brand_containers.append(container)

        self._container = container
        self._table = container.data_table

    def _reload_brand_container(self, brand: str, container, *,
                                 models=None, item_map=None) -> None:
        """Refresh the contents of an existing brand container IN PLACE.

        Does NOT destroy the widget — avoids the outer QScrollArea
        auto-scrolling to top when focus is lost on destroyed widgets.

        Accepts optional pre-fetched ``models`` / ``item_map`` so the worker
        pool in ``refresh()`` can avoid touching the DB on the UI thread.
        """
        from app.models.category import CategoryConfig
        if models is None:
            models = _model_repo.get_all(brand=brand)
        if not models:
            return
        if item_map is None:
            item_map = _item_repo.get_matrix_items(self._cat.id, brand=brand)
        used_pt_keys = {key[1] for key in item_map.keys()}
        filtered_pts = [pt for pt in self._cat.part_types if pt.key in used_pt_keys]
        models_with_items = {key[0] for key in item_map.keys()}
        filtered_models = [m for m in models if m.id in models_with_items]
        filtered_cat = CategoryConfig(
            id=self._cat.id, key=self._cat.key,
            name_en=self._cat.name_en, name_de=self._cat.name_de,
            name_ar=self._cat.name_ar, sort_order=self._cat.sort_order,
            icon=self._cat.icon, is_active=self._cat.is_active,
            part_types=filtered_pts or self._cat.part_types,
        )
        container.load(filtered_cat, filtered_models, item_map)

        # Recompute container height from new content
        tbl = container.data_table
        banner_h = 30
        header_h = tbl.horizontalHeader().height()
        rows_h = sum(tbl.rowHeight(r) for r in range(tbl.rowCount()))
        content_h = banner_h + header_h + rows_h + 16
        container.setFixedHeight(min(content_h, 500))

    def apply_theme(self) -> None:
        """Refresh the matrix table so per-part-type cards and cells pick up the new theme."""
        self.refresh()

    def retranslate(self) -> None:
        self._brand_lbl.setText(t("disp_filter_brand"))
        self._add_btn.setText(t("disp_add_model"))
        self._brand_combo.blockSignals(True)
        self._brand_combo.setItemText(0, t("disp_all_brands"))
        self._brand_combo.blockSignals(False)
        self._container.retranslate()
        self.refresh()
