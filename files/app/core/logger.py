"""
app/core/logger.py — Professional logging framework for Stock Manager Pro.

Provides rotating file and console handlers with PyInstaller compatibility.
Log format: [YYYY-MM-DD HH:MM:SS] [LEVEL] [module] Message
"""
from __future__ import annotations

import os
import sys
import logging
from logging.handlers import RotatingFileHandler


# ── Configuration constants ────────────────────────────────────────────────────

_LOG_FORMAT = "[%(asctime)s] [%(levelname)-5s] [%(name)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB per file
_BACKUP_COUNT = 5  # Keep 5 rotated backups


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
    global _INITIALIZED
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
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.DEBUG)
        root.addHandler(console_handler)

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
