"""
app/ui/components/dashboard_widget.py — Professional dashboard widget with summary cards and quick actions.

Features:
  - 5 summary cards (Total Products, Total Units, Low Stock, Out of Stock, Inventory Value)
  - Quick action buttons (New Product, Stock In, Stock Out, Export CSV)
  - Theme-aware styling with rounded corners and shadow effects
  - i18n support with retranslate() method
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QPushButton, QLabel,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor

from app.core.theme import THEME, qc
from app.core.i18n import t
from app.core.config import ShopConfig


# ── Summary Card Widget ────────────────────────────────────────────────────────

class SummaryCard(QFrame):
    """
    Professional summary card displaying a metric.

    Shows:
      - Large number (28pt, bold, colored)
      - Small label (10pt, muted)
      - Subtle background and border
      - Shadow effect
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value: int = 0
        self._label: str = ""
        self._color: str = "#4A9EFF"  # Default blue

        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Plain)
        self.setMinimumHeight(90)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # ── Shadow effect ────────────────────────────
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        tk = THEME.tokens
        shadow_color = qc(tk.t4, 40)
        shadow.setColor(shadow_color)
        self.setGraphicsEffect(shadow)

        # ── Layout ───────────────────────────────────
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        # Large number
        self._number_label = QLabel("0")
        number_font = QFont()
        number_font.setPointSize(28)
        number_font.setBold(True)
        self._number_label.setFont(number_font)
        self._number_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._number_label)

        # Small label
        self._text_label = QLabel("")
        text_font = QFont()
        text_font.setPointSize(10)
        self._text_label.setFont(text_font)
        self._text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._text_label)

        self._apply_style()

    def set_value(self, value: int, label: str, color: str | None = None) -> None:
        """Update card with new value, label, and optional color."""
        self._value = value
        self._label = label
        if color:
            self._color = color

        self._number_label.setText(str(value))
        self._text_label.setText(label)
        self._apply_style()

    def _apply_style(self) -> None:
        """Apply theme-aware styling."""
        tk = THEME.tokens

        # Number color from parameter
        self._number_label.setStyleSheet(f"""
            QLabel {{
                color: {self._color};
            }}
        """)

        # Text color (muted)
        self._text_label.setStyleSheet(f"""
            QLabel {{
                color: {tk.t3};
            }}
        """)

        # Card background and border
        self.setStyleSheet(f"""
            SummaryCard {{
                background: {tk.card};
                border: 1px solid {tk.border};
                border-radius: 12px;
            }}
            SummaryCard:hover {{
                background: {tk.card2};
                border-color: {tk.border2};
            }}
        """)


# ── Dashboard Widget ──────────────────────────────────────────────────────────

