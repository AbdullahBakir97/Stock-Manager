"""
app/services/zoom_service.py — Application-wide zoom authority.

Single source of truth for the zoom percentage. Every UI element that
participates in zoom connects to `ZOOM.pct_changed` and scales itself
through `ZOOM.scale(base, minimum)`.

Design:
    - Integer percentage 50–200 (clamped, snapped to 10%)
    - `scale(base, minimum)` helper returns `max(minimum, round(base * factor))`
    - Debounced save to ShopConfig.zoom_level (500 ms) — slider drags don't
      hit the DB on every tick
    - Presets: 50, 75, 100, 125, 150, 200
    - Ctrl+scroll / Ctrl+Plus / Ctrl+Minus step by 10; Ctrl+0 resets to 100

Usage:
    from app.services.zoom_service import ZOOM

    ZOOM.pct_changed.connect(self.apply_zoom)       # on main thread
    widget.setFixedWidth(ZOOM.scale(240, 160))      # respect minimum
    row_h = ZOOM.scale(48, 14)
"""
from __future__ import annotations

from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class ZoomService(QObject):
    MIN_PCT: int = 50
    MAX_PCT: int = 200
    STEP: int = 10
    PRESETS: tuple[int, ...] = (50, 75, 100, 125, 150, 200)

    # Fired AFTER _pct is updated. Listeners apply the zoom to their widgets.
    pct_changed = pyqtSignal(int)

    def __init__(self) -> None:
        super().__init__()
        self._pct: int = 100
        # Debounce timer for persisting to ShopConfig
        self._save_timer: QTimer | None = None
        self._save_scheduled: bool = False
        # Coalesce rapid successive set_pct calls (e.g. slider drag) so the
        # expensive apply_zoom runs at most once per animation frame (~16 ms).
        self._apply_timer: QTimer | None = None
        self._pending_pct: int | None = None

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def pct(self) -> int:
        return self._pct

    @property
    def factor(self) -> float:
        return self._pct / 100.0

    def scale(self, base: float | int, minimum: int = 1) -> int:
        """Return base * factor, floored at `minimum` and rounded to nearest int."""
        return max(int(minimum), int(round(float(base) * self.factor)))

    def set_pct(self, pct: int, *, persist: bool = True, coalesce: bool = True) -> None:
        """Set zoom percentage (clamped to 50–200, snapped to 10%).

        `pct_changed` is emitted after the value is updated. During rapid
        updates (slider drag, Ctrl+Wheel) multiple calls coalesce into a
        single emission on the next animation frame (~16 ms) so the
        expensive apply_zoom doesn't run 50× per second.

        Pass coalesce=False for one-shot changes where you need an
        immediate synchronous effect (tests, explicit UI reset).
        """
        try:
            v = int(round(pct / self.STEP) * self.STEP)
        except (TypeError, ValueError):
            return
        v = max(self.MIN_PCT, min(self.MAX_PCT, v))
        if v == self._pct:
            return
        self._pct = v
        if coalesce:
            # Schedule emission on the next event loop tick — multiple
            # rapid changes collapse into one apply_zoom call.
            self._pending_pct = v
            if self._apply_timer is None:
                self._apply_timer = QTimer()
                self._apply_timer.setSingleShot(True)
                self._apply_timer.setInterval(16)  # ~60 fps
                self._apply_timer.timeout.connect(self._fire_pending)
            if not self._apply_timer.isActive():
                self._apply_timer.start()
        else:
            self.pct_changed.emit(v)
        if persist:
            self._schedule_save()

    def _fire_pending(self) -> None:
        """Emit pct_changed for the latest pending value."""
        pct = self._pending_pct
        self._pending_pct = None
        if pct is not None:
            self.pct_changed.emit(pct)

    def zoom_in(self) -> None:
        self.set_pct(self._pct + self.STEP)

    def zoom_out(self) -> None:
        self.set_pct(self._pct - self.STEP)

    def reset(self) -> None:
        self.set_pct(100)

    # ── Persistence (debounced) ───────────────────────────────────────────────

    def load_from_config(self) -> None:
        """Read the stored zoom_level from ShopConfig and apply it silently.

        Does NOT trigger a save (persist=False) so that loading doesn't write.
        Emits pct_changed so consumers can apply on startup.
        """
        try:
            from app.core.config import ShopConfig
            pct = ShopConfig.get().zoom_level_int
        except Exception:
            pct = 100
        # Force emission even if value is same (startup needs one paint)
        self._pct = -1   # sentinel so set_pct fires
        self.set_pct(pct, persist=False, coalesce=False)

    def _schedule_save(self) -> None:
        """Debounce DB writes — only save 500ms after the last change."""
        if self._save_timer is None:
            self._save_timer = QTimer()
            self._save_timer.setSingleShot(True)
            self._save_timer.setInterval(500)
            self._save_timer.timeout.connect(self._do_save)
        self._save_timer.start()  # restart countdown

    def _do_save(self) -> None:
        try:
            from app.core.config import ShopConfig
            cfg = ShopConfig.get()
            cfg.zoom_level = str(self._pct)
            cfg.save()
            ShopConfig.invalidate()  # force reload next time
        except Exception:
            pass


# ── Module-level singleton ────────────────────────────────────────────────────

ZOOM = ZoomService()
