"""
app/ui/dialogs/admin/about_panel.py — About & Updates admin panel.

Four professional cards:
  1. App Identity     — name, version badge, license, copyright
  2. System Info      — OS, Python, DB (size + schema), data dir; copy/open actions
  3. Software Updates — auto-check toggle, last-checked timestamp, check now,
                        preview banner, inline status
  4. Support          — docs, changelog, bug report, feedback links
"""
from __future__ import annotations

import logging
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QFont
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QFrame, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from app.core.config import ShopConfig
from app.core.database import DB_PATH
from app.core.i18n import t
from app.core.theme import THEME, _rgba
from app.core.version import APP_VERSION, UPDATE_MANIFEST_URL
from app.services.update_service import (
    UpdateManifest, get_last_checked, record_last_checked,
)
from app.ui.workers.update_worker import UpdateCheckWorker

log = logging.getLogger(__name__)

# ── URLs (replace with real links before shipping) ─────────────────────────────
_URL_DOCS      = "https://stockmanagerpro.io/docs"
_URL_CHANGELOG = "https://stockmanagerpro.io/changelog"
_URL_BUG       = "https://stockmanagerpro.io/report-bug"
_URL_FEEDBACK  = "https://stockmanagerpro.io/feedback"

# ── Demo manifest (used when no real update was found during this session) ─────
_DEMO_MANIFEST = UpdateManifest(
    version="99.0.0",
    download_url="https://example.com/StockManagerPro-99.0.0-setup.exe",
    release_notes=(
        "Major new features: enhanced reporting, improved matrix view, "
        "faster startup, and a redesigned dashboard."
    ),
    release_date="2026-04-06",
    checksum_sha256="",
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _fmt_bytes(n: int) -> str:
    """Human-readable file size: '1.4 MB', '718 KB', '23 KB'."""
    for unit in ("bytes", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n} {unit}"
        n //= 1024
    return f"{n} TB"


def _fmt_last_checked(raw: str | None) -> str:
    """Convert a stored UTC ISO string to a friendly local-time string."""
    if not raw:
        return t("about_never_checked")
    try:
        dt_utc = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        dt_local = dt_utc.astimezone()          # convert to local tz
        now = datetime.now(dt_local.tzinfo)
        delta = now - dt_local
        if delta.days == 0:
            return dt_local.strftime(t("about_today_at") if t("about_today_at") != "about_today_at"
                                     else "Today at %H:%M")
        if delta.days == 1:
            return dt_local.strftime("Yesterday at %H:%M")
        return dt_local.strftime("%b %d at %H:%M")
    except Exception:
        return raw


def _schema_version() -> str:
    """Read schema_version from app_config, return '?' on error."""
    try:
        from app.core.database import get_connection
        with get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM app_config WHERE key='schema_version'"
            ).fetchone()
            return row["value"] if row else "?"
    except Exception:
        return "?"


def _db_size_str() -> str:
    """Return human-readable DB file size, or '—' if file missing."""
    try:
        return _fmt_bytes(os.path.getsize(DB_PATH))
    except OSError:
        return "—"


def _os_info() -> str:
    """Friendly OS string, e.g. 'Windows 11 (64-bit)'."""
    s = platform.system()
    if s == "Windows":
        try:
            ver = platform.version()           # e.g. '10.0.22621'
            build = ver.split(".")[-1]
            win_ver = platform.win32_ver()[0]  # e.g. '10' or '11'
            bits = "64-bit" if platform.machine().endswith("64") else "32-bit"
            return f"Windows {win_ver}  (build {build}, {bits})"
        except Exception:
            pass
    return f"{s} {platform.version()}"


def _python_info() -> str:
    """'3.14.2 (64-bit)'."""
    bits = "64-bit" if sys.maxsize > 2**32 else "32-bit"
    return f"{sys.version.split()[0]}  ({bits})"


def _build_sysinfo_text() -> str:
    """Plain-text system info block for copying to clipboard."""
    return (
        f"Stock Manager Pro  v{APP_VERSION}\n"
        f"{'─' * 40}\n"
        f"OS:          {_os_info()}\n"
        f"Python:      {_python_info()}\n"
        f"DB Path:     {DB_PATH}\n"
        f"DB Size:     {_db_size_str()}\n"
        f"Schema:      v{_schema_version()}\n"
        f"Data Dir:    {os.path.dirname(DB_PATH)}\n"
        f"Manifest:    {UPDATE_MANIFEST_URL or 'Not configured'}\n"
        f"Last check:  {_fmt_last_checked(get_last_checked())}\n"
    )


