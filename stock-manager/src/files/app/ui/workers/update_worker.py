"""
app/ui/workers/update_worker.py — Background workers for update checking and downloading.

Two workers:
  UpdateCheckWorker  — lightweight; fetches manifest only.  Runs on startup.
  UpdateDownloadWorker — heavier; downloads the installer with progress signals.
"""
from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from app.services.update_service import UpdateManifest, UpdateService, record_last_checked


# ── Check worker ───────────────────────────────────────────────────────────────

class UpdateCheckWorker(QThread):
    """
    Checks for an available update in the background.

    Signals:
        update_available(manifest)  — emitted when a newer version is found.
        up_to_date()                — emitted when already on the latest version.
        error(message)              — emitted on network/parse failure.
    """

    update_available: pyqtSignal = pyqtSignal(object)   # UpdateManifest
    up_to_date:       pyqtSignal = pyqtSignal()
    error:            pyqtSignal = pyqtSignal(str)

    def __init__(self, service: UpdateService | None = None, parent=None) -> None:
        super().__init__(parent)
        self._svc = service or UpdateService()

    def run(self) -> None:
        try:
            manifest = self._svc.check_for_update()
        except Exception as exc:
            self.error.emit(str(exc))
            return
        record_last_checked()   # persist timestamp regardless of outcome
        if manifest is not None:
            self.update_available.emit(manifest)
        else:
            self.up_to_date.emit()


# ── Download worker ────────────────────────────────────────────────────────────

class UpdateDownloadWorker(QThread):
    """
    Downloads the update installer in the background with progress signals.

    Signals:
        progress(bytes_done, total_bytes)  — emitted every chunk (~64 KiB).
        finished(installer_path)           — emitted when download + verify succeed.
        error(message)                     — emitted on failure.
    """

    progress: pyqtSignal  = pyqtSignal(int, int)   # (downloaded, total)
    finished: pyqtSignal  = pyqtSignal(str)         # installer_path
    error:    pyqtSignal  = pyqtSignal(str)

    def __init__(
        self,
        manifest: UpdateManifest,
        service: UpdateService | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._manifest = manifest
        self._svc = service or UpdateService()

    def run(self) -> None:
        try:
            path = self._svc.download(
                self._manifest,
                progress_cb=lambda done, total: self.progress.emit(done, total),
            )
            self.finished.emit(path)
        except Exception as exc:
            self.error.emit(str(exc))
