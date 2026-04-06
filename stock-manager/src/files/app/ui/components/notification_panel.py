"""
app/ui/components/notification_panel.py — Unified notification dropdown.

A frameless popup that appears under the header bell button.  It consolidates
all app notifications into one panel:

  • 🔄  Update Available  — with "Install Now" / "Remind Later" actions
  • ⚠️  Stock Alerts     — low stock, expiring, expired summaries +
                           "View All" button

Uses Qt.WindowType.Popup so it auto-dismisses when the user clicks elsewhere,
exactly like a native dropdown menu.
"""
from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget,
)

from app.core.i18n import t
from app.core.theme import THEME, _rgba
from app.services.update_service import UpdateManifest


# ── Data container ─────────────────────────────────────────────────────────────

@dataclass
class StockAlertCounts:
    low:      int = 0   # low-stock items
    expiring: int = 0   # expiring within 30 days
    expired:  int = 0   # already expired

    @property
    def total(self) -> int:
        return self.low + self.expiring + self.expired

    @property
    def is_critical(self) -> bool:
        return self.expired > 0


# ── NotificationPanel ──────────────────────────────────────────────────────────

class NotificationPanel(QFrame):
    """
    Frameless popup notification panel.

    Signals:
        view_alerts_requested()           — open LowStockDialog
        install_update_requested(object)  — pass manifest to show update banner
        remind_later()                    — hide update notification temporarily
        closed()                          — panel was dismissed (any reason)
    """

    view_alerts_requested   = pyqtSignal()
    install_update_requested = pyqtSignal(object)   # UpdateManifest
    remind_later            = pyqtSignal()
    closed                  = pyqtSignal()

    _PANEL_WIDTH = 380

    def __init__(
        self,
        pending_update: UpdateManifest | None,
        stock: StockAlertCounts,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._pending_update = pending_update
        self._stock = stock

        # Popup flag: auto-dismisses when clicking outside
        self.setWindowFlags(
            Qt.WindowType.Popup |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("notif_panel")
        self.setFixedWidth(self._PANEL_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Maximum)

        self._apply_style()
        self._build()
        self.adjustSize()

    # ── Styling ────────────────────────────────────────────────────────────────

    def _apply_style(self) -> None:
        tk = THEME.tokens
        self.setStyleSheet(
            f"QFrame#notif_panel {{"
            f"  background: {tk.card};"
            f"  border: 1px solid {tk.border};"
            f"  border-radius: 10px;"
            f"}}"
            # Section separator labels
            f"QLabel#notif_section {{"
            f"  color: {tk.t4};"
            f"  font-size: 10px;"
            f"  font-weight: bold;"
            f"  letter-spacing: 1px;"
            f"  padding: 0 0 2px 0;"
            f"}}"
            # Item text
            f"QLabel#notif_body {{"
            f"  color: {tk.t2};"
            f"  font-size: 12px;"
            f"}}"
            # Primary action button (Install, View All)
            f"QPushButton#notif_primary {{"
            f"  background: {tk.blue};"
            f"  color: #ffffff;"
            f"  border: none; border-radius: 6px;"
            f"  font-size: 12px; font-weight: bold;"
            f"  padding: 5px 14px;"
            f"}}"
            f"QPushButton#notif_primary:hover  {{ background: {_rgba(tk.blue, 'DD')}; }}"
            f"QPushButton#notif_primary:pressed {{ background: {_rgba(tk.blue, 'BB')}; }}"
            # Secondary action (Remind Later)
            f"QPushButton#notif_secondary {{"
            f"  background: transparent;"
            f"  color: {tk.t3};"
            f"  border: 1px solid {tk.border};"
            f"  border-radius: 6px;"
            f"  font-size: 12px;"
            f"  padding: 5px 14px;"
            f"}}"
            f"QPushButton#notif_secondary:hover  {{ background: {_rgba(tk.blue, '15')}; color: {tk.t1}; }}"
            # Close button
            f"QPushButton#notif_close {{"
            f"  background: transparent; color: {tk.t3};"
            f"  border: none; font-size: 14px;"
            f"  padding: 0; margin: 0;"
            f"}}"
            f"QPushButton#notif_close:hover {{ color: {tk.t1}; }}"
            # Section divider
            f"QFrame#notif_sep {{ background: {tk.border}; }}"
        )

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Header bar ────────────────────────────────────────────────────────
        lay.addWidget(self._build_header())

        has_content = False

        # ── Update section ────────────────────────────────────────────────────
        if self._pending_update:
            lay.addWidget(self._sep())
            lay.addWidget(self._build_update_section())
            has_content = True

        # ── Stock alerts section ───────────────────────────────────────────────
        if self._stock.total > 0:
            lay.addWidget(self._sep())
            lay.addWidget(self._build_stock_section())
            has_content = True

        # ── All-clear ─────────────────────────────────────────────────────────
        if not has_content:
            lay.addWidget(self._sep())
            lay.addWidget(self._build_empty_section())

        lay.addWidget(self._sep())
        lay.addSpacing(4)

    def _build_header(self) -> QWidget:
        tk = THEME.tokens
        w = QWidget()
        w.setStyleSheet(f"background: transparent;")
        h = QHBoxLayout(w)
        h.setContentsMargins(16, 12, 12, 12)
        h.setSpacing(8)

        total = (1 if self._pending_update else 0) + self._stock.total

        icon = QLabel("🔔")
        icon.setFont(QFont("Segoe UI Emoji", 14))
        icon.setStyleSheet("background: transparent;")
        h.addWidget(icon)

        title = QLabel(t("notif_title", n=total) if total > 0 else t("notif_title_clear"))
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {tk.t1}; background: transparent;")
        h.addWidget(title)
        h.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setObjectName("notif_close")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self._dismiss)
        h.addWidget(close_btn)

        return w

    def _build_update_section(self) -> QWidget:
        tk = THEME.tokens
        m = self._pending_update
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(8)

        # Section label
        sec = QLabel(t("notif_sec_update").upper())
        sec.setObjectName("notif_section")
        lay.addWidget(sec)

        # Row: colored dot + version title
        row = QHBoxLayout()
        row.setSpacing(8)

        dot = QLabel("●")
        dot.setStyleSheet(f"color: {tk.green}; font-size: 10px; background: transparent;")
        dot.setFixedWidth(14)
        row.addWidget(dot)

        title = QLabel(t("notif_update_title", version=m.version))
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {tk.t1}; background: transparent;")
        row.addWidget(title, 1)
        lay.addLayout(row)

        # Release notes preview
        if m.release_notes:
            notes = m.release_notes[:100] + ("…" if len(m.release_notes) > 100 else "")
            notes_lbl = QLabel(notes)
            notes_lbl.setObjectName("notif_body")
            notes_lbl.setWordWrap(True)
            notes_lbl.setStyleSheet(f"color: {tk.t3}; font-size: 11px; background: transparent;")
            lay.addWidget(notes_lbl)

        if m.release_date:
            date_lbl = QLabel(t("notif_released", date=m.release_date))
            date_lbl.setStyleSheet(f"color: {tk.t4}; font-size: 10px; background: transparent;")
            lay.addWidget(date_lbl)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        install_btn = QPushButton(t("notif_install_now"))
        install_btn.setObjectName("notif_primary")
        install_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        install_btn.clicked.connect(self._on_install)
        btn_row.addWidget(install_btn)

        later_btn = QPushButton(t("notif_remind_later"))
        later_btn.setObjectName("notif_secondary")
        later_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        later_btn.clicked.connect(self._on_remind_later)
        btn_row.addWidget(later_btn)

        btn_row.addStretch()
        lay.addLayout(btn_row)

        return w

    def _build_stock_section(self) -> QWidget:
        tk = THEME.tokens
        s = self._stock
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(8)

        # Section label
        sec = QLabel(t("notif_sec_stock").upper())
        sec.setObjectName("notif_section")
        lay.addWidget(sec)

        # Individual alert lines
        for count, key, color in (
            (s.expired,  "notif_stock_expired",  tk.red),
            (s.expiring, "notif_stock_expiring", tk.orange),
            (s.low,      "notif_stock_low",       tk.yellow),
        ):
            if count == 0:
                continue
            row = QHBoxLayout()
            row.setSpacing(8)

            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 10px; background: transparent;")
            dot.setFixedWidth(14)
            row.addWidget(dot)

            lbl = QLabel(t(key, n=count))
            lbl.setStyleSheet(f"color: {tk.t1}; font-size: 12px; background: transparent;")
            row.addWidget(lbl, 1)
            lay.addLayout(row)

        # View All button
        btn_row = QHBoxLayout()
        view_btn = QPushButton(t("notif_view_alerts"))
        view_btn.setObjectName("notif_primary")
        view_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        view_btn.clicked.connect(self._on_view_alerts)
        btn_row.addWidget(view_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        return w

    def _build_empty_section(self) -> QWidget:
        tk = THEME.tokens
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 20, 16, 20)
        lay.setSpacing(6)

        icon = QLabel("✅")
        icon.setFont(QFont("Segoe UI Emoji", 24))
        icon.setStyleSheet("background: transparent;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(icon)

        msg = QLabel(t("notif_all_clear"))
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet(f"color: {tk.t3}; font-size: 12px; background: transparent;")
        lay.addWidget(msg)

        return w

    @staticmethod
    def _sep() -> QFrame:
        f = QFrame()
        f.setObjectName("notif_sep")
        f.setFixedHeight(1)
        return f

    # ── Actions ────────────────────────────────────────────────────────────────

    def _on_install(self) -> None:
        self.install_update_requested.emit(self._pending_update)
        self.hide()     # hideEvent emits closed

    def _on_remind_later(self) -> None:
        self.remind_later.emit()
        self.hide()     # hideEvent emits closed

    def _on_view_alerts(self) -> None:
        self.view_alerts_requested.emit()
        self.hide()     # hideEvent emits closed

    def _dismiss(self) -> None:
        self.hide()     # hideEvent will emit closed

    # ── Positioning ────────────────────────────────────────────────────────────

    def popup_below(self, anchor_widget: QWidget) -> None:
        """Position and show the panel directly below anchor_widget."""
        # Map anchor's bottom-left to global coordinates
        global_pos = anchor_widget.mapToGlobal(
            QPoint(0, anchor_widget.height() + 4)
        )
        # Align right edge of panel with right edge of anchor
        global_pos.setX(global_pos.x() + anchor_widget.width() - self._PANEL_WIDTH)
        self.move(global_pos)
        self.show()
        self.raise_()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self.closed.emit()      # single canonical emission point
