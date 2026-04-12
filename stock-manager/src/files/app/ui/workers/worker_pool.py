"""
app/ui/workers/worker_pool.py — Central non-blocking task manager.

Design principles
-----------------
* Built on QThreadPool + QRunnable — threads are reused, no per-task
  creation cost.  Max 4 concurrent workers prevents SQLite contention.
* Keyed tasks — each logical operation gets a string key (e.g. "summary",
  "inventory_filter", "alerts").  Submitting a new task with the same key
  silently drops the in-flight result so stale data never overwrites fresh.
* Debounced submit — submit_debounced() waits N ms of silence before
  dispatching.  Rapid calls (search-as-you-type) collapse into one DB hit.
* All callbacks fire on the main Qt thread via signals — safe to update
  widgets directly in on_result / on_error handlers.
* Zero leaked threads — every task is self-cleaning; the pool is a
  module-level singleton created once for the process lifetime.

Quick reference
---------------
    from app.ui.workers.worker_pool import POOL

    # One-shot background query:
    POOL.submit("summary", lambda: repo.get_summary(), self._on_summary)

    # Debounced search (only fires after 200 ms of silence):
    POOL.submit_debounced("search", lambda: repo.search(q), self._on_items)

    # Cancel any pending/in-flight work for a key:
    POOL.cancel("search")
"""
from __future__ import annotations

import threading
from typing import Any, Callable

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, QTimer, pyqtSignal, pyqtSlot


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
            if not self._cancelled.is_set():
                try:
                    self._signals.result.emit(value)
                except RuntimeError:
                    pass  # widget deleted before signal delivered
        except Exception as exc:            # noqa: BLE001
            if not self._cancelled.is_set():
                try:
                    self._signals.error.emit(str(exc))
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

    # ── Public API ────────────────────────────────────────────────────────────

    def submit(
        self,
        key:       str,
        fn:        Callable[[], Any],
        on_result: Callable[[Any], None],
        on_error:  Callable[[str], None] | None = None,
    ) -> None:
        """
        Run fn() on a pool thread.  on_result(value) is called on the main
        thread when it finishes.  Any previous in-flight task with the same
        key is superseded — its result is dropped.
        """
        self._invalidate(key)           # cancel stale result

        ev   = threading.Event()
        sigs = _Signals()

        sigs.result.connect(on_result)
        if on_error:
            sigs.error.connect(on_error)
        # Cleanup regardless of success/failure
        sigs.result.connect(lambda _: self._cleanup(key, ev))
        sigs.error.connect(lambda _: self._cleanup(key, ev))

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
        # Restart the debounce timer
        if key in self._debounce_timers:
            self._debounce_timers[key].stop()
            self._debounce_timers[key].deleteLater()
            del self._debounce_timers[key]

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(delay_ms)
        timer.timeout.connect(lambda: self._fire_debounced(key, fn, on_result, on_error))
        self._debounce_timers[key] = timer
        timer.start()

    def cancel(self, key: str) -> None:
        """Cancel any pending or in-flight work registered under key."""
        self._invalidate(key)
        if key in self._debounce_timers:
            self._debounce_timers[key].stop()
            self._debounce_timers[key].deleteLater()
            del self._debounce_timers[key]

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

    def _cleanup(self, key: str, ev: threading.Event) -> None:
        """Remove tracking state after a task completes."""
        if self._cancel_events.get(key) is ev:
            self._cancel_events.pop(key, None)
        self._signals.pop(key, None)


# ── Module-level singleton ────────────────────────────────────────────────────

POOL = WorkerPool()
