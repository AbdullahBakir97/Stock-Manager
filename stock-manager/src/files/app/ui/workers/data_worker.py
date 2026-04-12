"""
app/ui/workers/data_worker.py — Background thread for loading page data.

Keeps the main thread (and UI) fully responsive while data is fetched
from SQLite. Each worker emits result/error signals on completion.
"""
from __future__ import annotations

from typing import Callable, Any
from PyQt6.QtCore import QThread, pyqtSignal


class DataWorker(QThread):
    """Generic background worker: runs `fn()` in a thread, emits result.

    Usage:
        worker = DataWorker(lambda: my_repo.get_all())
        worker.result.connect(self._on_data_ready)
        worker.error.connect(self._on_error)
        worker.start()
    """
    result = pyqtSignal(object)   # emits the return value of fn
    error  = pyqtSignal(str)      # emits str(exception) on failure

    def __init__(self, fn: Callable[[], Any], parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self) -> None:
        try:
            data = self._fn()
            self.result.emit(data)
        except Exception as e:
            self.error.emit(str(e))


class StartupWorker(QThread):
    """Runs multiple named startup steps sequentially, reporting progress.

    Usage:
        worker = StartupWorker()
        worker.add_step("Loading inventory…", lambda: item_repo.get_all())
        worker.step_done.connect(lambda name, pct, data: ...)
        worker.all_done.connect(lambda results: ...)
        worker.start()
    """
    step_done = pyqtSignal(str, int, object)   # (step_name, pct, result)
    all_done  = pyqtSignal(dict)               # {step_name: result}
    step_error = pyqtSignal(str, str)          # (step_name, error_msg)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._steps: list[tuple[str, Callable]] = []

    def add_step(self, name: str, fn: Callable[[], Any]) -> None:
        self._steps.append((name, fn))

    def run(self) -> None:
        results = {}
        n = len(self._steps)
        for i, (name, fn) in enumerate(self._steps):
            try:
                data = fn()
                results[name] = data
                pct = int((i + 1) / n * 100)
                self.step_done.emit(name, pct, data)
            except Exception as e:
                self.step_error.emit(name, str(e))
                results[name] = None
        self.all_done.emit(results)
