"""
app/ui/components/barcode_line_edit.py — Barcode-aware search input.

Two pieces:

* ``BarcodeLineEdit`` — the in-header search field that emits
  ``barcode_scanned`` when the user scans into it directly. Has been
  the primary scanner path since the app's inception. Receives the
  keystrokes when it has focus, which is the default state on every
  page EXCEPT the Matrix tab.
* ``GlobalScannerCapture`` — narrow application-wide event filter
  (added v2.5.6) that engages ONLY when a ``MatrixWidget`` has focus.
  Catches scanner bursts the Matrix table would otherwise swallow and
  re-emits them via ``barcode_scanned``. Every other page is left
  completely untouched so the existing BarcodeLineEdit path keeps
  working — earlier v2.5.6 dev build cast a wider net (any non-text-
  input focused widget) and broke the popup on every page.

Together they cover both cases: typed-into-search bar (existing path
on most pages) and Matrix-table-stole-focus (narrow filter path).
"""
from __future__ import annotations

import time

from PyQt6.QtWidgets import QLineEdit, QApplication
from PyQt6.QtCore import Qt, QTimer, QObject, QEvent, pyqtSignal

from app.core.i18n import t


class BarcodeLineEdit(QLineEdit):
    """QLineEdit that detects rapid barcode scanner input."""
    barcode_scanned = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._t = QTimer(self); self._t.setSingleShot(True); self._t.setInterval(80)
        self._t.timeout.connect(self._flush); self._buf: list[str] = []
        self.setPlaceholderText(t("search_placeholder"))

    def keyPressEvent(self, e):
        super().keyPressEvent(e)
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._commit()
        else:
            self._buf.append(e.text()); self._t.start()

    def _flush(self):
        if len(self._buf) >= 3:
            bc = "".join(self._buf).strip()
            if bc: self.barcode_scanned.emit(bc)
        self._buf.clear()

    def _commit(self):
        self._t.stop(); txt = self.text().strip()
        if txt: self.barcode_scanned.emit(txt); self.clear()
        self._buf.clear()


# ── Matrix-tab scanner capture ────────────────────────────────────────────
class GlobalScannerCapture(QObject):
    """Application-wide event filter that recognises USB-HID barcode
    scanner bursts ONLY when a ``MatrixWidget`` has focus, and re-emits
    them via ``barcode_scanned``.

    Why so narrow: the existing scanner path (header's BarcodeLineEdit
    → ``barcode_scanned`` signal → ``MainWindow._barcode``) works fine
    on every page EXCEPT the Matrix tab, because every other page
    leaves the header search bar in the natural focus chain. The Matrix
    tab is the one place that transfers focus to its table widget on
    activation, and ``MatrixWidget.keyPressEvent`` only handles Ctrl+D
    fill-down — it discards every other key, including scanner bursts.

    An earlier v2.5.6 attempt cast a wider net (intercept any non-text-
    input focused widget), which broke the popup on every page because
    BarcodeLineEdit never got a chance to receive its keystrokes. This
    version is intentionally minimal: it engages ONLY when the focused
    widget is the matrix-specific ``MatrixWidget`` class, so all other
    tabs keep their existing scanner routing untouched.

    Detection is timing-based: scanner output arrives in tight bursts
    (every char within ~10-30 ms), human typing is ~80 ms+. We
    accumulate printable characters; the buffer flushes after
    ``interval_ms`` of no new keys OR on Enter/Return. A flush emits
    iff the buffer is at least ``min_length`` chars (filters incidental
    fast typing).

    Install ONCE per app, on the QApplication instance:

        capture = GlobalScannerCapture()
        QApplication.instance().installEventFilter(capture)
        capture.barcode_scanned.connect(main_window._barcode)
    """
    barcode_scanned = pyqtSignal(str)

    def __init__(self, interval_ms: int = 80, min_length: int = 4,
                 parent: QObject | None = None):
        super().__init__(parent)
        self._interval_ns = interval_ms * 1_000_000  # monotonic_ns is ns
        self._min_length = min_length
        self._buf: list[str] = []
        self._last_press_ns: int = 0
        self._flush_timer = QTimer(self)
        self._flush_timer.setSingleShot(True)
        self._flush_timer.setInterval(interval_ms)
        self._flush_timer.timeout.connect(self._flush)

    def eventFilter(self, obj, event):  # noqa: N802 (Qt API)
        # Only key-press events carry scanner input; everything else
        # passes through untouched.
        if event.type() != QEvent.Type.KeyPress:
            return False

        # NARROW ENGAGEMENT: only intercept when the focused widget is
        # specifically a Matrix table. Every other page in the app —
        # Inventory, Transactions, Sales, Quick Scan, etc. — already
        # delivers scanner keystrokes to the header's ``BarcodeLineEdit``
        # through Qt's normal focus chain, which is how the scan-action
        # popup and command routing have always worked. The Matrix tab
        # is the ONE place that steals focus to its table and swallows
        # scans (the table's ``keyPressEvent`` only handles Ctrl+D
        # fill-down and discards everything else).
        #
        # A wider net here — intercepting whenever the focused widget
        # is non-text-input — broke the popup on every page in a
        # v2.5.6 dev build: BarcodeLineEdit's own ``keyPressEvent``
        # never got a chance to fire because this filter consumed the
        # keystrokes first. Lesson: don't generalise focus-stealing
        # detection beyond the specific widget that's known to steal.
        focused = QApplication.focusWidget()
        try:
            from app.ui.components.matrix_widget import MatrixWidget
        except ImportError:
            return False
        if not isinstance(focused, MatrixWidget):
            return False

        text = event.text()
        if not text or not text.isprintable():
            # Modifier keys (Shift/Ctrl/Alt), function keys, arrows —
            # ignore. Enter / Return are NOT isprintable so the Enter
            # check below has to be explicit BEFORE the printable test.
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                # Burst terminator (most scanners append CR). Flush
                # whatever we have NOW rather than waiting for the
                # timer — and swallow the Enter so it doesn't trigger
                # a default-button click on the focused window.
                if self._buf:
                    self._flush()
                    return True
            return False

        now = time.monotonic_ns()
        if self._last_press_ns and (now - self._last_press_ns) > self._interval_ns:
            # Gap too wide for a scanner burst — discard the partial
            # buffer (it was probably human typing that never amounted
            # to a barcode-length string) and start a fresh capture
            # with the current char.
            self._buf.clear()
        self._buf.append(text)
        self._last_press_ns = now
        self._flush_timer.start()
        # Swallow the event so the underlying focused widget doesn't
        # also receive the keystroke — otherwise a Matrix-tab scan
        # would type garbage into the table's current cell.
        return True

    def _flush(self) -> None:
        if not self._buf:
            return
        bc = "".join(self._buf).strip()
        self._buf.clear()
        self._last_press_ns = 0
        if len(bc) >= self._min_length:
            self.barcode_scanned.emit(bc)
