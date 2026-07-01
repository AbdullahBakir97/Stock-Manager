"""
app/core/logger.py — Professional logging framework for Stock Manager Pro.

Provides rotating file and console handlers with PyInstaller compatibility.
Log format: [YYYY-MM-DD HH:MM:SS] [LEVEL] [module] Message
"""
from __future__ import annotations

import os
import sys
import logging
import threading
from collections import deque
from logging.handlers import RotatingFileHandler


# ── Configuration constants ────────────────────────────────────────────────────

_LOG_FORMAT = "[%(asctime)s] [%(levelname)-5s] [%(name)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB per file
_BACKUP_COUNT = 5  # Keep 5 rotated backups
_RING_CAPACITY = 5000  # in-memory records kept for the in-app log viewer


# ── In-memory ring buffer for the in-app log viewer ─────────────────────────────
# Deliberately framework-free (no PyQt6) — logging starts before QApplication.
# The UI layer registers a listener that marshals records onto the Qt thread.

class LogRecordView:
    """A lightweight, picklable snapshot of a log record for the UI.

    `detail` holds the formatted traceback (when the record carries exc_info),
    so the in-app viewer can show the real failure — not just the summary line.
    """
    __slots__ = ("time", "level", "levelno", "name", "message", "detail")

    def __init__(self, time: str, level: str, levelno: int,
                 name: str, message: str, detail: str = "") -> None:
        self.time = time
        self.level = level
        self.levelno = levelno
        self.name = name
        self.message = message
        self.detail = detail

    @property
    def has_detail(self) -> bool:
        return bool(self.detail)


class RingBufferHandler(logging.Handler):
    """Keeps the last N records in memory and notifies listeners on each emit.

    Listeners are plain callables invoked (on the logging thread) with a single
    LogRecordView. They must be cheap and thread-safe — the UI listener simply
    emits a queued Qt signal, doing the real work on the main thread.
    """

    def __init__(self, capacity: int = _RING_CAPACITY) -> None:
        super().__init__(level=logging.DEBUG)
        self._buf: deque[LogRecordView] = deque(maxlen=capacity)
        self._listeners: list = []
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = record.getMessage()
            detail = ""
            # Pull the traceback (if any) so the viewer shows the real failure.
            if record.exc_info:
                detail = self._format_exc(record.exc_info)
            elif record.exc_text:
                detail = record.exc_text
            if record.stack_info:
                detail = (detail + "\n" + record.stack_info).strip()
            if detail:
                # Make the collapsed one-liner informative too: append the
                # exception's own summary line (e.g. "OperationalError: ...").
                first = detail.strip().splitlines()[-1] if detail.strip() else ""
                if first and first not in message:
                    message = f"{message} — {first}"
            view = LogRecordView(
                time=self.format_time(record),
                level=record.levelname,
                levelno=record.levelno,
                name=record.name,
                message=message,
                detail=detail,
            )
        except Exception:
            return
        with self._lock:
            self._buf.append(view)
            listeners = list(self._listeners)
        for cb in listeners:
            try:
                cb(view)
            except Exception:
                pass  # never let a UI listener break logging

    @staticmethod
    def format_time(record: logging.LogRecord) -> str:
        import time as _t
        return _t.strftime(_DATE_FORMAT, _t.localtime(record.created))

    @staticmethod
    def _format_exc(exc_info) -> str:
        import traceback
        try:
            return "".join(traceback.format_exception(*exc_info)).rstrip()
        except Exception:
            return ""

    def snapshot(self) -> list:
        with self._lock:
            return list(self._buf)

    def add_listener(self, cb) -> None:
        with self._lock:
            if cb not in self._listeners:
                self._listeners.append(cb)

    def remove_listener(self, cb) -> None:
        with self._lock:
            if cb in self._listeners:
                self._listeners.remove(cb)


_ring_handler: "RingBufferHandler | None" = None


# ── Log path resolution ────────────────────────────────────────────────────────

