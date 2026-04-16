"""
app/services/undo_manager.py — Excel-like undo/redo stack for all operations.

Every user operation pushes a Command onto the undo stack. Ctrl+Z pops and
executes its undo function; Ctrl+Y pops from the redo stack and re-applies.

Usage from a controller:
    from app.services.undo_manager import UNDO, Command

    # Before an operation, capture state; after, push the command
    UNDO.push(Command(
        label="Stock IN (iPhone 15, +5)",
        undo_fn=lambda: stock_svc.stock_adjust(item_id, -5, "undo"),
        redo_fn=lambda: stock_svc.stock_adjust(item_id, +5, "redo"),
    ))
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from collections import deque

from PyQt6.QtCore import QObject, pyqtSignal


@dataclass
class Command:
    """A single undoable operation.

    Attributes:
        label:   Short human-readable description shown in status bar and tooltip
        undo_fn: Callable() that reverts the operation
        redo_fn: Callable() that re-applies the operation (same as original action)
    """
    label: str
    undo_fn: Callable[[], None]
    redo_fn: Callable[[], None]


class UndoManager(QObject):
    """Application-wide undo/redo stack (singleton via module-level UNDO).

    - Maximum 100 operations on the undo stack (oldest discarded when full)
    - Redo stack cleared on every new push (branching edits)
    - Emits signals when stacks change so UI buttons can enable/disable
    - Suppresses recursion: undo/redo calls don't push new commands
    """

    MAX_DEPTH = 100

    # Emitted when either stack changes — UI listens to enable/disable buttons
    changed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._undo: deque[Command] = deque(maxlen=self.MAX_DEPTH)
        self._redo: deque[Command] = deque(maxlen=self.MAX_DEPTH)
        self._suppressed = False   # True while undo/redo is running

    # ── Public API ────────────────────────────────────────────────────────────

    def push(self, cmd: Command) -> None:
        """Record a new operation. Clears the redo stack."""
        if self._suppressed:
            return
        self._undo.append(cmd)
        self._redo.clear()
        self.changed.emit()

    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo_label(self) -> str:
        return self._undo[-1].label if self._undo else ""

    def redo_label(self) -> str:
        return self._redo[-1].label if self._redo else ""

    def undo(self) -> str | None:
        """Pop the top command and run its undo_fn. Returns the label or None."""
        if not self._undo:
            return None
        cmd = self._undo.pop()
        self._suppressed = True
        try:
            cmd.undo_fn()
        except Exception:
            # If undo fails, discard the command (can't re-run it safely)
            self._suppressed = False
            self.changed.emit()
            raise
        self._suppressed = False
        self._redo.append(cmd)
        self.changed.emit()
        return cmd.label

    def redo(self) -> str | None:
        """Pop the top redo command and re-run it. Returns the label or None."""
        if not self._redo:
            return None
        cmd = self._redo.pop()
        self._suppressed = True
        try:
            cmd.redo_fn()
        except Exception:
            self._suppressed = False
            self.changed.emit()
            raise
        self._suppressed = False
        self._undo.append(cmd)
        self.changed.emit()
        return cmd.label

    def clear(self) -> None:
        """Clear both stacks (e.g. on language change, admin panel close)."""
        self._undo.clear()
        self._redo.clear()
        self.changed.emit()


# Application-wide singleton
UNDO = UndoManager()