class DashboardWidget(QWidget):
    """
    Professional dashboard section with summary cards and quick action buttons.

    Signals:
        action_new_product: User clicked "New Product" button
        action_stock_in: User clicked "Stock In" button
        action_stock_out: User clicked "Stock Out" button
        action_export: User clicked "Export CSV" button
    """

    action_new_product = pyqtSignal()
    action_stock_in = pyqtSignal()
    action_stock_out = pyqtSignal()
    action_export = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._shop_config = ShopConfig()
        self._cards: dict[str, SummaryCard] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the dashboard layout."""
        tk = THEME.tokens

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(16)

        # ── Summary Cards Row ────────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setContentsMargins(0, 0, 0, 0)
        cards_row.setSpacing(16)

        # Total Products
        card_total = SummaryCard()
        card_total.set_value(0, t("card_total_products"), tk.blue)
        self._cards["total_products"] = card_total
        cards_row.addWidget(card_total)

        # Total Units
        card_units = SummaryCard()
        card_units.set_value(0, t("card_total_units"), tk.green)
        self._cards["total_units"] = card_units
        cards_row.addWidget(card_units)

        # Low Stock
        card_low = SummaryCard()
        card_low.set_value(0, t("card_low_stock"), tk.orange)
        self._cards["low_stock"] = card_low
        cards_row.addWidget(card_low)

        # Out of Stock
        card_out = SummaryCard()
        card_out.set_value(0, t("card_out_of_stock"), tk.red)
        self._cards["out_of_stock"] = card_out
        cards_row.addWidget(card_out)

        # Inventory Value
        card_value = SummaryCard()
        card_value.set_value(0, t("dash_inventory_value"), tk.purple)
        self._cards["inventory_value"] = card_value
        cards_row.addWidget(card_value)

        main_layout.addLayout(cards_row)

        # ── Quick Actions Row ────────────────────────────────────────
        actions_container = QFrame()
        actions_container.setObjectName("dashboard_actions")
        actions_container.setStyleSheet(f"""
            QFrame#dashboard_actions {{
                background: {tk.card};
                border: 1px solid {tk.border};
                border-radius: 10px;
                padding: 12px;
            }}
        """)

        actions_layout = QVBoxLayout(actions_container)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(0)

        # Label
        actions_title = QLabel(t("dash_quick_actions"))
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        actions_title.setFont(title_font)
        actions_title.setStyleSheet(f"color: {tk.t1};")
        actions_layout.addWidget(actions_title)
        actions_layout.addSpacing(10)

        # Buttons row
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(8)

        # New Product button
        btn_new = QPushButton(t("dash_new_product"))
        btn_new.setMinimumHeight(40)
        btn_new.setStyleSheet(self._button_style("blue"))
        btn_new.clicked.connect(self.action_new_product.emit)
        buttons_layout.addWidget(btn_new)

        # Export CSV button
        btn_export = QPushButton(t("dash_export_csv"))
        btn_export.setMinimumHeight(40)
        btn_export.setStyleSheet(self._button_style("secondary"))
        btn_export.clicked.connect(self.action_export.emit)
        buttons_layout.addWidget(btn_export)

        actions_layout.addLayout(buttons_layout)

        main_layout.addWidget(actions_container)
        main_layout.addStretch()

    def _button_style(self, button_type: str) -> str:
        """Generate stylesheet for button based on type."""
        tk = THEME.tokens

        color_map = {
            "blue": (tk.blue, "#2563EB" if tk.is_dark else "#1D4ED8"),
            "green": (tk.green, "#059669" if tk.is_dark else "#047857"),
            "red": (tk.red, "#DC2626" if tk.is_dark else "#B91C1C"),
            "secondary": (tk.border2, tk.border),
        }

        if button_type == "secondary":
            base_color, hover_color = color_map["secondary"]
            return f"""
                QPushButton {{
                    background: {tk.card2};
                    color: {tk.t1};
                    border: 1px solid {base_color};
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 13px;
                    padding: 8px 16px;
                }}
                QPushButton:hover {{
                    background: {hover_color};
                    border-color: {tk.t2};
                }}
                QPushButton:pressed {{
                    background: {tk.border};
                }}
            """
        else:
            base_color, hover_color = color_map[button_type]
            return f"""
                QPushButton {{
                    background: {base_color};
                    color: #FFFFFF;
                    border: none;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 13px;
                    padding: 8px 16px;
                }}
                QPushButton:hover {{
                    background: {hover_color};
                }}
                QPushButton:pressed {{
                    opacity: 0.8;
                }}
            """

    def update_data(self, summary: dict) -> None:
        """
        Update card values from a summary dictionary.

        Expected keys:
            - total_products: int
            - total_units: int
            - low_stock_count: int
            - out_of_stock_count: int
            - total_value: int or float
        """
        tk = THEME.tokens
        self._cards["total_products"].set_value(
            int(summary.get("total_products") or 0),
            t("card_total_products"), tk.blue,
        )
        self._cards["total_units"].set_value(
            int(summary.get("total_units") or 0),
            t("card_total_units"), tk.green,
        )
        self._cards["low_stock"].set_value(
            int(summary.get("low_stock_count") or 0),
            t("card_low_stock"), tk.orange,
        )
        self._cards["out_of_stock"].set_value(
            int(summary.get("out_of_stock_count") or 0),
            t("card_out_of_stock"), tk.red,
        )
        self._cards["inventory_value"].set_value(
            int(summary.get("total_value") or 0),
            t("dash_inventory_value"), tk.purple,
        )

    def retranslate(self) -> None:
        """Update all labels after language change."""
        tk = THEME.tokens

        # Update card labels
        self._cards["total_products"].set_value(
            self._cards["total_products"]._value,
            t("card_total_products"),
            tk.blue
        )

        self._cards["total_units"].set_value(
            self._cards["total_units"]._value,
            t("card_total_units"),
            tk.green
        )

        self._cards["low_stock"].set_value(
            self._cards["low_stock"]._value,
            t("card_low_stock"),
            tk.orange
        )

        self._cards["out_of_stock"].set_value(
            self._cards["out_of_stock"]._value,
            t("card_out_of_stock"),
            tk.red
        )

        self._cards["inventory_value"].set_value(
            self._cards["inventory_value"]._value,
            t("dash_inventory_value"),
            tk.purple
        )

    def apply_theme(self) -> None:
        """Re-apply theme colors after theme change."""
        tk = THEME.tokens

        # Reapply card styles
        for card in self._cards.values():
            card._apply_style()

        # Reapply actions container background
        container = self.findChild(QFrame, "dashboard_actions")
        if container:
            container.setStyleSheet(f"""
                QFrame#dashboard_actions {{
                    background: {tk.card};
                    border: 1px solid {tk.border};
                    border-radius: 10px;
                    padding: 12px;
                }}
            """)