def _log_dir() -> str:
    """
    Resolve log directory based on PyInstaller frozen status.
    Production: %LOCALAPPDATA%\\StockPro\\StockManagerPro\\logs\\
    Development: src/files/logs/
    """
    if getattr(sys, "frozen", False):
        # PyInstaller bundle — use user's AppData
        try:
            from platformdirs import user_data_dir
            base = user_data_dir("StockManagerPro", "StockPro")
        except ImportError:
            base = os.path.join(
                os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                "StockPro", "StockManagerPro",
            )
    else:
        # Development: use src/files/logs/
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        base = root

    logs_dir = os.path.join(base, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir


# ── Logger initialization ──────────────────────────────────────────────────────

_LOG_DIR = _log_dir()
_LOG_PATH = os.path.join(_LOG_DIR, "stock_manager.log")
_INITIALIZED = False


def _init_root_logger() -> None:
    """
    Initialize the root logger with rotating file handler and console handler.
    Called once on first get_logger() call.
    """
    global _INITIALIZED, _ring_handler
    if _INITIALIZED:
        return

    root = logging.getLogger()

    # Set log level based on frozen status (DEBUG in dev, INFO in prod)
    if getattr(sys, "frozen", False):
        root.setLevel(logging.INFO)
    else:
        root.setLevel(logging.DEBUG)

    # Create formatters
    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # ── File handler (rotating) ────────────────────────────────────────────────
    file_handler = RotatingFileHandler(
        _LOG_PATH,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)  # Always capture DEBUG in files
    root.addHandler(file_handler)

    # ── Console handler (development only) ─────────────────────────────────────
    if not getattr(sys, "frozen", False):
        # Force UTF-8 on Windows consoles (cp1252 can't handle → ✓ etc.)
        import io
        utf8_stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
        ) if hasattr(sys.stdout, "buffer") else sys.stdout
        console_handler = logging.StreamHandler(utf8_stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.DEBUG)
        root.addHandler(console_handler)

    # ── In-memory ring buffer (feeds the in-app log viewer) ────────────────────
    _ring_handler = RingBufferHandler()
    _ring_handler.setLevel(logging.DEBUG)
    root.addHandler(_ring_handler)

    _INITIALIZED = True


# ── Public API ─────────────────────────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    """
    Get a module-specific logger.

    Args:
        name: Module name (typically __name__)

    Returns:
        logging.Logger instance with the given name
    """
    _init_root_logger()
    return logging.getLogger(name)


# ── In-app log viewer support ───────────────────────────────────────────────────

def get_log_buffer() -> list:
    """Return a snapshot of the recent in-memory log records (LogRecordView)."""
    _init_root_logger()
    return _ring_handler.snapshot() if _ring_handler else []


def add_log_listener(callback) -> None:
    """Register a callable invoked with each new LogRecordView (any thread).

    Keep it cheap and thread-safe — the UI listener should only emit a queued
    Qt signal and do the real work on the main thread.
    """
    _init_root_logger()
    if _ring_handler:
        _ring_handler.add_listener(callback)


def remove_log_listener(callback) -> None:
    _init_root_logger()
    if _ring_handler:
        _ring_handler.remove_listener(callback)


def log_file_path() -> str:
    """Absolute path of the active rotating log file."""
    return _LOG_PATH


def log_dir() -> str:
    """Directory holding the log files."""
    return _LOG_DIR


def set_verbose(enabled: bool) -> None:
    """Temporarily lower/raise the root level so the viewer can show DEBUG.

    In production the root level is INFO, so DEBUG records are never emitted;
    turning this on raises verbosity to DEBUG while troubleshooting, off
    restores the default for the current build (INFO frozen / DEBUG dev).
    """
    _init_root_logger()
    if enabled:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(
            logging.INFO if getattr(sys, "frozen", False) else logging.DEBUG
        )


def is_verbose() -> bool:
    return logging.getLogger().getEffectiveLevel() <= logging.DEBUG
