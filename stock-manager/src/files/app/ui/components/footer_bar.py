"""
app/ui/components/footer_bar.py — Status footer with professional zoom group.

Layout (right-aligned group):
    [−] [────●────tick tick tick────] [+]  │  100% ▾  │  ↺

Components:
    • Zoom-out QToolButton with tooltip and Ctrl+− shortcut hint
    • QSlider with visible tick marks at each preset (50 / 75 / 100 / 125 / 150 / 200)
    • Zoom-in QToolButton with tooltip and Ctrl++ shortcut hint
    • Preset dropdown — "100% ▾" opens a QMenu of preset percentages + Reset
    • Reset button (↺) — single-click to return to 100%

The footer is a view only — the authoritative zoom state lives in ZoomService.
Every interaction calls ZOOM.set_pct() / ZOOM.zoom_in() / ZOOM.zoom_out() / ZOOM.reset().
The footer listens on ZOOM.pct_changed to stay in sync with all other views.
"""
from __future__ import annotations

from datetime import datetime

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QSizePolicy, QWidget,
    QSlider, QToolButton, QMenu,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence

from app.core.i18n import t
from app.core.version import APP_VERSION
from app.services.zoom_service import ZOOM


class FooterBar(QFrame):
    """Status footer — 32 px high. Includes a professional zoom widget group
    that mirrors ``ZoomService`` state."""

    # Kept for backwards compatibility. Still emitted, but ZOOM is authoritative.
    zoom_changed = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("footer_bar")
        self.setFixedHeight(32)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._build()

        # Sync footer UI when ZoomService changes (startup load, Ctrl+Scroll, presets)
        ZOOM.pct_changed.connect(self._on_zoom_external, Qt.ConnectionType.QueuedConnection)
        # Apply the current ZoomService value to the widgets (in case set before ctor)
        self._sync_ui(ZOOM.pct)

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

        # ── Zoom control group — all sizes locked to prevent layout shifts ──
        self._zoom_group = QWidget()
        self._zoom_group.setObjectName("footer_zoom_group")
        self._zoom_group.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        # Fixed overall size — button (22) + slider (110) + button (22) + divider
        # + preset (60) + reset (22) + gaps/padding = 260 px × 24 px
        self._zoom_group.setFixedHeight(24)
        zlay = QHBoxLayout(self._zoom_group)
        zlay.setContentsMargins(4, 0, 4, 0)
        zlay.setSpacing(3)

        def _make_iconbtn(text: str, tip: str, slot) -> QToolButton:
            b = QToolButton()
            b.setObjectName("footer_zoom_btn")
            b.setText(text)
            b.setAutoRaise(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            b.setFixedSize(22, 22)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            return b

        # Zoom-out button
        self._zoom_out_btn = _make_iconbtn("−", "Zoom out  (Ctrl+−)", ZOOM.zoom_out)
        zlay.addWidget(self._zoom_out_btn)

        # Slider — locked width + height, fixed size policy
        # During drag: valueChanged only updates the preset label (cheap preview)
        # On release: apply the final zoom (expensive apply_zoom runs once)
        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setObjectName("footer_zoom_slider")
        self._zoom_slider.setRange(ZOOM.MIN_PCT, ZOOM.MAX_PCT)
        self._zoom_slider.setValue(ZOOM.pct)
        self._zoom_slider.setSingleStep(ZOOM.STEP)
        self._zoom_slider.setPageStep(25)
        self._zoom_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._zoom_slider.setTickInterval(25)
        self._zoom_slider.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._zoom_slider.setFixedSize(110, 18)
        self._zoom_slider.setToolTip("Drag to zoom  (Ctrl+Scroll)")
        self._zoom_slider.setTracking(True)
        self._is_dragging = False
        self._zoom_slider.sliderPressed.connect(self._on_slider_pressed)
        self._zoom_slider.sliderReleased.connect(self._on_slider_released)
        self._zoom_slider.valueChanged.connect(self._on_slider_value)
        zlay.addWidget(self._zoom_slider)

        # Zoom-in button
        self._zoom_in_btn = _make_iconbtn("+", "Zoom in  (Ctrl++)", ZOOM.zoom_in)
        zlay.addWidget(self._zoom_in_btn)

        # Divider
        div1 = QFrame()
        div1.setObjectName("footer_zoom_divider")
        div1.setFrameShape(QFrame.Shape.VLine)
        div1.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        div1.setFixedSize(1, 16)
        zlay.addWidget(div1)

        # Preset dropdown — FIXED width so "50% ▾" and "125% ▾" both fit without shifting
        self._zoom_preset_btn = QToolButton()
        self._zoom_preset_btn.setObjectName("footer_zoom_preset")
        self._zoom_preset_btn.setText("100%")
        self._zoom_preset_btn.setAutoRaise(True)
        self._zoom_preset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._zoom_preset_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._zoom_preset_btn.setFixedSize(56, 22)  # locked — text never pushes layout
        self._zoom_preset_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._zoom_preset_btn.setArrowType(Qt.ArrowType.NoArrow)
        self._zoom_preset_btn.setToolTip("Zoom presets")
        self._build_preset_menu()
        zlay.addWidget(self._zoom_preset_btn)

        # Reset button
        self._zoom_reset_btn = _make_iconbtn("↺", "Reset zoom to 100%  (Ctrl+0)", ZOOM.reset)
        zlay.addWidget(self._zoom_reset_btn)

        # Lock overall width so the group NEVER stretches regardless of slider state
        self._zoom_group.setFixedWidth(
            22 + 3 + 110 + 3 + 22 + 3 + 1 + 3 + 56 + 3 + 22 + 8  # children + spacings + margins
        )

        lay.addWidget(self._zoom_group)

        # Track all zoom widgets for show/hide
        self._zoom_widgets = [self._zoom_group]

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

    def _build_preset_menu(self) -> None:
        """Populate the preset dropdown menu from ZoomService.PRESETS."""
        menu = QMenu(self._zoom_preset_btn)
        menu.setObjectName("footer_zoom_menu")
        for p in ZOOM.PRESETS:
            act = QAction(f"{p}%", menu)
            if p == 100:
                act.setShortcut(QKeySequence("Ctrl+0"))
            act.triggered.connect(lambda _=False, v=p: ZOOM.set_pct(v))
            menu.addAction(act)
        menu.addSeparator()
        fit_act = QAction("Fit to Width", menu)
        fit_act.triggered.connect(lambda: ZOOM.set_pct(100))  # treated as 100% preset
        menu.addAction(fit_act)
        reset_act = QAction("Reset  (Ctrl+0)", menu)
        reset_act.triggered.connect(ZOOM.reset)
        menu.addAction(reset_act)
        self._zoom_preset_btn.setMenu(menu)

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

    def _on_slider_pressed(self) -> None:
        """User started dragging."""
        self._is_dragging = True

    def _on_slider_released(self) -> None:
        """User released the slider — commit final value synchronously."""
        self._is_dragging = False
        snapped = round(self._zoom_slider.value() / ZOOM.STEP) * ZOOM.STEP
        ZOOM.set_pct(snapped, coalesce=False)

    def _on_slider_value(self, val: int) -> None:
        """Live zoom: every slider tick applies the zoom via ZoomService.
        The service's 16 ms coalescer collapses rapid ticks into at most one
        apply_zoom per animation frame, so drag stays smooth."""
        snapped = round(val / ZOOM.STEP) * ZOOM.STEP
        ZOOM.set_pct(snapped)

    def _on_zoom_external(self, pct: int) -> None:
        """ZoomService changed — sync the slider + label + legacy signal."""
        self._sync_ui(pct)
        self.zoom_changed.emit(pct)

    def _sync_ui(self, pct: int) -> None:
        self._zoom_slider.blockSignals(True)
        self._zoom_slider.setValue(pct)
        self._zoom_slider.blockSignals(False)
        self._zoom_preset_btn.setText(f"{pct}%")

    # Kept for backwards compatibility with any caller still using this API
    def set_zoom(self, pct: int) -> None:
        ZOOM.set_pct(pct)

    @property
    def zoom_pct(self) -> int:
        return ZOOM.pct

    def set_zoom_visible(self, visible: bool) -> None:
        """Show or hide the entire zoom group."""
        for w in self._zoom_widgets:
            w.setVisible(visible)

    def retranslate(self) -> None:
        self._sync.setText(f"●  {t('footer_connected')}")
        # Preset menu uses English labels (numbers + Fit/Reset) — no retranslate needed

    # ── UI Scale (one-shot at startup) ────────────────────────────────────
    def apply_ui_scale(self, factor: float) -> None:
        """Scale footer height once at startup. The zoom widget itself
        keeps its fixed size — it's a control, not content."""
        h = max(28, int(round(32 * factor)))
        self.setFixedHeight(h)
