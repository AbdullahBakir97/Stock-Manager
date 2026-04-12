"""
app/ui/controllers/update_controller.py — Auto-update banner orchestration.

Owns:
  - Spawning UpdateCheckWorker threads
  - Inserting / removing the UpdateBanner in the content layout
  - Tracking the pending UpdateManifest (drives the notification badge)

Usage (from MainWindow):
    self._upd_ctrl = UpdateController(
        content_layout=self._content_layout,
        parent_widget=self._bg,
        parent=self,
    )
    self._upd_ctrl.badge_changed.connect(self._alert_ctrl.refresh)
    # wire admin "preview" signal:
    dlg.preview_banner_requested.connect(self._upd_ctrl.show_banner)
"""
from __future__ import annotations

from PyQt6.QtCore import QTimer, QObject, pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from app.services.update_service import UpdateService
from app.ui.workers.update_worker import UpdateCheckWorker
from app.ui.components.update_banner import UpdateBanner, _get_skipped_version


class UpdateController(QObject):
    """Manages background update checks, silent pre-download, and banner lifecycle."""

    # Emitted whenever the pending-update state changes (callers refresh badge)
    badge_changed = pyqtSignal()
    # Emitted when the user clicks "Remind Later" in the notification panel
    remind_later_clicked = pyqtSignal()

    def __init__(
        self,
        content_layout: QVBoxLayout,
        parent_widget: QWidget,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._layout          = content_layout
        self._parent_w        = parent_widget
        self._banner: UpdateBanner | None = None
        self._workers: list   = []   # check + download workers
        self._dl_worker       = None # active download worker (at most one)
        self.pending          = None # UpdateManifest | None — public

    # ── Timer wiring (call once from MainWindow.__init__) ────────────────────

    def start_auto_check(self, enabled: bool) -> None:
        """Kick off the recurring 4-hour timer and optional 30-s startup check."""
        self._timer = QTimer(self)
        self._timer.setInterval(4 * 60 * 60 * 1_000)
        self._timer.timeout.connect(self.check)
        self._timer.start()
        if enabled:
            QTimer.singleShot(30_000, self.check)

    # ── Public actions ────────────────────────────────────────────────────────

    def check(self) -> None:
        """Spawn a background worker to silently check for updates."""
        svc = UpdateService()
        if not svc.is_enabled():
            return
        worker = UpdateCheckWorker(svc, parent=self)
        self._workers.append(worker)

        def _on_found(manifest) -> None:
            if _get_skipped_version() == manifest.version:
                return
            if self._banner and self._banner.isVisible():
                return
            self.show_banner(manifest)
            self._start_background_download(manifest)   # ← silent pre-download
            if worker in self._workers:
                self._workers.remove(worker)

        def _cleanup() -> None:
            if worker in self._workers:
                self._workers.remove(worker)

        worker.update_available.connect(_on_found)
        worker.up_to_date.connect(_cleanup)
        worker.error.connect(lambda _: _cleanup())
        worker.start()

    def _start_background_download(self, manifest) -> None:
        """
        Silently download the installer in the background as soon as an update
        is detected.  No progress UI — the download runs quietly so that when
        the user clicks "Install Now" in the banner the file is already cached
        and SHA256-verified; install starts immediately.

        If a download is already in progress or the installer is already cached
        (UpdateService.download() detects this via checksum comparison) the
        worker exits almost instantly with the cached path.
        """
        from app.ui.workers.update_worker import UpdateDownloadWorker

        if self._dl_worker and self._dl_worker.isRunning():
            return  # already downloading

        dl = UpdateDownloadWorker(manifest, parent=self)
        self._dl_worker = dl
        self._workers.append(dl)

        def _on_done(installer_path: str) -> None:
            # Tell the banner the file is ready — button becomes "Install Now"
            if self._banner is not None:
                try:
                    self._banner.set_installer_ready(installer_path)
                except RuntimeError:
                    pass   # banner was deleted
            if dl in self._workers:
                self._workers.remove(dl)

        def _on_error(msg: str) -> None:
            # Silent failure — user can still trigger manual download via banner
            import logging
            logging.getLogger(__name__).debug(
                "Background download failed (will retry on click): %s", msg
            )
            if dl in self._workers:
                self._workers.remove(dl)

        dl.finished.connect(_on_done)
        dl.error.connect(_on_error)
        dl.start()

    def show_banner(self, manifest) -> None:
        """
        Store the manifest, emit badge_changed, and insert animated banner
        at position 0 of the content layout (above the stack).
        """
        self.pending = manifest
        self.badge_changed.emit()

        # Remove any old banner
        if self._banner is not None:
            try:
                self._layout.removeWidget(self._banner)
                self._banner.setVisible(False)
                self._banner.deleteLater()
            except RuntimeError:
                pass

        self._banner = UpdateBanner(manifest, parent=self._parent_w)
        self._layout.insertWidget(0, self._banner)

        def _dismissed() -> None:
            try:
                self._layout.removeWidget(self._banner)
            except Exception:
                pass
            # Badge stays — user can still install from the notification panel

        self._banner.dismissed.connect(_dismissed)
        self._banner.show_animated()

    def remind_later(self) -> None:
        """Called when the user clicks 'Remind Later' in the notification panel."""
        self.pending = None
        self.badge_changed.emit()
        self.remind_later_clicked.emit()