# ── AboutPanel ─────────────────────────────────────────────────────────────────

class AboutPanel(QWidget):
    """
    Comprehensive About & Updates admin panel.

    Signals:
        preview_banner_requested(manifest) — AdminDialog listens, closes itself,
            then passes the manifest to MainWindow._show_update_banner().
    """

    preview_banner_requested = pyqtSignal(object)   # UpdateManifest

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._worker: UpdateCheckWorker | None = None
        self._found_manifest: UpdateManifest | None = None
        self._build()

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        scroll_lay = QVBoxLayout(self)
        scroll_lay.setContentsMargins(0, 0, 0, 0)
        scroll_lay.setSpacing(0)

        from PyQt6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setObjectName("analytics_scroll")

        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(16)

        lay.addWidget(self._build_identity_card())
        lay.addWidget(self._build_sysinfo_card())
        lay.addWidget(self._build_updates_card())
        lay.addWidget(self._build_support_card())
        lay.addStretch()

        scroll.setWidget(inner)
        scroll_lay.addWidget(scroll)

    # ── Card builders ──────────────────────────────────────────────────────────

    def _build_identity_card(self) -> QFrame:
        tk = THEME.tokens
        card = self._card()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(28, 24, 28, 20)
        lay.setSpacing(0)

        # ── Header row: app name + version badge ──────────────────────────────
        hdr = QHBoxLayout()
        hdr.setSpacing(12)

        name_lbl = QLabel("Stock Manager Pro")
        name_lbl.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        hdr.addWidget(name_lbl)

        badge = QLabel(t("about_badge_stable"))
        badge.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        badge.setStyleSheet(
            f"background: {_rgba(tk.green, '30')}; color: {tk.green};"
            f"border: 1px solid {_rgba(tk.green, '60')}; border-radius: 10px;"
            f"padding: 2px 10px;"
        )
        badge.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        hdr.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)
        hdr.addStretch()
        lay.addLayout(hdr)

        # Tagline
        tag = QLabel(t("about_tagline"))
        tag.setStyleSheet(f"color: {tk.t3}; font-size: 12px; margin-bottom: 14px;")
        lay.addWidget(tag)

        # Divider
        lay.addWidget(self._divider())

        # Info rows
        ver_str = f"v{APP_VERSION}"
        self._add_info_row(lay, t("about_version"), ver_str, value_color=tk.green, value_bold=True)
        self._add_info_row(lay, t("about_license"), t("about_license_value"))
        self._add_info_row(lay, t("about_copyright"), "© 2024–2026 StockPro")

        return card

    def _build_sysinfo_card(self) -> QFrame:
        tk = THEME.tokens
        card = self._card()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(28, 20, 28, 20)
        lay.setSpacing(0)

        self._section_title(lay, t("about_sysinfo_title"), "🖥️")
        lay.addWidget(self._divider())

        self._add_info_row(lay, t("about_sysinfo_os"),     _os_info())
        self._add_info_row(lay, t("about_sysinfo_python"), _python_info())

        # DB row: filename + size + schema
        db_name = os.path.basename(DB_PATH)
        db_detail = f"{db_name}  ·  {_db_size_str()}  ·  {t('about_sysinfo_schema', v=_schema_version())}"
        self._add_info_row(lay, t("about_sysinfo_db"), db_detail)

        data_dir = os.path.dirname(DB_PATH)
        data_lbl = QLabel(data_dir)
        data_lbl.setStyleSheet(f"color: {tk.t3}; font-size: 11px;")
        data_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        data_lbl.setWordWrap(True)
        lay.addSpacing(4)
        dir_key = QLabel(t("about_sysinfo_datadir"))
        dir_key.setObjectName("form_label")
        dir_key.setFixedWidth(150)
        dir_row = QHBoxLayout()
        dir_row.setSpacing(8)
        dir_row.addWidget(dir_key)
        dir_row.addWidget(data_lbl, 1)
        lay.addLayout(dir_row)

        lay.addSpacing(14)
        lay.addWidget(self._divider())
        lay.addSpacing(12)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._copy_btn = QPushButton(f"  📋  {t('about_copy_sysinfo')}")
        self._copy_btn.setObjectName("secondary_btn")
        self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_btn.clicked.connect(self._do_copy_sysinfo)
        btn_row.addWidget(self._copy_btn)

        open_btn = QPushButton(f"  📂  {t('about_open_datafolder')}")
        open_btn.setObjectName("secondary_btn")
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.clicked.connect(self._do_open_datafolder)
        btn_row.addWidget(open_btn)

        btn_row.addStretch()
        lay.addLayout(btn_row)

        return card

    def _build_updates_card(self) -> QFrame:
        tk = THEME.tokens
        card = self._card()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(28, 20, 28, 20)
        lay.setSpacing(0)

        self._section_title(lay, t("about_updates_title"), "🔄")
        lay.addWidget(self._divider())
        lay.addSpacing(8)

        # Auto-check checkbox
        self._auto_check_cb = QCheckBox(t("about_auto_check"))
        self._auto_check_cb.setChecked(ShopConfig.get().is_update_auto_check_enabled)
        self._auto_check_cb.toggled.connect(self._save_auto_check)
        lay.addWidget(self._auto_check_cb)

        lay.addSpacing(10)

        # Last-checked row
        last_row = QHBoxLayout()
        last_row.setSpacing(8)
        lc_key = QLabel(t("about_last_checked"))
        lc_key.setObjectName("form_label")
        lc_key.setFixedWidth(110)
        self._last_checked_lbl = QLabel(_fmt_last_checked(get_last_checked()))
        self._last_checked_lbl.setStyleSheet(f"color: {tk.t2}; font-size: 12px;")
        last_row.addWidget(lc_key)
        last_row.addWidget(self._last_checked_lbl)
        last_row.addStretch()
        lay.addLayout(last_row)

        # Manifest URL row (small, dimmed)
        url_row = QHBoxLayout()
        url_row.setSpacing(8)
        url_key = QLabel(t("about_manifest_url"))
        url_key.setObjectName("form_label")
        url_key.setFixedWidth(110)
        url_val = QLabel(UPDATE_MANIFEST_URL or t("about_manifest_none"))
        url_val.setStyleSheet(f"color: {tk.t4}; font-size: 10px;")
        url_val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        url_val.setWordWrap(True)
        url_row.addWidget(url_key, 0, Qt.AlignmentFlag.AlignTop)
        url_row.addWidget(url_val, 1)
        lay.addLayout(url_row)

        lay.addSpacing(14)
        lay.addWidget(self._divider())
        lay.addSpacing(12)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._check_btn = QPushButton(f"  🔍  {t('about_check_now')}")
        self._check_btn.setObjectName("action_btn")
        self._check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._check_btn.setMinimumWidth(190)
        self._check_btn.clicked.connect(self._do_check)
        btn_row.addWidget(self._check_btn)

        self._preview_btn = QPushButton(f"  👁  {t('about_preview_banner')}")
        self._preview_btn.setObjectName("secondary_btn")
        self._preview_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._preview_btn.setMinimumWidth(220)
        self._preview_btn.setToolTip(t("about_preview_tip"))
        self._preview_btn.clicked.connect(self._do_preview)
        btn_row.addWidget(self._preview_btn)

        btn_row.addStretch()
        lay.addLayout(btn_row)

        lay.addSpacing(10)

        # Status label
        self._status_lbl = QLabel(t("about_check_idle"))
        self._status_lbl.setWordWrap(True)
        self._status_lbl.setStyleSheet(f"color: {tk.t3}; font-size: 12px;")
        lay.addWidget(self._status_lbl)

        return card

    def _build_support_card(self) -> QFrame:
        card = self._card()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(28, 20, 28, 20)
        lay.setSpacing(0)

        self._section_title(lay, t("about_support_title"), "🆘")
        lay.addWidget(self._divider())
        lay.addSpacing(12)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        for label_key, url in (
            ("about_btn_docs",      _URL_DOCS),
            ("about_btn_changelog", _URL_CHANGELOG),
            ("about_btn_bug",       _URL_BUG),
            ("about_btn_feedback",  _URL_FEEDBACK),
        ):
            btn = QPushButton(t(label_key))
            btn.setObjectName("secondary_btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, u=url: QDesktopServices.openUrl(QUrl(u)))
            btn_row.addWidget(btn)

        btn_row.addStretch()
        lay.addLayout(btn_row)

        return card

    # ── UI helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _card() -> QFrame:
        f = QFrame()
        f.setObjectName("analytics_card")
        f.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return f

    @staticmethod
    def _divider() -> QFrame:
        d = QFrame()
        d.setFixedHeight(1)
        d.setStyleSheet(f"background: {THEME.tokens.border};")
        return d

    @staticmethod
    def _section_title(lay: QVBoxLayout, text: str, icon: str = "") -> None:
        lbl = QLabel(f"{icon}  {text}" if icon else text)
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl.setStyleSheet("margin-bottom: 8px;")
        lay.addWidget(lbl)

    def _add_info_row(
        self,
        lay: QVBoxLayout,
        key: str,
        value: str,
        *,
        value_color: str | None = None,
        value_bold: bool = False,
    ) -> None:
        tk = THEME.tokens
        row = QHBoxLayout()
        row.setSpacing(8)

        key_lbl = QLabel(key)
        key_lbl.setObjectName("form_label")
        key_lbl.setFixedWidth(150)

        val_lbl = QLabel(value)
        style = f"color: {value_color or tk.t1}; font-size: 12px;"
        if value_bold:
            style += " font-weight: bold;"
        val_lbl.setStyleSheet(style)
        val_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        row.addWidget(key_lbl)
        row.addWidget(val_lbl)
        row.addStretch()
        lay.addSpacing(4)
        lay.addLayout(row)

    def _set_status(self, text: str, color: str | None = None) -> None:
        c = color or THEME.tokens.t3
        self._status_lbl.setText(text)
        self._status_lbl.setStyleSheet(f"color: {c}; font-size: 12px;")

    # ── Slots ──────────────────────────────────────────────────────────────────

    def _save_auto_check(self, checked: bool) -> None:
        """Persist the auto-check preference to app_config."""
        try:
            from app.core.database import get_connection
            val = "1" if checked else "0"
            with get_connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO app_config (key, value) VALUES ('update_auto_check', ?)",
                    (val,),
                )
            ShopConfig.invalidate()
        except Exception as exc:
            log.warning("AboutPanel: failed to save update_auto_check: %s", exc)

    def _do_copy_sysinfo(self) -> None:
        """Copy formatted system info block to clipboard."""
        QApplication.clipboard().setText(_build_sysinfo_text())
        self._copy_btn.setText(f"  ✅  {t('about_copied')}")
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(2500, lambda: self._copy_btn.setText(
            f"  📋  {t('about_copy_sysinfo')}"
        ))

    def _do_open_datafolder(self) -> None:
        """Open the data directory in the OS file manager."""
        data_dir = os.path.dirname(DB_PATH)
        if sys.platform == "win32":
            os.startfile(data_dir)          # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", data_dir])
        else:
            subprocess.Popen(["xdg-open", data_dir])

    def _do_check(self) -> None:
        """Run update check in a background thread."""
        if self._worker and self._worker.isRunning():
            return

        self._check_btn.setEnabled(False)
        self._check_btn.setText(f"  🔍  {t('about_checking')}")
        self._set_status(t("about_checking"))
        self._found_manifest = None

        self._worker = UpdateCheckWorker(parent=self)
        self._worker.update_available.connect(self._on_update_found)
        self._worker.up_to_date.connect(self._on_up_to_date)
        self._worker.error.connect(self._on_check_error)
        self._worker.finished.connect(self._on_worker_done)
        self._worker.start()

    def _on_update_found(self, manifest: UpdateManifest) -> None:
        self._found_manifest = manifest
        self._set_status(
            t("about_update_found", version=manifest.version),
            THEME.tokens.green,
        )
        self._refresh_last_checked()

    def _on_up_to_date(self) -> None:
        self._set_status(t("about_up_to_date"), THEME.tokens.green)
        self._refresh_last_checked()

    def _on_check_error(self, msg: str) -> None:
        self._set_status(t("about_check_error", reason=msg), THEME.tokens.orange)
        log.debug("AboutPanel: update check error: %s", msg)

    def _on_worker_done(self) -> None:
        self._check_btn.setEnabled(True)
        self._check_btn.setText(f"  🔍  {t('about_check_now')}")

    def _refresh_last_checked(self) -> None:
        """Re-read the last-checked timestamp from DB and update the label."""
        self._last_checked_lbl.setText(_fmt_last_checked(get_last_checked()))

    def _do_preview(self) -> None:
        """
        Emit preview_banner_requested — AdminDialog will close itself so the
        banner (injected into MainWindow) becomes visible immediately.
        """
        manifest = self._found_manifest or _DEMO_MANIFEST
        self.preview_banner_requested.emit(manifest)
