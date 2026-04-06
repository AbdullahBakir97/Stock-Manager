"""
app/ui/components/language_switcher.py — Professional language selector.

Replaces the old three-button segmented control with a single dropdown button
that shows the active language name and opens a polished popup on click.

Anatomy:
  ┌──────────────────────┐
  │  🌐  English   ▾    │  ← trigger (LanguageSwitcher)
  └──────────────────────┘
            ↓ click
  ┌─────────────────────────┐
  │  ✓  English       EN   │  ← active row
  │     Deutsch       DE   │
  │     العربية       AR   │
  └─────────────────────────┘

Uses Qt.WindowType.Popup so the dropdown auto-dismisses when the user
clicks anywhere else — no extra event filtering needed.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QSizePolicy,
    QVBoxLayout, QWidget,
)

from app.core.theme import THEME, _rgba

# ── Language registry ──────────────────────────────────────────────────────────
# (code, native_name, display_label_in_trigger)
_LANGS: list[tuple[str, str, str]] = [
    ("EN", "English",   "English"),
    ("DE", "Deutsch",   "Deutsch"),
    ("AR", "العربية",   "العربية"),
]


# ── Dropdown row ───────────────────────────────────────────────────────────────

class _LangRow(QFrame):
    """Single selectable row inside the language dropdown."""

    clicked = pyqtSignal(str)   # emits the language code

    def __init__(
        self,
        code: str,
        native: str,
        active: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._code   = code
        self._active = active

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(40)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._paint(hovered=False)
        self._build(native)

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build(self, native: str) -> None:
        tk = THEME.tokens
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 14, 0)
        lay.setSpacing(10)

        # Checkmark (only visible for active)
        self._check = QLabel("✓" if self._active else "")
        self._check.setFixedWidth(16)
        self._check.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self._check.setStyleSheet(f"color: {tk.blue}; background: transparent;")
        lay.addWidget(self._check)

        # Native language name
        name = QLabel(native)
        weight = QFont.Weight.Bold if self._active else QFont.Weight.Normal
        name.setFont(QFont("Segoe UI", 11, weight))
        name.setStyleSheet(
            f"color: {tk.t1 if self._active else tk.t2}; background: transparent;"
        )
        lay.addWidget(name, 1)

        # Language code (dimmed)
        code_lbl = QLabel(self._code)
        code_lbl.setStyleSheet(f"color: {tk.t4}; font-size: 10px; background: transparent;")
        code_lbl.setFixedWidth(22)
        code_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(code_lbl)

    # ── Hover / paint ──────────────────────────────────────────────────────────

    def _paint(self, hovered: bool) -> None:
        tk = THEME.tokens
        if hovered:
            bg = _rgba(tk.blue, "18")
        elif self._active:
            bg = _rgba(tk.blue, "12")
        else:
            bg = "transparent"
        self.setStyleSheet(
            f"QFrame {{ background: {bg}; border-radius: 6px; }}"
        )

    def enterEvent(self, event) -> None:
        self._paint(hovered=True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._paint(hovered=False)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._code)
        super().mousePressEvent(event)


# ── Dropdown popup ─────────────────────────────────────────────────────────────

class _LangDropdown(QFrame):
    """Frameless Popup containing all language rows."""

    selected = pyqtSignal(str)

    _WIDTH = 210

    def __init__(self, current: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current = current

        self.setWindowFlags(
            Qt.WindowType.Popup |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("lang_dropdown")
        self.setFixedWidth(self._WIDTH)

        self._apply_style()
        self._build()
        self.adjustSize()

    def _apply_style(self) -> None:
        tk = THEME.tokens
        self.setStyleSheet(
            f"QFrame#lang_dropdown {{"
            f"  background: {tk.card};"
            f"  border: 1px solid {tk.border};"
            f"  border-radius: 10px;"
            f"}}"
        )

    def _build(self) -> None:
        tk = THEME.tokens
        lay = QVBoxLayout(self)
        lay.setContentsMargins(5, 6, 5, 6)
        lay.setSpacing(2)

        # Header label
        header = QLabel("Language / Sprache / اللغة")
        header.setStyleSheet(
            f"color: {tk.t4}; font-size: 10px; font-weight: bold;"
            f" letter-spacing: 0.5px; background: transparent;"
            f" padding: 2px 8px 4px 8px;"
        )
        lay.addWidget(header)

        # Divider
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {tk.border};")
        lay.addWidget(sep)
        lay.addSpacing(2)

        # Language rows
        for code, native, _ in _LANGS:
            row = _LangRow(code, native, active=(code == self._current))
            row.clicked.connect(self._on_row_clicked)
            lay.addWidget(row)

    def _on_row_clicked(self, code: str) -> None:
        self.selected.emit(code)
        self.hide()

    def popup_below(self, anchor: QWidget) -> None:
        """Position and show directly below the anchor widget."""
        global_pos = anchor.mapToGlobal(QPoint(0, anchor.height() + 4))
        self.move(global_pos)
        self.show()
        self.raise_()


# ── LanguageSwitcher (public widget) ──────────────────────────────────────────

class LanguageSwitcher(QWidget):
    """
    Drop-in replacement for the old segmented EN/DE/AR button bar.

    Emits lang_changed(code) — same signal as the old buttons did via HeaderBar.
    Call set_lang(code) to update the display after an external language change.
    """

    lang_changed = pyqtSignal(str)

    def __init__(
        self,
        current_lang: str = "EN",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._current   = current_lang
        self._dropdown: _LangDropdown | None = None
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._build()

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._trigger = _TriggerButton(self._current, parent=self)
        self._trigger.clicked_signal.connect(self._toggle_dropdown)
        lay.addWidget(self._trigger)

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_lang(self, code: str) -> None:
        """Update the trigger label (called after language change is applied)."""
        self._current = code
        self._trigger.update_lang(code)

    # ── Dropdown management ────────────────────────────────────────────────────

    def _toggle_dropdown(self) -> None:
        if self._dropdown and self._dropdown.isVisible():
            self._dropdown.hide()
            return

        dd = _LangDropdown(self._current, parent=None)
        dd.selected.connect(self._on_selected)
        dd.popup_below(self._trigger)
        self._dropdown = dd

    def _on_selected(self, code: str) -> None:
        self._current = code
        self._trigger.update_lang(code)
        self.lang_changed.emit(code)


# ── Trigger button ─────────────────────────────────────────────────────────────

class _TriggerButton(QFrame):
    """The visible pill-shaped button that shows the current language."""

    clicked_signal = pyqtSignal()

    def __init__(self, current: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current = current

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(34)
        self.setFixedWidth(130)
        self.setObjectName("lang_trigger")

        self._apply_style(False)
        self._build()

    def _build(self) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 8, 0)
        lay.setSpacing(6)

        # Globe icon
        globe = QLabel("🌐")
        globe.setFont(QFont("Segoe UI Emoji", 11))
        globe.setStyleSheet("background: transparent;")
        lay.addWidget(globe)

        # Language name
        self._name_lbl = QLabel(self._lang_name(self._current))
        self._name_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        self._name_lbl.setStyleSheet("background: transparent;")
        lay.addWidget(self._name_lbl, 1)

        # Chevron
        chevron = QLabel("▾")
        chevron.setFont(QFont("Segoe UI", 8))
        chevron.setStyleSheet("background: transparent;")
        lay.addWidget(chevron)

    def update_lang(self, code: str) -> None:
        self._current = code
        self._name_lbl.setText(self._lang_name(code))

    @staticmethod
    def _lang_name(code: str) -> str:
        return next((n for c, n, _ in _LANGS if c == code), code)

    # ── Hover ──────────────────────────────────────────────────────────────────

    def _apply_style(self, hovered: bool) -> None:
        tk = THEME.tokens
        bg  = _rgba(tk.blue, "18") if hovered else tk.card
        brd = tk.blue              if hovered else tk.border
        col = tk.t1                if hovered else tk.t2
        self.setStyleSheet(
            f"QFrame#lang_trigger {{"
            f"  background: {bg};"
            f"  border: 1px solid {brd};"
            f"  border-radius: 8px;"
            f"}}"
            f"QLabel {{ color: {col}; }}"
        )

    def enterEvent(self, event) -> None:
        self._apply_style(hovered=True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._apply_style(hovered=False)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked_signal.emit()
        super().mousePressEvent(event)
