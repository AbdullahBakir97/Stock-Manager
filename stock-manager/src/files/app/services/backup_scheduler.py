"""
app/services/backup_scheduler.py — QTimer-based auto-backup scheduler.

Runs inside the main thread (no QThread needed) by using a 5-minute polling
timer.  Each tick it checks whether enough time has passed since the last
backup; if so it calls BackupService.auto_backup() off the main thread via
a lightweight DataWorker so the UI never blocks.
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import QObject, QTimer

from app.core.config import ShopConfig
from app.services.backup_service import BackupService

log = logging.getLogger(__name__)

_CHECK_INTERVAL_MS = 5 * 60 * 1_000   # check every 5 minutes


class BackupScheduler(QObject):
    """
    Monitors the auto-backup configuration and triggers backups when due.

    Usage::

        scheduler = BackupScheduler(parent=main_window)
        scheduler.start()

    The scheduler respects the ShopConfig settings at each check, so any
    changes made in the admin panel take effect without restarting.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._svc = BackupService()
        self._timer = QTimer(self)
        self._timer.setInterval(_CHECK_INTERVAL_MS)
        self._timer.timeout.connect(self._tick)

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the scheduler.  Safe to call multiple times."""
        if not self._timer.isActive():
            self._timer.start()
            # Do an immediate check so the first backup isn't deferred 5 min.
            self._tick()

    def stop(self) -> None:
        """Stop the scheduler."""
        self._timer.stop()

    def trigger_now(self) -> bool:
        """Force an immediate backup regardless of schedule. Returns True on success."""
        cfg = ShopConfig.get()
        retain = cfg.auto_backup_retain_int
        backup_dir = cfg.auto_backup_dir or None
        try:
            path = self._svc.auto_backup(retain=retain, backup_dir=backup_dir)
            log.info("BackupScheduler: forced backup → %s", path)
            return True
        except Exception as exc:
            log.error("BackupScheduler: forced backup failed: %s", exc)
            return False

    # ── Internal ──────────────────────────────────────────────────────────────

    def _tick(self) -> None:
        """Called every CHECK_INTERVAL_MS to decide whether to run a backup."""
        cfg = ShopConfig.get()
        if not cfg.is_auto_backup_enabled:
            return

        interval = cfg.auto_backup_interval_hours_int
        if not self._svc.should_backup_now(interval_hours=interval):
            return

        retain = cfg.auto_backup_retain_int
        backup_dir = cfg.auto_backup_dir or None
        try:
            path = self._svc.auto_backup(retain=retain, backup_dir=backup_dir)
            log.info("BackupScheduler: auto-backup created → %s", path)
        except Exception as exc:
            log.error("BackupScheduler: auto-backup failed: %s", exc)
