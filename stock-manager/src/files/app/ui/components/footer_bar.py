"""
app/ui/components/footer_bar.py — 32px status footer bar.

Shows: status message, active-filter indicator, last-action timestamp,
app version, and DB connection status dot.
"""
from __future__ import annotations

from datetime import datetime

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QSizePolicy, QWidget,
    QPushButton, QSlider,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from app.core.i18n import t
from app.core.version import APP_VERSION


class FooterBar(QFrame):
    """32px footer: status | filter indicator · · · zoom controls  timestamp  v{ver}  ● connected."""

    zoom_changed = pyqtSignal(int)  # emits zoom percentage (50-200)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("footer_bar")
        self.setFixedHeight(32)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._zoom_pct = 100
        self._build()

    # ── Build ────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(6)
        lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._status = QLabel(t("statusbar_ready"))
        self._status.setObjectName("footer_status")
        lay.addWidget(self._status)

        self._filter_lbl = QLabel()
        self._filter_lbl.setObjectName("footer_filter_indicator")
        self._filter_lbl.hide()
        lay.addWidget(self._filter_lbl)

        lay.addStretch()

        # ── Zoom controls ────────────────────────────────────────
        self._zoom_out_btn = QLabel("−")
        self._zoom_out_btn.setObjectName("footer_zoom_btn")
        self._zoom_out_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zoom_out_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._zoom_out_btn.setToolTip("Zoom out (Ctrl+−)")
        self._zoom_out_btn.mousePressEvent = lambda _: self.set_zoom(self._zoom_pct - 10)
        lay.addWidget(self._zoom_out_btn)

        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setObjectName("footer_zoom_slider")
        self._zoom_slider.setRange(50, 200)
        self._zoom_slider.setValue(100)
        self._zoom_slider.setSingleStep(10)
        self._zoom_slider.setPageStep(25)
        self._zoom_slider.setFixedWidth(70)
        self._zoom_slider.setFixedHeight(11)
        self._zoom_slider.valueChanged.connect(self._on_slider)
        lay.addWidget(self._zoom_slider)

        self._zoom_in_btn = QLabel("+")
        self._zoom_in_btn.setObjectName("footer_zoom_btn")
        self._zoom_in_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zoom_in_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._zoom_in_btn.setToolTip("Zoom in (Ctrl++)")
        self._zoom_in_btn.mousePressEvent = lambda _: self.set_zoom(self._zoom_pct + 10)
        lay.addWidget(self._zoom_in_btn)

        self._zoom_lbl = QLabel("100%")
        self._zoom_lbl.setObjectName("footer_zoom_pct")
        self._zoom_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zoom_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        self._zoom_lbl.setToolTip("Click to reset zoom (Ctrl+0)")
        self._zoom_lbl.mousePressEvent = lambda _: self.set_zoom(100)
        lay.addWidget(self._zoom_lbl)

        self._zoom_widgets = [self._zoom_out_btn, self._zoom_slider,
                              self._zoom_in_btn, self._zoom_lbl]

        lay.addSpacing(12)

        # ── Info widgets ─────────────────────────────────────────
        self._timestamp = QLabel()
        self._timestamp.setObjectName("footer_timestamp")
        lay.addWidget(self._timestamp)

        self._version = QLabel(f"v{APP_VERSION}")
        self._version.setObjectName("footer_version")
        lay.addWidget(self._version)

        self._sync = QLabel(f"●  {t('footer_connected')}")
        self._sync.setObjectName("footer_sync")
        lay.addWidget(self._sync)

        # Live clock — update every second
        self._timestamp.setText(datetime.now().strftime("%H:%M:%S"))
        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start()

    def _tick_clock(self) -> None:
        self._timestamp.setText(datetime.now().strftime("%H:%M:%S"))

    # ── Public API ───────────────────────────────────────────────────────────

    def show_status(self, msg: str, timeout: int = 0, level: str = "") -> None:
        """Display a status message, optionally reverting after *timeout* ms."""
        icon = {"ok": "✓ ", "warn": "⚠ ", "err": "✕ "}.get(level, "")
        self._status.setText(f"{icon}{msg}")
        obj = {
            "ok":   "footer_status_ok",
            "warn": "footer_status_warn",
            "err":  "footer_status_err",
        }.get(level, "footer_status")
        self._status.setObjectName(obj)
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)
        if timeout > 0:
            QTimer.singleShot(timeout, lambda: self.show_status(t("statusbar_ready")))
        self._timestamp.setText(datetime.now().strftime("%H:%M:%S"))

    def show_filter(self, text: str) -> None:
        """Show the filter indicator with *text* (e.g. '12 / 200')."""
        self._filter_lbl.setText(text)
        self._filter_lbl.show()

    def hide_filter(self) -> None:
        """Hide the filter indicator."""
        self._filter_lbl.hide()

    # ── Zoom ────────────────────────────────────────────────────────────────

    def set_zoom(self, pct: int) -> None:
        """Set zoom percentage, clamped to 50-200."""
        pct = max(50, min(200, round(pct / 10) * 10))
        if pct == self._zoom_pct:
            return
        self._zoom_pct = pct
        self._zoom_slider.blockSignals(True)
        self._zoom_slider.setValue(pct)
        self._zoom_slider.blockSignals(False)
        self._zoom_lbl.setText(f"{pct}%")
        self.zoom_changed.emit(pct)

    def _on_slider(self, val: int) -> None:
        # Snap to nearest 10
        snapped = round(val / 10) * 10
        self.set_zoom(snapped)

    @property
    def zoom_pct(self) -> int:
        return self._zoom_pct

    def set_zoom_visible(self, visible: bool) -> None:
        """Show or hide zoom controls."""
        for w in self._zoom_widgets:
            w.setVisible(visible)
        # Also hide/show the spacing after zoom
        # (spacing is handled naturally by Qt when widgets hide)

    def retranslate(self) -> None:
        self._sync.setText(f"●  {t('footer_connected')}")
