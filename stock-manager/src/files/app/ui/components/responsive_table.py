"""
app/ui/components/responsive_table.py — Responsive column-hiding for QTableWidget.

Usage
-----
from app.ui.components.responsive_table import make_table_responsive

# After configuring the table's resize modes, call once:
make_table_responsive(self._table, [
    (col_index, min_viewport_width),   # hide col when viewport < min_viewport_width
    ...
])

The returned _TableResizer object keeps itself alive as a child of the table.
"""
from __future__ import annotations

from PyQt6.QtCore import QEvent, QObject
from PyQt6.QtWidgets import QTableWidget


class _TableResizer(QObject):
    """
    QObject event-filter that hides/shows table columns based on viewport width.
    Installed as a child of the table so its lifetime is tied to the table's.
    """

    def __init__(self, table: QTableWidget,
                 hide_at: list[tuple[int, int]]) -> None:
        """
        Args:
            table:   The QTableWidget to watch.
            hide_at: List of (column_index, min_viewport_width).
                     The column is hidden when viewport.width() < min_viewport_width.
        """
        super().__init__(table)          # parent = table → auto-deleted with it
        self._table   = table
        self._hide_at = hide_at
        table.installEventFilter(self)
        self._adapt()                    # apply immediately on construction

    def eventFilter(self, obj, event) -> bool:          # type: ignore[override]
        if obj is self._table and event.type() == QEvent.Type.Resize:
            self._adapt()
        return False                                      # don't consume the event

    def _adapt(self) -> None:
        try:
            vw = self._table.viewport().width()
        except RuntimeError:
            return          # table has been destroyed (C++ side freed)
        header = self._table.horizontalHeader()
        for col, min_w in self._hide_at:
            if col < self._table.columnCount():
                header.setSectionHidden(col, vw < min_w)


def make_table_responsive(table: QTableWidget,
                           hide_at: list[tuple[int, int]]) -> _TableResizer:
    """
    Attach a responsive column-hide listener to *table*.

    Parameters
    ----------
    table   : The QTableWidget instance to make responsive.
    hide_at : List of ``(column_index, min_viewport_width_px)`` tuples.

    Returns
    -------
    The installed _TableResizer (already a child of the table — caller need
    not keep a reference, but may do so to adjust hide_at later).
    """
    return _TableResizer(table, hide_at)
