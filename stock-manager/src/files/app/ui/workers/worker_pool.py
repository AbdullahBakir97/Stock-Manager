"""
app/ui/workers/worker_pool.py — Central non-blocking task manager.

Design principles
-----------------
* Built on QThreadPool + QRunnable — threads are reused, no per-task
  creation cost.  Max 4 concurrent workers prevents SQLite contention.
* Keyed tasks — each logical operation gets a string key (e.g. "summary",
  "inventory_filter", "alerts").  Submitting a new task with the same key
  silently drops the in-flight result so stale data never overwrites fresh.
* **Epoch-based cancellation** — every submit increments a per-key epoch;
  result/error callbacks are gated by the captured epoch, so a signal
  already queued but not yet dispatched can't overwrite the newest result.
* Debounced submit — submit_debounced() waits N ms of silence before
  dispatching.  Rapid calls (search-as-you-type) collapse into one DB hit.
* All callbacks fire on the main Qt thread via signals — safe to update
  widgets directly in on_result / on_error handlers.
* Zero leaked threads — every task is self-cleaning; the pool is a
  module-level singleton created once for the process lifetime.

SQLite threading
----------------
`app/core/database.py` uses `threading.local()` + `check_same_thread=False`,
so each worker thread gets its own connection.  Workers are free to call
repository methods concurrently — SQLite WAL handles contention, and the
max-4-worker cap keeps latency predictable.

Quick reference
---------------
    from app.ui.workers.worker_pool import POOL

    # One-shot background query:
    POOL.submit("summary", lambda: repo.get_summary(), self._on_summary)

    # Debounced search (only fires after 200 ms of silence):
    POOL.submit_debounced("search", lambda: repo.search(q), self._on_items)

    # Cancel any pending/in-flight work for a key:
    POOL.cancel("search")

    # Ask if work is currently queued/running for a key:
    if POOL.has_pending("admin:matrix_ensure"):
        return   # skip — we're still busy

    # Graceful shutdown on app close:
    POOL.shutdown(timeout_ms=2000)
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Callable

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, QTimer, pyqtSignal, pyqtSlot

_log = logging.getLogger(__name__)


# ── Per-task signal carrier ───────────────────────────────────────────────────
# QRunnable cannot host Qt signals, so we attach a lightweight QObject instead.

class _Signals(QObject):
    result = pyqtSignal(object)   # the return value of fn()
    error  = pyqtSignal(str)      # str(exception) on failure


# ── Runnable ──────────────────────────────────────────────────────────────────

class _Task(QRunnable):
    """One unit of background work."""

    def __init__(
        self,
        fn: Callable[[], Any],
        signals: _Signals,
        cancelled: threading.Event,
    ) -> None:
        super().__init__()
        self.setAutoDelete(True)
        self._fn        = fn
        self._signals   = signals
        self._cancelled = cancelled

    @pyqtSlot()
    def run(self) -> None:
        if self._cancelled.is_set():
            return
        try:
            value = self._fn()
        except Exception as exc:            # noqa: BLE001
            if not self._cancelled.is_set():
                try:
                    self._signals.error.emit(str(exc))
                except RuntimeError:
                    pass  # widget deleted before signal delivered
            return

        if not self._cancelled.is_set():
            try:
                self._signals.result.emit(value)
            except RuntimeError:
                pass  # widget deleted before signal delivered


# ── Pool ──────────────────────────────────────────────────────────────────────

class WorkerPool(QObject):
    """
    Application-wide background task dispatcher.

    Thread safety: all public methods must be called from the main thread.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        pool = QThreadPool.globalInstance()
        pool.setMaxThreadCount(4)   # cap DB concurrency; SQLite WAL handles it fine
        self._pool = pool

        self._cancel_events:   dict[str, threading.Event] = {}
        self._signals:         dict[str, _Signals]        = {}
        self._debounce_timers: dict[str, QTimer]          = {}
        # Per-key monotonic epoch. Every submit bumps this; callbacks are
        # gated by the epoch captured at submit-time so a late signal
        # carrying stale data is silently dropped.
        self._epochs:          dict[str, int]             = {}
        self._shutdown:        bool                        = False

    # ── Public API ────────────────────────────────────────────────────────────

    def submit(
        self,
        key:       str,
        fn:        Callable[[], Any],
        on_result: Callable[[Any], None],
        on_error:  Callable[[str], None] | None = None,
    ) -> None:
        """
        Run fn() on a pool thread. `on_result(value)` is called on the main
        thread when it finishes. Any previous in-flight task with the same
        key is superseded — its result is dropped via both the cancel event
        (worker checks before emit) and the epoch guard (main thread drops
        any signal that slipped through).
        """
        if self._shutdown:
            return

        # Invalidate prior in-flight task for this key, then bump epoch.
        self._invalidate(key)
        epoch = self._epochs.get(key, 0) + 1
        self._epochs[key] = epoch

        ev   = threading.Event()
        sigs = _Signals()

        def _guarded_result(value):
            # Drop if a newer submit superseded us, or if the pool is shut down.
            if self._shutdown or self._epochs.get(key) != epoch:
                return
            try:
                on_result(value)
            except Exception:
                _log.exception("POOL on_result handler raised (key=%s)", key)

        def _guarded_error(msg):
            if self._shutdown or self._epochs.get(key) != epoch:
                return
            if on_error is None:
                _log.warning("POOL task error (key=%s): %s", key, msg)
                return
            try:
                on_error(msg)
            except Exception:
                _log.exception("POOL on_error handler raised (key=%s)", key)

        sigs.result.connect(_guarded_result)
        sigs.error.connect(_guarded_error)
        # Cleanup when either fires — only when epoch still matches.
        sigs.result.connect(lambda _e=epoch: self._cleanup(key, ev, _e))
        sigs.error.connect(lambda _e=epoch: self._cleanup(key, ev, _e))

        self._cancel_events[key] = ev
        self._signals[key]       = sigs  # keep alive until signal fires

        self._pool.start(_Task(fn, sigs, ev))

    def submit_debounced(
        self,
        key:       str,
        fn:        Callable[[], Any],
        on_result: Callable[[Any], None],
        on_error:  Callable[[str], None] | None = None,
        delay_ms:  int = 200,
    ) -> None:
        """
        Like submit() but waits delay_ms of silence before dispatching.
        Rapid successive calls with the same key restart the timer — only the
        last call actually reaches the thread pool.
        """
        if self._shutdown:
            return
        # Restart the debounce timer
        existing = self._debounce_timers.pop(key, None)
        if existing is not None:
            existing.stop()
            existing.deleteLater()

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(delay_ms)
        timer.timeout.connect(lambda: self._fire_debounced(key, fn, on_result, on_error))
        self._debounce_timers[key] = timer
        timer.start()

    def cancel(self, key: str) -> None:
        """Cancel any pending or in-flight work registered under key."""
        self._invalidate(key)
        timer = self._debounce_timers.pop(key, None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()

    def has_pending(self, key: str) -> bool:
        """True when a task for `key` is debounced, queued, or running."""
        if key in self._debounce_timers:
            return True
        ev = self._cancel_events.get(key)
        return ev is not None and not ev.is_set()

    def shutdown(self, timeout_ms: int = 2000) -> None:
        """Cancel everything, stop debounce timers, and block up to
        timeout_ms for in-flight tasks to finish. Call from the main
        window's closeEvent to avoid leaks on exit.
        """
        self._shutdown = True
        # Cancel all keyed work
        for key in list(self._cancel_events.keys()):
            self._cancel_events[key].set()
        self._cancel_events.clear()
        self._signals.clear()
        # Stop all debounce timers
        for t in list(self._debounce_timers.values()):
            try:
                t.stop()
                t.deleteLater()
            except RuntimeError:
                pass
        self._debounce_timers.clear()
        # Wait for running tasks to exit (they'll return early via the flag)
        try:
            self._pool.waitForDone(max(0, int(timeout_ms)))
        except Exception:
            pass

    # ── Internal ──────────────────────────────────────────────────────────────

    def _fire_debounced(
        self,
        key:       str,
        fn:        Callable,
        on_result: Callable,
        on_error:  Callable | None,
    ) -> None:
        self._debounce_timers.pop(key, None)
        self.submit(key, fn, on_result, on_error)

    def _invalidate(self, key: str) -> None:
        """Mark any existing in-flight task for key as cancelled."""
        ev = self._cancel_events.pop(key, None)
        if ev:
            ev.set()
        self._signals.pop(key, None)

    def _cleanup(self, key: str, ev: threading.Event, epoch: int) -> None:
        """Remove tracking state after a task completes — only when the
        epoch still matches, so a stale cleanup doesn't nuke the newest
        entries after a rapid resubmit."""
        if self._epochs.get(key) != epoch:
            return
        if self._cancel_events.get(key) is ev:
            self._cancel_events.pop(key, None)
        self._signals.pop(key, None)


# ── Module-level singleton ────────────────────────────────────────────────────

POOL = WorkerPool()
