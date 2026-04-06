"""
app/ui/components/barcode_line_edit.py — Barcode-aware search input.
"""
from __future__ import annotations

from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

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
