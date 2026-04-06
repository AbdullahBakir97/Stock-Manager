"""
app/ui/components/dashboard_widget.py — Premium professional dashboard with enhanced summary cards.

Features:
  - 5 summary cards with icon circles, colored left borders, and shadow effects
  - Large formatted numbers with professional typography
  - Quick action buttons (New Product, Export CSV)
  - Premium animations and hover effects
  - Full i18n and theme support
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QPushButton, QLabel,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor

from app.core.theme import THEME, _rgba
from app.core.i18n import t
from app.core.config import ShopConfig


# ── Summary Card Widget ────────────────────────────────────────────────────────

class SummaryCard(QFrame):
    """
    Premium summary card with icon circle, colored left border, and shadow effect.

    Shows:
      - Colored icon circle (top-left, 40px) with unicode emoji
      - Large number (24pt, JetBrains Mono, bold, accent color)
      - Small label (9pt, muted text)
      - 3px left border in accent color
      - Smooth background with shadow effect
      - Hover state with enhanced border
    """

    def __init__(
        self,
        icon: str,
        accent_color: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._value: int = 0
        self._label: str = ""
        self._icon = icon
        self._accent_color = accent_color

        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Plain)
        self.setMinimumHeight(110)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # ── Main layout (with padding for left border) ───────
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(6)

        # ── Top row: icon circle + value ─────────────────────
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(12)

        # Icon circle label (40x40)
        self._icon_label = QLabel(self._icon)
        icon_font = QFont("Segoe UI Emoji", 18)
        if icon_font.pointSize() <= 0:
            icon_font.setPixelSize(18)
        self._icon_label.setFont(icon_font)
        self._icon_label.setFixedSize(QSize(40, 40))
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        self._icon_label.setStyleSheet(f"""
            QLabel {{
                background: {_rgba(accent_color, '18')};
                border-radius: 8px;
                color: {accent_color};
            }}
        """)
        top_row.addWidget(self._icon_label)

        # Number value (large, bold, monospace)
        self._number_label = QLabel("0")
        number_font = QFont("JetBrains Mono", 24, QFont.Weight.Bold)
        self._number_label.setFont(number_font)
        self._number_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._number_label.setStyleSheet(f"color: {accent_color};")
        top_row.addWidget(self._number_label)
        top_row.addStretch()

        main_layout.addLayout(top_row)

        # ── Text label (muted, smaller) ──────────────────────
        self._text_label = QLabel("")
        self._text_label.setObjectName("card_label")   # picked up by _apply_style QSS
        text_font = QFont("Segoe UI", 9)
        if text_font.pointSize() <= 0:
            text_font.setPixelSize(12)
        self._text_label.setFont(text_font)
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        main_layout.addWidget(self._text_label)

        self._apply_style()

    def set_value(self, value: int | float, label: str) -> None:
        """Update card with new value and label (data-only, no style recalc)."""
        self._value = int(value)
        self._label = label
        self._number_label.setText(str(self._value))
        self._text_label.setText(label)

    def set_formatted_value(self, formatted_str: str, label: str) -> None:
        """Update card with pre-formatted string, e.g. currency (no style recalc)."""
        self._label = label
        self._number_label.setText(formatted_str)
        self._text_label.setText(label)

    def _apply_style(self) -> None:
        """Apply theme-aware styling. Call inside a setUpdatesEnabled(False) block
        to suppress per-call repaints when changing themes."""
        tk = THEME.tokens
        # Single setStyleSheet covers both the card frame and its text label so Qt
        # only re-parses CSS once per card instead of twice.
        self.setStyleSheet(f"""
            SummaryCard {{
                background: {tk.card};
                border: 1px solid {tk.border};
                border-left: 3px solid {self._accent_color};
                border-radius: 12px;
            }}
            SummaryCard:hover {{
                background: {tk.card2};
                border: 1px solid {tk.border2};
                border-left: 3px solid {self._accent_color};
            }}
            SummaryCard QLabel#card_label {{
                color: {tk.t3};
            }}
        """)


# ── Dashboard Widget ──────────────────────────────────────────────────────────

class DashboardWidget(QWidget):
    """
    Premium professional dashboard with enhanced summary cards and quick actions.

    Displays:
      - 5 summary cards with icons, colored accents, and professional typography
      - Quick action buttons for core workflows
      - Real-time updates and theme-aware styling

    Signals:
        action_new_product: User clicked "New Product" button
        action_export: User clicked "Export CSV" button
    """

    action_new_product = pyqtSignal()
    action_export = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._shop_config = ShopConfig.get()
        self._cards: dict[str, SummaryCard] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the premium dashboard layout."""
        tk = THEME.tokens

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)

        # ── Summary Cards Row (5 cards) ──────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setContentsMargins(0, 0, 0, 0)
        cards_row.setSpacing(16)

        # Define cards: (key, icon, accent_color, label_key)
        card_specs = [
            ("total_products", "📦", tk.blue, "card_total_products"),
            ("total_units", "📊", tk.green, "card_total_units"),
            ("low_stock", "⚠", tk.orange, "card_low_stock"),
            ("out_of_stock", "🔴", tk.red, "card_out_of_stock"),
            ("inventory_value", "💰", tk.purple, "dash_inventory_value"),
        ]

        for key, icon, color, label_key in card_specs:
            card = SummaryCard(icon, color)
            card.set_value(0, t(label_key))
            self._cards[key] = card
            cards_row.addWidget(card)

        main_layout.addLayout(cards_row)

        # ── Quick Actions Bar ────────────────────────────────────────
        actions_bar = self._build_actions_bar(tk)
        main_layout.addWidget(actions_bar)

        # Stretch to push everything to top
        main_layout.addStretch()

    def _build_actions_bar(self, tk) -> QFrame:
        """Build the compact quick actions bar."""
        actions_container = QFrame()
        actions_container.setObjectName("dashboard_actions")
        actions_container.setStyleSheet(f"""
            QFrame#dashboard_actions {{
                background: {tk.card};
                border: 1px solid {tk.border};
                border-radius: 10px;
                padding: 14px 16px;
            }}
        """)

        actions_layout = QHBoxLayout(actions_container)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(12)

        # New Product button (primary)
        btn_new = QPushButton(f"➕ {t('dash_new_product')}")
        btn_new.setMinimumHeight(38)
        btn_new.setMaximumWidth(180)
        btn_new.setStyleSheet(self._primary_button_style(tk))
        btn_new.clicked.connect(self.action_new_product.emit)
        actions_layout.addWidget(btn_new)

        # Export CSV button (secondary)
        btn_export = QPushButton(f"📥 {t('dash_export_csv')}")
        btn_export.setMinimumHeight(38)
        btn_export.setMaximumWidth(180)
        btn_export.setStyleSheet(self._secondary_button_style(tk))
        btn_export.clicked.connect(self.action_export.emit)
        actions_layout.addWidget(btn_export)

        # Stretch to push buttons to left
        actions_layout.addStretch()

        return actions_container

    def _primary_button_style(self, tk) -> str:
        """Generate stylesheet for primary (blue) button."""
        hover_color = "#2563EB" if tk.is_dark else "#1D4ED8"
        return f"""
            QPushButton {{
                background: {tk.blue};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 12px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background: {hover_color};
            }}
            QPushButton:pressed {{
                background: {hover_color};
                opacity: 0.9;
            }}
        """

    def _secondary_button_style(self, tk) -> str:
        """Generate stylesheet for secondary (outline) button."""
        return f"""
            QPushButton {{
                background: {tk.card2};
                color: {tk.t1};
                border: 1px solid {tk.border2};
                border-radius: 8px;
                font-weight: 600;
                font-size: 12px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background: {tk.border};
                border-color: {tk.border2};
            }}
            QPushButton:pressed {{
                background: {tk.border2};
            }}
        """

    def update_data(self, summary: dict) -> None:
        """
        Update all card values from a summary dictionary.

        Expected keys:
            - total_products: int
            - total_units: int
            - low_stock_count: int
            - out_of_stock_count: int
            - total_value: int or float
        """
        # Total Products
        self._cards["total_products"].set_value(
            int(summary.get("total_products") or 0),
            t("card_total_products"),
        )

        # Total Units
        self._cards["total_units"].set_value(
            int(summary.get("total_units") or 0),
            t("card_total_units"),
        )

        # Low Stock
        self._cards["low_stock"].set_value(
            int(summary.get("low_stock_count") or 0),
            t("card_low_stock"),
        )

        # Out of Stock
        self._cards["out_of_stock"].set_value(
            int(summary.get("out_of_stock_count") or 0),
            t("card_out_of_stock"),
        )

        # Inventory Value (formatted as currency)
        total_value = float(summary.get("inventory_value") or summary.get("total_value") or 0)
        formatted_value = self._shop_config.format_currency(total_value)
        self._cards["inventory_value"].set_formatted_value(
            formatted_value,
            t("dash_inventory_value"),
        )

    def retranslate(self) -> None:
        """Update all text labels after language change."""
        # Retranslate all cards
        self._cards["total_products"].set_value(
            self._cards["total_products"]._value,
            t("card_total_products"),
        )
        self._cards["total_units"].set_value(
            self._cards["total_units"]._value,
            t("card_total_units"),
        )
        self._cards["low_stock"].set_value(
            self._cards["low_stock"]._value,
            t("card_low_stock"),
        )
        self._cards["out_of_stock"].set_value(
            self._cards["out_of_stock"]._value,
            t("card_out_of_stock"),
        )
        self._cards["inventory_value"].set_value(
            self._cards["inventory_value"]._value,
            t("dash_inventory_value"),
        )

        # Retranslate action buttons
        self._rebuild_actions_buttons()

    def apply_theme(self) -> None:
        """Re-apply all theme colors after a theme change.

        Uses setUpdatesEnabled(False) to suppress the individual repaint events
        triggered by each setStyleSheet() call, flushing a single repaint at the
        end instead of N separate ones (N = cards + buttons + containers).
        """
        self.setUpdatesEnabled(False)
        try:
            tk = THEME.tokens

            # Re-style every summary card (accent border varies per card)
            for card in self._cards.values():
                card._apply_style()

            # Re-style the quick-actions container via unpolish/polish so the
            # global QSS rule for #dashboard_actions takes effect automatically.
            container = self.findChild(QFrame, "dashboard_actions")
            if container:
                container.style().unpolish(container)
                container.style().polish(container)
                for btn in container.findChildren(QPushButton):
                    btn.style().unpolish(btn)
                    btn.style().polish(btn)
        finally:
            self.setUpdatesEnabled(True)
            self.update()  # single repaint for the whole dashboard

    def _rebuild_actions_buttons(self) -> None:
        """Rebuild action buttons with new translations (internal helper)."""
        container = self.findChild(QFrame, "dashboard_actions")
        if not container:
            return

        buttons = container.findChildren(QPushButton)
        if len(buttons) >= 2:
            buttons[0].setText(f"➕ {t('dash_new_product')}")
            buttons[1].setText(f"📥 {t('dash_export_csv')}")
