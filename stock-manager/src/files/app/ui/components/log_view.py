"""app/ui/components/log_view.py — in-app log viewer.

Components:
    LogBus     — QObject bridge: turns the logger's ring-buffer listener
                 (called on any thread) into a thread-safe Qt signal, and
                 tracks unseen warning/error counts for the footer indicator.
    LogViewer  — the actual viewer widget: colour-coded table, level/source/
                 text filters, live tail (pause/resume), verbose toggle,
                 copy/export, open-log-file/folder, and an optional cloud-sync
                 status block.
    LogWindow  — a non-modal top-level window wrapping a LogViewer.
    LogsPage   — sidebar page wrapping a LogViewer + a "pop out" button.

Everything reads from app.core.logger's in-memory ring buffer, so any message
logged anywhere in the app appears here automatically.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QCheckBox, QFrame, QSizePolicy, QApplication, QFileDialog,
    QDialog, QPlainTextEdit, QDialogButtonBox,
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont

from app.core import logger as _logmod
from app.core.i18n import t
from app.core.theme import THEME

_MAX_DISPLAY = 2500  # cap visible rows so the table stays responsive

_LEVELS = [
    ("log_lvl_all",     0),
    ("log_lvl_debug",   logging.DEBUG),
    ("log_lvl_info",    logging.INFO),
    ("log_lvl_warning", logging.WARNING),
    ("log_lvl_error",   logging.ERROR),
]


# ── Shared bus ──────────────────────────────────────────────────────────────────

class LogBus(QObject):
    """Bridges the (thread-agnostic) logger listener to Qt signals."""

    record_logged  = pyqtSignal(object)   # LogRecordView, on the UI thread
    counts_changed = pyqtSignal(int, int)  # (unseen_warnings, unseen_errors)

    def __init__(self) -> None:
        super().__init__()
        self._warn = 0
        self._err = 0
        # Tally on the UI thread (queued from worker threads).
        self.record_logged.connect(self._tally)
        _logmod.add_log_listener(self._on_record)

    def _on_record(self, view) -> None:
        # Called on whatever thread logged. Only emit — never touch widgets.
        try:
            self.record_logged.emit(view)
        except RuntimeError:
            pass  # bus torn down during shutdown

    def _tally(self, view) -> None:
        if view.levelno >= logging.ERROR:
            self._err += 1
        elif view.levelno >= logging.WARNING:
            self._warn += 1
        else:
            return
        self.counts_changed.emit(self._warn, self._err)

    def reset_counts(self) -> None:
        self._warn = self._err = 0
        self.counts_changed.emit(0, 0)


_BUS: "LogBus | None" = None


def log_bus() -> LogBus:
    """App-wide singleton bus (create on the main thread, e.g. in MainWindow)."""
    global _BUS
    if _BUS is None:
        _BUS = LogBus()
    return _BUS


# ── Detail dialog ─────────────────────────────────────────────────────────────

class _LogDetailDialog(QDialog):
    """Shows a single log record's full message + traceback (monospaced, copyable)."""

    def __init__(self, view, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("log_detail_title"))
        self.resize(760, 460)
        THEME.apply(self)
        tk = THEME.tokens
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(8)

        header = QLabel(f"{view.time}   ·   {view.level}   ·   {view.name}")
        color = {"WARNING": tk.orange, "ERROR": tk.red,
                 "CRITICAL": tk.red}.get(view.level, tk.t2)
        header.setStyleSheet(f"color:{color}; font-weight:600; background:transparent;")
        lay.addWidget(header)

        body = view.message if not view.detail else f"{view.message}\n\n{view.detail}"
        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setPlainText(body)
        self._text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        mono = QFont("Consolas"); mono.setStyleHint(QFont.StyleHint.Monospace)
        mono.setPointSize(9)
        self._text.setFont(mono)
        lay.addWidget(self._text, 1)

        btns = QDialogButtonBox()
        copy_btn = btns.addButton(t("log_copy"), QDialogButtonBox.ButtonRole.ActionRole)
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(body))
        close_btn = btns.addButton(QDialogButtonBox.StandardButton.Close)
        close_btn.clicked.connect(self.accept)
        lay.addWidget(btns)


