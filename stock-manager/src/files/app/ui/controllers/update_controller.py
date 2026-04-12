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
    """Manages background update checks and banner lifecycle."""

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
        self._layout       = content_layout
        self._parent_w     = parent_widget
        self._banner: UpdateBanner | None = None
        self._workers: list[UpdateCheckWorker] = []
        self.pending = None    # UpdateManifest | None — public; callers read this

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
            if worker in self._workers:
                self._workers.remove(worker)

        def _cleanup() -> None:
            if worker in self._workers:
                self._workers.remove(worker)

        worker.update_available.connect(_on_found)
        worker.up_to_date.connect(_cleanup)
        worker.error.connect(lambda _: _cleanup())
        worker.start()

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
