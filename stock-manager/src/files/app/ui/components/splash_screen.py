"""
app/ui/components/splash_screen.py — Professional animated startup splash.

Shows a branded, frameless loading screen with a progress bar,
custom geometric icon, SMP monogram, and step labels while the
app initialises in the background.
"""
from __future__ import annotations

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QLinearGradient, QBrush, QFont, QPen,
    QPainterPath, QRadialGradient,
)

from app.core.version import APP_VERSION


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
    _BG_BOT    = "#0F1419"
    _ACCENT    = "#10B981"   # emerald
    _ACCENT2   = "#059669"   # darker emerald
    _ACCENT3   = "#34D399"   # lighter emerald
    _TEXT      = "#F9FAFB"
    _SUBTEXT   = "#9CA3AF"
    _DIM       = "#4B5563"
    _TRACK     = "#1F2937"
    _BORDER    = "#1E2D3D"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(520, 320)
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
        QTimer.singleShot(400, self._close_splash)

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
        margin = 1

        # ── Rounded card with border ─────────────────────────────────────
        card = QRectF(margin, margin, w - 2 * margin, h - 2 * margin)
        radius = 12.0

        # Background gradient
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0.0, QColor(self._BG_TOP))
        grad.setColorAt(1.0, QColor(self._BG_BOT))

        path = QPainterPath()
        path.addRoundedRect(card, radius, radius)
        p.setClipPath(path)
        p.fillRect(self.rect(), QBrush(grad))

        # Subtle glow in top-left corner
        glow = QRadialGradient(80, 60, 160)
        glow.setColorAt(0.0, QColor(16, 185, 129, 15))  # emerald glow
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), QBrush(glow))

        # Top accent line
        p.setPen(QPen(QColor(self._ACCENT), 2))
        p.drawLine(int(radius) + margin, margin, w - int(radius) - margin, margin)

        # ── Geometric icon: inventory cube ───────────────────────────────
        self._draw_icon(p, 40, 35)

        # ── App name ─────────────────────────────────────────────────────
        p.setPen(QColor(self._TEXT))
        p.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        p.drawText(110, 72, "Stock Manager")

        p.setFont(QFont("Segoe UI", 28, QFont.Weight.Light))
        p.setPen(QColor(self._ACCENT))
        p.drawText(110, 108, "Pro")

        # ── Version badge ────────────────────────────────────────────────
        ver_text = f"v{APP_VERSION}"
        p.setFont(QFont("JetBrains Mono", 8, QFont.Weight.DemiBold))
        fm = p.fontMetrics()
        ver_w = fm.horizontalAdvance(ver_text) + 16
        ver_x = 115
        ver_y = 118

        # Badge background
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(16, 185, 129, 30))
        p.drawRoundedRect(QRectF(ver_x, ver_y, ver_w, 20), 4, 4)

        # Badge border
        p.setPen(QPen(QColor(self._ACCENT), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(ver_x, ver_y, ver_w, 20), 4, 4)

        # Badge text
        p.setPen(QColor(self._ACCENT3))
        p.drawText(int(ver_x + 8), int(ver_y + 15), ver_text)

        # "Professional Edition" label
        p.setPen(QColor(self._DIM))
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(ver_x + ver_w + 8, int(ver_y + 14), "Professional Edition")

        # ── Progress bar ─────────────────────────────────────────────────
        track_y = 220
        track_h = 3
        track_r = 1
        track_w = w - 80

        # Track
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self._TRACK))
        p.drawRoundedRect(QRectF(40, track_y, track_w, track_h), track_r, track_r)

        # Fill
        fill_w = int(track_w * self._progress / 100)
        if fill_w > 0:
            fill_grad = QLinearGradient(40, 0, 40 + fill_w, 0)
            fill_grad.setColorAt(0.0, QColor(self._ACCENT2))
            fill_grad.setColorAt(1.0, QColor(self._ACCENT))
            p.setBrush(QBrush(fill_grad))
            p.drawRoundedRect(QRectF(40, track_y, fill_w, track_h), track_r, track_r)

        # ── Step label ───────────────────────────────────────────────────
        dots = "." * self._dots
        label = f"{self._step_label}{dots}" if self._step_label else ""
        p.setPen(QColor(self._SUBTEXT))
        p.setFont(QFont("Segoe UI", 9))
        p.drawText(40, track_y + 24, label)

        # Percent
        p.setPen(QColor(self._ACCENT))
        p.setFont(QFont("JetBrains Mono", 9, QFont.Weight.DemiBold))
        pct_text = f"{self._progress}%"
        fm = p.fontMetrics()
        p.drawText(w - 40 - fm.horizontalAdvance(pct_text), track_y + 24, pct_text)

        # ── Bottom tagline ───────────────────────────────────────────────
        p.setPen(QColor(self._DIM))
        p.setFont(QFont("Segoe UI", 7))
        p.drawText(40, h - 22, f"\u00a9 2026 StockPro  \u00b7  Offline-first inventory management")

        # ── Card border (drawn last, on top) ─────────────────────────────
        p.setClipping(False)
        p.setPen(QPen(QColor(self._BORDER), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(card, radius, radius)

        p.end()

    # ── Custom icon: geometric inventory cube + SMP monogram ─────────────

    def _draw_icon(self, p: QPainter, x: int, y: int) -> None:
        """Draw a 56×56 geometric inventory cube with an upward arrow
        and 'SMP' monogram overlay."""
        s = 56  # icon size

        p.save()
        p.translate(x, y)

        # ── Cube body (isometric-style box) ──────────────────────────────
        # Front face
        front = QPainterPath()
        front.moveTo(8, 20)
        front.lineTo(28, 10)
        front.lineTo(28, 42)
        front.lineTo(8, 52)
        front.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(16, 185, 129, 60))
        p.drawPath(front)

        # Right face
        right = QPainterPath()
        right.moveTo(28, 10)
        right.lineTo(48, 20)
        right.lineTo(48, 52)
        right.lineTo(28, 42)
        right.closeSubpath()
        p.setBrush(QColor(16, 185, 129, 35))
        p.drawPath(right)

        # Top face
        top = QPainterPath()
        top.moveTo(8, 20)
        top.lineTo(28, 10)
        top.lineTo(48, 20)
        top.lineTo(28, 30)
        top.closeSubpath()
        p.setBrush(QColor(16, 185, 129, 90))
        p.drawPath(top)

        # Cube edges
        p.setPen(QPen(QColor(self._ACCENT), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        # Front edges
        p.drawLine(QPointF(8, 20), QPointF(28, 10))
        p.drawLine(QPointF(8, 20), QPointF(8, 52))
        p.drawLine(QPointF(8, 52), QPointF(28, 42))
        p.drawLine(QPointF(28, 10), QPointF(28, 42))
        # Right edges
        p.drawLine(QPointF(28, 10), QPointF(48, 20))
        p.drawLine(QPointF(48, 20), QPointF(48, 52))
        p.drawLine(QPointF(48, 52), QPointF(28, 42))
        # Top center line
        p.drawLine(QPointF(8, 20), QPointF(28, 30))
        p.drawLine(QPointF(28, 30), QPointF(48, 20))

        # ── Arrow (upward, inside the cube top) ──────────────────────────
        p.setPen(QPen(QColor(self._ACCENT3), 2))
        # Arrow shaft
        p.drawLine(QPointF(28, 28), QPointF(28, 16))
        # Arrow head
        p.drawLine(QPointF(28, 16), QPointF(24, 20))
        p.drawLine(QPointF(28, 16), QPointF(32, 20))

        p.restore()
