"""
app/ui/components/toast.py — Toast notification system.

Provides slide-in/out notification toasts that appear in the top-right
corner of the main window. Supports success, warning, error, and info types.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
    QGraphicsOpacityEffect, QWidget,
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, pyqtSignal
from PyQt6.QtGui import QFont

from app.core.theme import THEME, _rgba


class Toast(QFrame):
    """A single toast notification widget."""

    # Emitted just before the widget is scheduled for deletion.
    # ToastManager connects to this instead of monkey-patching _dismiss.
    dismissed = pyqtSignal()

    _TYPES = {
        "success": ("✓", "green"),
        "warning": ("⚠", "orange"),
        "error":   ("✕", "red"),
        "info":    ("ℹ", "blue"),
    }

    def __init__(self, message: str, toast_type: str = "info",
                 duration: int = 3000, parent=None,
                 action_text: str = "", action_callback=None):
        super().__init__(parent)
        self._duration = duration
        self.setFixedWidth(340)
        self.setMinimumHeight(52)

        tk = THEME.tokens
        icon_char, color_key = self._TYPES.get(toast_type, ("ℹ", "blue"))
        color = getattr(tk, color_key, tk.blue)
        bg = _rgba(color, "18")
        border = _rgba(color, "50")

        self.setStyleSheet(
            f"QFrame {{ background: {tk.card}; border: 1px solid {border};"
            f"border-left: 3px solid {color}; border-radius: 8px; }}"
        )

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 8, 10)
        lay.setSpacing(10)

        # Icon
        icon_lbl = QLabel(icon_char)
        icon_lbl.setFixedSize(24, 24)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(
            f"color: {color}; font-size: 14px; font-weight: 700;"
            f"background: {_rgba(color, '20')}; border-radius: 12px;"
            "border: none;"
        )
        lay.addWidget(icon_lbl)

        # Message
        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(
            f"color: {tk.t1}; font-size: 12px; font-weight: 500;"
            "border: none; background: transparent;"
        )
        lay.addWidget(msg_lbl, 1)

        # Optional action button (e.g. Undo)
        if action_text and action_callback:
            action_btn = QPushButton(action_text)
            action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            action_btn.setFixedHeight(26)
            action_btn.setStyleSheet(
                f"background: {color}; color: #fff; border: none;"
                "border-radius: 4px; padding: 2px 10px; font-size: 11px;"
                "font-weight: 600;"
            )
            action_btn.clicked.connect(lambda: (action_callback(), self._dismiss()))
            lay.addWidget(action_btn)

        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(
            f"background: transparent; color: {tk.t3}; border: none;"
            "font-size: 14px; font-weight: 400; border-radius: 10px;"
        )
        close_btn.clicked.connect(self._dismiss)
        lay.addWidget(close_btn)

        # Auto-dismiss timer
        if duration > 0:
            QTimer.singleShot(duration, self._dismiss)

    def _dismiss(self):
        """Hide, emit dismissed signal, then schedule C++ object deletion."""
        if not self.isVisible():
            return  # guard against double-dismiss (timer + button click)
        self.setVisible(False)
        self.dismissed.emit()
        self.deleteLater()


class ToastManager:
    """Manages toast notifications for a parent widget.

    Usage:
        self._toasts = ToastManager(self)
        self._toasts.success("Item saved!")
        self._toasts.error("Failed to save!")
    """

    def __init__(self, parent: QWidget):
        self._parent = parent
        self._toasts: list[Toast] = []
        self._margin_top = 50
        self._margin_right = 16
        self._spacing = 8

    def success(self, message: str, duration: int = 3000,
                action_text: str = "", action_callback=None):
        self._show(message, "success", duration, action_text, action_callback)

    def warning(self, message: str, duration: int = 4000,
                action_text: str = "", action_callback=None):
        self._show(message, "warning", duration, action_text, action_callback)

    def error(self, message: str, duration: int = 5000,
              action_text: str = "", action_callback=None):
        self._show(message, "error", duration, action_text, action_callback)

    def info(self, message: str, duration: int = 3000,
             action_text: str = "", action_callback=None):
        self._show(message, "info", duration, action_text, action_callback)

    def _show(self, message: str, toast_type: str, duration: int,
              action_text: str = "", action_callback=None):
        # Remove any toasts whose C++ backing has already been freed.
        self._purge()

        toast = Toast(message, toast_type, duration, self._parent,
                      action_text=action_text, action_callback=action_callback)
        toast.show()
        self._toasts.append(toast)
        self._reposition()

        # When the toast dismisses itself (timer or button) it emits dismissed.
        # We react by pruning the list and restacking the survivors.
        toast.dismissed.connect(self._on_toast_dismissed)

    def _purge(self) -> None:
        """Remove toasts whose C++ wrapper has been freed or are no longer visible."""
        alive = []
        for t in self._toasts:
            try:
                if t.isVisible():
                    alive.append(t)
            except RuntimeError:
                pass  # C++ object already deleted — drop silently
        self._toasts = alive

    def _on_toast_dismissed(self) -> None:
        """Called when any Toast emits dismissed; restack survivors."""
        self._purge()
        self._reposition()

    def _reposition(self):
        """Stack toasts from top-right corner."""
        y = self._margin_top
        pw = self._parent.width()
        for toast in self._toasts:
            try:
                if toast.isVisible():
                    x = pw - toast.width() - self._margin_right
                    toast.move(x, y)
                    toast.raise_()
                    y += toast.height() + self._spacing
            except RuntimeError:
                pass  # safety net — shouldn't happen after _purge
