"""
app/ui/components/splash_screen.py — Professional animated startup splash.

Shows a branded, frameless loading screen with a progress bar and
step labels while the app initialises in the background.
"""
from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QBrush, QFont, QPen


class SplashScreen(QWidget):
    """Frameless branded splash screen with animated progress bar.

    Usage (in main.py):
        splash = SplashScreen()
        splash.show()
        splash.set_progress(25, "Initialising database…")
        # … after MainWindow is ready:
        splash.finish()
    """

    finished = pyqtSignal()

    # Dark emerald / charcoal palette — always dark regardless of user theme
    _BG_TOP    = "#0A0A0A"
    _BG_BOT    = "#111827"
    _ACCENT    = "#10B981"   # emerald
    _ACCENT2   = "#059669"
    _TEXT      = "#F9FAFB"
    _SUBTEXT   = "#9CA3AF"
    _TRACK     = "#1F2937"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(480, 300)
        self._center_on_screen()

        self._progress = 0          # 0–100
        self._target   = 0
        self._step_label = ""

        # Smooth progress animation
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)   # ~60 fps
        self._anim_timer.timeout.connect(self._tick_progress)
        self._anim_timer.start()

        # Dot animation
        self._dot_timer = QTimer(self)
        self._dot_timer.setInterval(400)
        self._dot_timer.timeout.connect(self._tick_dots)
        self._dot_timer.start()
        self._dots = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def set_progress(self, pct: int, label: str = "") -> None:
        """Animate progress bar to `pct` (0–100) and show `label`."""
        self._target = max(self._progress, min(100, pct))
        if label:
            self._step_label = label
        self.update()

    def finish(self) -> None:
        """Animate to 100 % then fade out."""
        self._target = 100
        self._step_label = "Ready!"
        # Give a moment to show 100 % before closing
        QTimer.singleShot(350, self._close_splash)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _center_on_screen(self) -> None:
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            sg = screen.availableGeometry()
            self.move(
                sg.left() + (sg.width()  - self.width())  // 2,
                sg.top()  + (sg.height() - self.height()) // 2,
            )

    def _tick_progress(self) -> None:
        if self._progress < self._target:
            self._progress = min(self._target, self._progress + 2)
            self.update()

    def _tick_dots(self) -> None:
        self._dots = (self._dots + 1) % 4
        self.update()

    def _close_splash(self) -> None:
        self._anim_timer.stop()
        self._dot_timer.stop()
        self.hide()
        self.finished.emit()
        self.deleteLater()

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _ev) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Background gradient
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, QColor(self._BG_TOP))
        grad.setColorAt(1.0, QColor(self._BG_BOT))
        p.fillRect(self.rect(), QBrush(grad))

        # Subtle top accent line
        p.setPen(QPen(QColor(self._ACCENT), 2))
        p.drawLine(0, 0, w, 0)

        # ── Logo / app name ──────────────────────────────────────────────────
        p.setPen(QColor(self._TEXT))
        p.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
        p.drawText(40, 80, "Stock Manager")
        p.setFont(QFont("Segoe UI", 26, QFont.Weight.Light))
        p.setPen(QColor(self._ACCENT))
        p.drawText(40, 115, "Pro")

        # Version tag
        p.setPen(QColor(self._SUBTEXT))
        p.setFont(QFont("Segoe UI", 9))
        p.drawText(40, 140, "v2.0.0  ·  Professional Edition")

        # ── Progress bar ─────────────────────────────────────────────────────
        track_y = 200
        track_h = 4
        track_r = track_h // 2
        track_w = w - 80

        # Track
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self._TRACK))
        p.drawRoundedRect(40, track_y, track_w, track_h, track_r, track_r)

        # Fill
        fill_w = int(track_w * self._progress / 100)
        if fill_w > 0:
            fill_grad = QLinearGradient(40, 0, 40 + fill_w, 0)
            fill_grad.setColorAt(0.0, QColor(self._ACCENT2))
            fill_grad.setColorAt(1.0, QColor(self._ACCENT))
            p.setBrush(QBrush(fill_grad))
            p.drawRoundedRect(40, track_y, fill_w, track_h, track_r, track_r)

        # ── Step label ───────────────────────────────────────────────────────
        dots = "." * self._dots
        label = f"{self._step_label}{dots}" if self._step_label else ""
        p.setPen(QColor(self._SUBTEXT))
        p.setFont(QFont("Segoe UI", 9))
        p.drawText(40, track_y + 22, label)

        # Percent
        p.setPen(QColor(self._ACCENT))
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        pct_text = f"{self._progress}%"
        fm = p.fontMetrics()
        p.drawText(w - 40 - fm.horizontalAdvance(pct_text), track_y + 22, pct_text)

        # ── Bottom tagline ───────────────────────────────────────────────────
        p.setPen(QColor(self._SUBTEXT))
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(40, h - 20, "© 2026 StockPro  ·  Offline-first inventory management")

        p.end()
