"""
app/services/sync_service.py — Turso cloud sync scheduler.

Manages periodic and on-demand bidirectional sync between the local libsql
embedded replica and the Turso remote database. Follows the BackupScheduler
pattern: QObject + QTimer in the main thread, heavy work offloaded via POOL.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

_log = logging.getLogger(__name__)


class SyncService(QObject):
    """Periodic and on-demand sync between local embedded replica and Turso cloud.

    Usage::

        service = SyncService(parent=main_window)
        if ShopConfig.get().is_cloud_sync_enabled:
            service.start()
            QTimer.singleShot(3000, service.sync_now)   # defer initial pull

    The service re-reads ShopConfig on every tick, so credential/interval changes
    made in the admin panel take effect without restarting.
    """

    sync_started   = pyqtSignal()         # emitted before every sync attempt
    sync_completed = pyqtSignal(str)      # ISO timestamp string on success
    sync_failed    = pyqtSignal(str)      # human-readable error on failure

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._timer           = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._last_sync:  Optional[datetime] = None
        self._last_error: Optional[str]      = None
        self._is_syncing: bool               = False
        self._error_log:  list[str]          = []  # last 5 errors, for admin panel

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def is_configured(self) -> bool:
        try:
            from app.core.config import ShopConfig
            return ShopConfig.get().is_cloud_sync_enabled
        except Exception:
            return False

    @property
    def last_sync_time(self) -> Optional[datetime]:
        return self._last_sync

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    @property
    def is_syncing(self) -> bool:
        return self._is_syncing

    @property
    def error_log(self) -> list[str]:
        return list(self._error_log)

    def start(self) -> None:
        """Start periodic sync timer. Safe to call multiple times."""
        try:
            from app.core.config import ShopConfig
            interval_ms = ShopConfig.get().sync_interval_minutes_int * 60 * 1000
        except Exception:
            interval_ms = 5 * 60 * 1000
        self._timer.setInterval(interval_ms)
        if not self._timer.isActive():
            self._timer.start()

    def stop(self) -> None:
        """Stop periodic sync timer."""
        self._timer.stop()

    def reconfigure(self) -> None:
        """Reload sync interval from ShopConfig. Call after admin saves settings."""
        was_active = self._timer.isActive()
        self.stop()
        if was_active:
            self.start()

    def sync_now(self) -> None:
        """Trigger an immediate bidirectional sync (non-blocking, via POOL)."""
        if self._is_syncing or not self.is_configured:
            return
        import time
        from app.ui.workers.worker_pool import POOL
        self._is_syncing = True
        self._sync_t0 = time.monotonic()
        self.sync_started.emit()
        _log.info("Cloud sync started (%s)", self._mode_str())
        POOL.submit(
            "cloud_sync",
            self._do_sync,
            self._on_sync_done,
            self._on_sync_error,
        )

    @staticmethod
    def _mode_str() -> str:
        """Short, secrets-free description of the active connection mode."""
        try:
            from app.core.database import connection_mode
            info = connection_mode()
            return f"{info['mode']} · {info['role']}"
        except Exception:
            return "unknown"

    # ── Internal (runs on POOL worker thread) ─────────────────────────────────

    def _do_sync(self) -> str:
        """Ping Turso to confirm connectivity. Returns ISO timestamp on success.
        With the HTTP API each write already goes directly to the cloud —
        the 'sync' step is just a liveness check."""
        from app.core.database import sync_to_remote
        return sync_to_remote()  # returns ISO timestamp string

    # ── Callbacks (main thread, via POOL signal delivery) ─────────────────────

    def _on_sync_done(self, timestamp: str) -> None:
        import time
        self._is_syncing = False
        self._last_sync  = datetime.fromisoformat(timestamp)
        self._last_error = None
        self.sync_completed.emit(timestamp)
        elapsed_ms = (time.monotonic() - getattr(self, "_sync_t0", time.monotonic())) * 1000
        # INFO (not DEBUG) so successful syncs are visible in production logs.
        _log.info("Cloud sync completed in %.0f ms (%s)", elapsed_ms, self._mode_str())

    def _on_sync_error(self, error_msg: str) -> None:
        self._is_syncing = False
        self._last_error = error_msg
        ts = datetime.now().strftime("%H:%M:%S")
        self._error_log.append(f"[{ts}] {error_msg}")
        self._error_log = self._error_log[-5:]
        self.sync_failed.emit(error_msg)
        _log.error("Cloud sync failed: %s", error_msg)

    def _tick(self) -> None:
        """Called by QTimer every N minutes."""
        if self.is_configured:
            self.sync_now()
