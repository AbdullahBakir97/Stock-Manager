"""app/ui/workers/ui_watchdog.py — Main-thread event-loop heartbeat.

Dev-only diagnostic: start it once near app startup and it will log a
warning whenever the UI thread hasn't returned control to the event loop
within a threshold (default 50 ms). Use it to spot regressions where
someone accidentally puts a sync DB call back on the UI thread.

Enable by setting the environment variable ``SM_UI_WATCHDOG=1`` before
launching. If unset, ``start()`` is a no-op.

Example
-------

    from app.ui.workers.ui_watchdog import start as start_watchdog
    start_watchdog()

Implementation
--------------
A `QTimer` with interval 10 ms stamps `time.monotonic()` into a shared
variable on every tick. A daemon thread reads that stamp every 50 ms and
emits a warning whenever the delta exceeds the threshold — i.e. the UI
thread missed its heartbeat, which means it was blocked.

Zero cost when disabled; the `start()` function returns early if the env
flag is not set.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Optional

from PyQt6.QtCore import QTimer

_log = logging.getLogger(__name__)

_ENV_FLAG = "SM_UI_WATCHDOG"
_HEARTBEAT_MS = 10           # how often the UI thread stamps
_POLL_INTERVAL_S = 0.05      # how often the watchdog thread checks
_STALL_THRESHOLD_S = 0.050   # warn when stamp is older than this

_state = {
    "last_beat":  0.0,
    "running":    False,
    "timer":      None,        # type: ignore[assignment]
    "thread":     None,        # type: ignore[assignment]
    "threshold":  _STALL_THRESHOLD_S,
}


def _beat() -> None:
    _state["last_beat"] = time.monotonic()


def _poll_loop() -> None:
    worst = 0.0
    while _state["running"]:
        time.sleep(_POLL_INTERVAL_S)
        last = _state["last_beat"]
        if last <= 0:
            continue
        gap = time.monotonic() - last
        if gap > _state["threshold"]:
            # Log once per stall; track the worst seen in this stretch
            if gap > worst:
                worst = gap
                _log.warning(
                    "UI-watchdog: main thread blocked for %.0f ms "
                    "(threshold %.0f ms)",
                    gap * 1000.0, _state["threshold"] * 1000.0,
                )
        else:
            # UI recovered — reset the worst-seen tracker for the next stall
            worst = 0.0


def start(threshold_ms: int = 50) -> None:
    """Start the watchdog if the ``SM_UI_WATCHDOG`` env var is truthy.

    Safe to call multiple times — later calls are no-ops.
    """
    if _state["running"]:
        return
    if os.environ.get(_ENV_FLAG, "").lower() not in ("1", "true", "yes", "on"):
        return
    _state["threshold"] = max(0.010, threshold_ms / 1000.0)
    _state["running"] = True
    _state["last_beat"] = time.monotonic()

    timer = QTimer()
    timer.setInterval(_HEARTBEAT_MS)
    timer.timeout.connect(_beat)
    timer.start()
    _state["timer"] = timer

    thread = threading.Thread(target=_poll_loop, name="ui-watchdog", daemon=True)
    thread.start()
    _state["thread"] = thread

    _log.info(
        "UI-watchdog enabled (threshold=%dms, heartbeat=%dms)",
        int(_state["threshold"] * 1000), _HEARTBEAT_MS,
    )


def stop() -> None:
    """Stop the watchdog if running."""
    if not _state["running"]:
        return
    _state["running"] = False
    timer = _state.get("timer")
    if timer is not None:
        try:
            timer.stop()
        except Exception:
            pass
    _state["timer"] = None
    _state["thread"] = None
