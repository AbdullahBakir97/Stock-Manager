"""
app/ui/components/update_banner.py — Animated in-app update notification banner.

Shows a slim, non-modal bar at the top of the content area when a newer
version is available.  The user can:

  • "Download & Install" — opens a progress dialog, then launches installer
  • "Remind Me Later"    — hides the banner until next app restart
  • "Skip This Version"  — persists the decision so the banner never reappears
                           for this specific version (stored in app_config)

Animation: slides in from the top via QPropertyAnimation on maximumHeight.
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve,
    QTimer, pyqtSignal,
)
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton,
    QProgressDialog, QMessageBox, QApplication,
)
from PyQt6.QtGui import QFont

from app.core.theme import THEME, _rgba
from app.core.i18n import t
from app.core.database import get_connection
from app.services.update_service import UpdateManifest, UpdateService
from app.ui.workers.update_worker import UpdateDownloadWorker

log = logging.getLogger(__name__)

_BANNER_HEIGHT = 56          # fully-expanded height in pixels
_ANIM_MS       = 280         # slide animation duration


# ── Dismiss persistence ────────────────────────────────────────────────────────

def _get_skipped_version() -> str:
    """Return the version string the user previously chose to skip, or ''."""
    try:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM app_config WHERE key='update_skipped_version'"
            ).fetchone()
            return row["value"] if row else ""
    except Exception:
        return ""


def _set_skipped_version(version: str) -> None:
    """Persist the skipped version so the banner is suppressed permanently."""
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO app_config (key, value) VALUES (?, ?)",
                ("update_skipped_version", version),
            )
    except Exception:
        pass


# ── UpdateBanner ───────────────────────────────────────────────────────────────

class UpdateBanner(QFrame):
    """
    A slim, animated notification bar shown when an update is available.

    Usage::

        banner = UpdateBanner(manifest, parent=content_widget)
        content_layout.insertWidget(0, banner)   # insert at top of content
        banner.show_animated()

    Signals:
        dismissed()  — emitted after the banner fully hides itself (either by
                        user action or after the installer is launched).
    """

    dismissed = pyqtSignal()

    def __init__(self, manifest: UpdateManifest, parent=None) -> None:
        super().__init__(parent)
        self._manifest = manifest
        self._svc = UpdateService()
        self._worker: UpdateDownloadWorker | None = None
        self._installer_path: str = ""
        self._build()
        self.setMaximumHeight(0)   # start collapsed; show_animated() expands

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        tk = THEME.tokens
        self.setObjectName("update_banner")
        self.setStyleSheet(
            f"QFrame#update_banner {{"
            f"  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"    stop:0 {tk.green}, stop:1 {_rgba(tk.green, 'B4')});"
            f"  border-bottom: 1px solid {_rgba(tk.green, 'C8')};"
            f"}}"
            f"QLabel {{ background: transparent; color: #FFFFFF; }}"
        )
        self.setFixedHeight(_BANNER_HEIGHT)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 12, 0)
        lay.setSpacing(12)

        # Icon + text
        icon = QLabel("🎉")
        icon.setFont(QFont("Segoe UI Emoji", 16))
        lay.addWidget(icon)

        text_col = QHBoxLayout()
        text_col.setSpacing(6)
        title = QLabel(t("update_available"))
        title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        notes_text = self._manifest.release_notes[:80]
        if len(self._manifest.release_notes) > 80:
            notes_text += "…"
        version_lbl = QLabel(
            f"v{self._manifest.version}"
            + (f" — {notes_text}" if notes_text else "")
        )
        version_lbl.setFont(QFont("Segoe UI", 9))
        version_lbl.setStyleSheet("color: rgba(255,255,255,0.85);")
        text_col.addWidget(title)
        text_col.addWidget(version_lbl)
        lay.addLayout(text_col)
        lay.addStretch()

        # Action buttons
        self._download_btn = QPushButton(t("update_now"))
        self._download_btn.setObjectName("update_banner_primary")
        self._download_btn.setStyleSheet(
            "QPushButton {"
            "  background: rgba(255,255,255,0.22); color: #fff;"
            "  border: 1px solid rgba(255,255,255,0.5); border-radius: 6px;"
            "  padding: 4px 14px; font-weight: 600;"
            "}"
            "QPushButton:hover { background: rgba(255,255,255,0.35); }"
            "QPushButton:pressed { background: rgba(255,255,255,0.15); }"
        )
        self._download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._download_btn.clicked.connect(self._on_download)
        lay.addWidget(self._download_btn)

        later_btn = QPushButton(t("update_later"))
        later_btn.setStyleSheet(
            "QPushButton {"
            "  background: transparent; color: rgba(255,255,255,0.75);"
            "  border: none; padding: 4px 10px;"
            "}"
            "QPushButton:hover { color: #fff; }"
        )
        later_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        later_btn.clicked.connect(self._on_later)
        lay.addWidget(later_btn)

        skip_btn = QPushButton(t("update_dismiss"))
        skip_btn.setStyleSheet(
            "QPushButton {"
            "  background: transparent; color: rgba(255,255,255,0.55);"
            "  border: none; padding: 4px 10px; font-size: 11px;"
            "}"
            "QPushButton:hover { color: rgba(255,255,255,0.85); }"
        )
        skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        skip_btn.clicked.connect(self._on_skip)
        lay.addWidget(skip_btn)

    # ── Animation ──────────────────────────────────────────────────────────────

    def show_animated(self) -> None:
        """Expand the banner with a smooth slide-in animation."""
        self.setVisible(True)
        anim = QPropertyAnimation(self, b"maximumHeight", self)
        anim.setDuration(_ANIM_MS)
        anim.setStartValue(0)
        anim.setEndValue(_BANNER_HEIGHT)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        self._anim = anim   # keep reference alive

    def _hide_animated(self, callback=None) -> None:
        """Collapse the banner with a smooth slide-out animation."""
        anim = QPropertyAnimation(self, b"maximumHeight", self)
        anim.setDuration(_ANIM_MS)
        anim.setStartValue(self.maximumHeight())
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)

        def _done():
            self.setVisible(False)
            self.dismissed.emit()
            if callback:
                callback()

        anim.finished.connect(_done)
        anim.start()
        self._anim = anim

    # ── Button handlers ────────────────────────────────────────────────────────

    def _on_later(self) -> None:
        """Hide for this session but do not persist the decision."""
        self._hide_animated()

    def _on_skip(self) -> None:
        """Persist 'skipped version' so this version is never shown again."""
        _set_skipped_version(self._manifest.version)
        self._hide_animated()

    def _on_download(self) -> None:
        """Start downloading the installer in the background."""
        self._download_btn.setEnabled(False)
        self._download_btn.setText(t("update_downloading"))

        # Progress dialog (non-blocking via QProgressDialog)
        self._progress_dlg = QProgressDialog(
            t("update_downloading"),
            None,    # no cancel button
            0, 100,
            self.window(),
        )
        self._progress_dlg.setWindowTitle(t("update_available"))
        self._progress_dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._progress_dlg.setMinimumDuration(0)
        self._progress_dlg.setValue(0)
        self._progress_dlg.show()

        self._worker = UpdateDownloadWorker(self._manifest, parent=self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_download_done)
        self._worker.error.connect(self._on_download_error)
        self._worker.start()

    def _on_progress(self, done: int, total: int) -> None:
        if total > 0:
            pct = min(99, int(done / total * 100))
            self._progress_dlg.setValue(pct)

    def _on_download_done(self, installer_path: str) -> None:
        self._installer_path = installer_path
        self._progress_dlg.setValue(100)
        self._progress_dlg.close()

        # Ask user to confirm before launching installer + quitting
        reply = QMessageBox.question(
            self.window(),
            t("update_available"),
            t("update_download_done"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._launch_installer()
        else:
            # Restore button so user can try again later
            self._download_btn.setEnabled(True)
            self._download_btn.setText(t("update_now"))

    def _on_download_error(self, msg: str) -> None:
        self._progress_dlg.close()
        self._download_btn.setEnabled(True)
        self._download_btn.setText(t("update_now"))
        QMessageBox.critical(
            self.window(),
            t("update_error"),
            t("update_download_fail", reason=msg),
        )
        log.error("UpdateBanner: download failed: %s", msg)

    def _launch_installer(self) -> None:
        """Launch the installer then quit the app."""
        try:
            self._svc.launch_installer(self._installer_path)
        except Exception as exc:
            QMessageBox.critical(
                self.window(),
                t("update_error"),
                str(exc),
            )
            log.error("UpdateBanner: launch_installer failed: %s", exc)
            return

        # Give the installer a moment to start, then quit
        QTimer.singleShot(800, QApplication.quit)