# ── Viewer ──────────────────────────────────────────────────────────────────────

class LogViewer(QWidget):
    """Colour-coded, filterable, live log table."""

    def __init__(self, sync_service=None, parent=None) -> None:
        super().__init__(parent)
        self._sync = sync_service
        self._records: list = list(_logmod.get_log_buffer())
        self._paused = False
        self._build()
        self._refresh_sources()
        self._rebuild()
        log_bus().record_logged.connect(self._on_record)
        if self._sync is not None:
            self._sync_timer = QTimer(self)
            self._sync_timer.timeout.connect(self._refresh_sync_status)
            self._sync_timer.start(4000)
            # Instant refresh on sync lifecycle signals (not just the 4s poll).
            for _sig in ("sync_started", "sync_completed", "sync_failed"):
                s = getattr(self._sync, _sig, None)
                if s is not None:
                    try:
                        s.connect(lambda *a: self._refresh_sync_status())
                    except Exception:
                        pass
            self._refresh_sync_status()

    # ── build ──
    def _build(self) -> None:
        tk = THEME.tokens
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # Cloud-sync diagnostics card — status, mode/role/host, sync-now + filter
        self._sync_box = QFrame()
        self._sync_box.setObjectName("kpi_tile")
        sb = QHBoxLayout(self._sync_box)
        sb.setContentsMargins(12, 8, 12, 8)
        sb.setSpacing(12)

        textcol = QVBoxLayout()
        textcol.setSpacing(2)
        self._sync_lbl = QLabel("")
        self._sync_lbl.setStyleSheet(f"color:{tk.t2}; background:transparent;")
        self._sync_detail = QLabel("")
        self._sync_detail.setStyleSheet(
            f"color:{tk.t3}; background:transparent; font-size:11px;")
        textcol.addWidget(self._sync_lbl)
        textcol.addWidget(self._sync_detail)
        sb.addLayout(textcol, 1)

        self._sync_only_btn = QPushButton(t("log_sync_only"))
        self._sync_only_btn.setObjectName("log_sync_only_btn")
        self._sync_only_btn.setCheckable(True)
        self._sync_only_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sync_only_btn.toggled.connect(self._rebuild)
        sb.addWidget(self._sync_only_btn)

        self._sync_now_btn = QPushButton(t("log_sync_now"))
        self._sync_now_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sync_now_btn.clicked.connect(self._on_sync_now)
        sb.addWidget(self._sync_now_btn)

        root.addWidget(self._sync_box)
        self._sync_box.setVisible(self._sync is not None)

        # Toolbar
        bar = QHBoxLayout()
        bar.setSpacing(8)

        self._level_combo = QComboBox()
        for key, lvl in _LEVELS:
            self._level_combo.addItem(t(key), lvl)
        self._level_combo.setCurrentIndex(2)  # default INFO+
        self._level_combo.currentIndexChanged.connect(self._rebuild)
        bar.addWidget(self._level_combo)

        self._source_combo = QComboBox()
        self._source_combo.addItem(t("log_all_sources"), "")
        self._source_combo.currentIndexChanged.connect(self._rebuild)
        bar.addWidget(self._source_combo)

        self._search = QLineEdit()
        self._search.setPlaceholderText(t("log_search_placeholder"))
        self._search.textChanged.connect(self._rebuild)
        bar.addWidget(self._search, 1)

        self._verbose = QCheckBox(t("log_verbose"))
        self._verbose.setToolTip(t("log_verbose_tip"))
        self._verbose.setChecked(_logmod.is_verbose())
        self._verbose.toggled.connect(_logmod.set_verbose)
        bar.addWidget(self._verbose)

        self._pause_btn = QPushButton(t("log_pause"))
        self._pause_btn.setCheckable(True)
        self._pause_btn.toggled.connect(self._on_pause)
        bar.addWidget(self._pause_btn)
        root.addLayout(bar)

        # Table
        self._table = QTableWidget()
        self._table.setObjectName("log_table")
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(
            [t("log_col_time"), t("log_col_level"),
             t("log_col_source"), t("log_col_message")])
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setWordWrap(False)
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setDefaultSectionSize(20)
        self._table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self._table.setToolTip(t("log_row_tip"))
        root.addWidget(self._table, 1)

        # Bottom actions
        actions = QHBoxLayout()
        actions.setSpacing(8)
        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet(f"color:{tk.t3}; background:transparent;")
        actions.addWidget(self._count_lbl, 1)
        for key, slot in (
            ("log_clear", self._clear),
            ("log_copy", self._copy),
            ("log_export", self._export),
            ("log_open_file", self._open_file),
            ("log_open_folder", self._open_folder),
        ):
            b = QPushButton(t(key))
            b.clicked.connect(slot)
            actions.addWidget(b)
        root.addLayout(actions)

    # ── data ──
    def _refresh_sources(self) -> None:
        cur = self._source_combo.currentData()
        names = sorted({r.name for r in self._records})
        self._source_combo.blockSignals(True)
        self._source_combo.clear()
        self._source_combo.addItem(t("log_all_sources"), "")
        for n in names:
            self._source_combo.addItem(n, n)
        idx = self._source_combo.findData(cur)
        self._source_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._source_combo.blockSignals(False)

    # Records considered "cloud sync" for the quick filter.
    _SYNC_SOURCE = "app.services.sync_service"
    _SYNC_KEYWORDS = ("sync", "turso", "replica", "cloud")

    @classmethod
    def _is_sync_record(cls, view) -> bool:
        if view.name == cls._SYNC_SOURCE:
            return True
        m = view.message.lower()
        return any(k in m for k in cls._SYNC_KEYWORDS)

    def _passes(self, view) -> bool:
        if view.levelno < (self._level_combo.currentData() or 0):
            return False
        btn = getattr(self, "_sync_only_btn", None)
        if btn is not None and btn.isChecked() and not self._is_sync_record(view):
            return False
        src = self._source_combo.currentData()
        if src and view.name != src:
            return False
        text = self._search.text().strip().lower()
        if text and text not in view.message.lower() and text not in view.name.lower():
            return False
        return True

    def _rebuild(self) -> None:
        self._table.setRowCount(0)
        rows = [r for r in self._records if self._passes(r)][-_MAX_DISPLAY:]
        self._table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self._set_row(i, r)
        self._count_lbl.setText(
            t("log_count", shown=len(rows), total=len(self._records)))
        self._scroll_to_bottom()

    def _set_row(self, i: int, r) -> None:
        tk = THEME.tokens
        color = {
            "DEBUG": tk.t4, "INFO": tk.t2, "WARNING": tk.orange,
            "ERROR": tk.red, "CRITICAL": tk.red,
        }.get(r.level, tk.t2)
        has_detail = getattr(r, "has_detail", False)
        # Prefix a ▸ affordance on rows that carry a traceback/detail.
        msg = ("▸ " + r.message) if has_detail else r.message
        cells = [r.time, r.level, r.name, msg]
        for c, txt in enumerate(cells):
            it = QTableWidgetItem(txt)
            it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            if c == 0:
                # Stash the record on the row so double-click can open detail.
                it.setData(Qt.ItemDataRole.UserRole, r)
            if c == 1:  # level column always coloured
                it.setForeground(QColor(color))
                f = QFont(); f.setBold(r.levelno >= logging.WARNING)
                it.setFont(f)
            elif r.levelno >= logging.WARNING:
                it.setForeground(QColor(color))
            if c == 3 and has_detail:
                it.setToolTip(t("log_row_tip"))
            self._table.setItem(i, c, it)

    def _on_record(self, view) -> None:
        self._records.append(view)
        if len(self._records) > _logmod._RING_CAPACITY:
            self._records = self._records[-_logmod._RING_CAPACITY:]
        # keep the source filter current
        if self._source_combo.findData(view.name) < 0:
            self._source_combo.addItem(view.name, view.name)
        if self._paused or not self._passes(view):
            return
        at_bottom = self._is_at_bottom()
        r = self._table.rowCount()
        if r >= _MAX_DISPLAY:
            self._table.removeRow(0)
            r -= 1
        self._table.insertRow(r)
        self._set_row(r, view)
        self._count_lbl.setText(
            t("log_count", shown=self._table.rowCount(), total=len(self._records)))
        if at_bottom:
            self._scroll_to_bottom()

    def _on_cell_double_clicked(self, row: int, _col: int) -> None:
        """Open the detail dialog for the double-clicked log row."""
        item = self._table.item(row, 0)
        if item is None:
            return
        view = item.data(Qt.ItemDataRole.UserRole)
        if view is not None:
            _LogDetailDialog(view, self).exec()

    # ── helpers ──
    def _is_at_bottom(self) -> bool:
        sb = self._table.verticalScrollBar()
        return sb.value() >= sb.maximum() - 4

    def _scroll_to_bottom(self) -> None:
        self._table.scrollToBottom()

    def _on_pause(self, paused: bool) -> None:
        self._paused = paused
        self._pause_btn.setText(t("log_resume") if paused else t("log_pause"))
        if not paused:
            self._rebuild()

    def _clear(self) -> None:
        # Clears the VIEW only (the on-disk log file is untouched).
        self._records = []
        self._table.setRowCount(0)
        self._count_lbl.setText(t("log_count", shown=0, total=0))

    def _copy(self) -> None:
        lines = []
        for r in range(self._table.rowCount()):
            lines.append("  ".join(
                self._table.item(r, c).text() if self._table.item(r, c) else ""
                for c in range(4)))
        QApplication.clipboard().setText("\n".join(lines))

    def _export(self) -> None:
        from datetime import datetime
        default = f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path, _ = QFileDialog.getSaveFileName(
            self, t("log_export"), default, "Text files (*.txt)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                for r in self._records:
                    f.write(f"[{r.time}] [{r.level}] [{r.name}] {r.message}\n")
                    if getattr(r, "detail", ""):
                        f.write(r.detail.rstrip() + "\n")
        except Exception:
            pass

    def _open_file(self) -> None:
        self._open(_logmod.log_file_path())

    def _open_folder(self) -> None:
        self._open(_logmod.log_dir())

    @staticmethod
    def _open(path: str) -> None:
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass

    def _on_sync_now(self) -> None:
        """Trigger an on-demand cloud sync from the log viewer."""
        if self._sync is not None and hasattr(self._sync, "sync_now"):
            self._sync.sync_now()
            self._refresh_sync_status()

    def _refresh_sync_status(self) -> None:
        if self._sync is None:
            return
        tk = THEME.tokens
        last = getattr(self._sync, "last_sync_time", None)
        err = getattr(self._sync, "last_error", None)
        syncing = bool(getattr(self._sync, "is_syncing", False))
        last_s = last.strftime("%Y-%m-%d %H:%M:%S") if last else t("log_never")

        if err:
            self._sync_lbl.setText(t("log_sync_error", time=last_s, error=err))
            self._sync_lbl.setStyleSheet(
                f"color:{tk.red}; background:transparent; font-weight:600;")
        elif syncing:
            self._sync_lbl.setText(t("log_sync_running"))
            self._sync_lbl.setStyleSheet(
                f"color:{tk.orange}; background:transparent; font-weight:600;")
        else:
            self._sync_lbl.setText(t("log_sync_ok", time=last_s))
            self._sync_lbl.setStyleSheet(
                f"color:{tk.green}; background:transparent; font-weight:600;")

        # Connection detail line: mode · role · host (no secrets).
        try:
            from app.core.database import connection_mode
            info = connection_mode()
            mode_key = {
                "embedded_replica": "log_sync_mode_embedded",
                "http": "log_sync_mode_http",
                "local": "log_sync_mode_local",
            }.get(info["mode"], "log_sync_mode_local")
            role_key = ("log_sync_role_replica" if info["role"] == "replica"
                        else "log_sync_role_primary")
            self._sync_detail.setText(t(
                "log_sync_detail",
                mode=t(mode_key), role=t(role_key), host=info["host"] or "—"))
        except Exception:
            self._sync_detail.setText("")

        self._sync_now_btn.setEnabled(not syncing)

    def retranslate(self) -> None:
        self._table.setHorizontalHeaderLabels(
            [t("log_col_time"), t("log_col_level"),
             t("log_col_source"), t("log_col_message")])
        if hasattr(self, "_sync_only_btn"):
            self._sync_only_btn.setText(t("log_sync_only"))
            self._sync_now_btn.setText(t("log_sync_now"))
            self._refresh_sync_status()


# ── Window + page wrappers ──────────────────────────────────────────────────────

class LogWindow(QWidget):
    """Non-modal top-level log window (kept open alongside normal work).

    Carries its own toast manager so that, when popped out as a separate
    window, ERROR-level records still surface as a professional toast there
    (the main-window footer toast only covers the main window).
    """

    def __init__(self, sync_service=None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setWindowTitle(t("log_window_title"))
        self.resize(1000, 640)
        THEME.apply(self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        self.viewer = LogViewer(sync_service=sync_service, parent=self)
        lay.addWidget(self.viewer)

        # Own toast manager + throttled error surfacing for the pop-out window.
        from app.ui.components.toast import ToastManager
        self._toasts = ToastManager(self)
        self._last_toast_ts = 0.0
        log_bus().record_logged.connect(self._on_record)

    def _on_record(self, view) -> None:
        try:
            if view.levelno < logging.ERROR:
                return
            import time as _t
            now = _t.monotonic()
            if now - self._last_toast_ts < 5.0:
                return
            self._last_toast_ts = now
            msg = view.message
            if len(msg) > 140:
                msg = msg[:139] + "…"
            self._toasts.error(t("log_toast_error", source=view.name, message=msg))
        except Exception:
            pass

    def closeEvent(self, e):  # noqa: N802 (Qt override)
        try:
            log_bus().record_logged.disconnect(self._on_record)
        except Exception:
            pass
        super().closeEvent(e)


class LogsPage(QWidget):
    """Sidebar page hosting the log viewer + a pop-out button."""

    def __init__(self, sync_service=None, parent=None) -> None:
        super().__init__(parent)
        self._sync = sync_service
        self._window: "LogWindow | None" = None
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        header = QHBoxLayout()
        self._title = QLabel(t("log_title"))
        self._title.setObjectName("section_caption")
        f = QFont("Segoe UI", 14, QFont.Weight.Bold)
        self._title.setFont(f)
        header.addWidget(self._title)
        header.addStretch()
        self._popout = QPushButton(t("log_popout"))
        self._popout.clicked.connect(self._pop_out)
        header.addWidget(self._popout)
        root.addLayout(header)

        self.viewer = LogViewer(sync_service=sync_service, parent=self)
        root.addWidget(self.viewer, 1)

    def _pop_out(self) -> None:
        if self._window is None:
            self._window = LogWindow(sync_service=self._sync)
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()

    def refresh(self) -> None:
        pass

    def retranslate(self) -> None:
        self._title.setText(t("log_title"))
        self._popout.setText(t("log_popout"))
        self.viewer.retranslate()
