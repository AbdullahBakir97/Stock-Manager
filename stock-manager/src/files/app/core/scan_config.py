"""app/core/scan_config.py — Command + color barcode configuration for Quick Scan."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from app.core.database import get_connection


# Default color barcodes
_DEFAULT_COLORS = {
    "Black":  "CLR-BLACK",
    "Blue":   "CLR-BLUE",
    "Silver": "CLR-SILVER",
    "Gold":   "CLR-GOLD",
    "Green":  "CLR-GREEN",
    "Purple": "CLR-PURPLE",
    "White":  "CLR-WHITE",
}


@dataclass
class ScanConfig:
    cmd_takeout: str = "CMD-TAKEOUT"
    cmd_insert:  str = "CMD-INSERT"
    cmd_confirm: str = "CMD-CONFIRM"
    # Color barcodes: color_name → barcode_text
    color_barcodes: dict[str, str] = field(default_factory=lambda: dict(_DEFAULT_COLORS))

    _KEYS = ("scan_cmd_takeout", "scan_cmd_insert", "scan_cmd_confirm")
    _FIELDS = ("cmd_takeout", "cmd_insert", "cmd_confirm")

    _instance: Optional["ScanConfig"] = None

    @classmethod
    def get(cls) -> "ScanConfig":
        if cls._instance is None:
            cls._instance = cls.load()
        return cls._instance

    @classmethod
    def invalidate(cls) -> None:
        cls._instance = None

    @classmethod
    def load(cls) -> "ScanConfig":
        cfg = cls()
        try:
            with get_connection() as conn:
                rows = conn.execute(
                    "SELECT key, value FROM app_config WHERE key LIKE 'scan_%'",
                ).fetchall()
                key_map = dict(zip(cls._KEYS, cls._FIELDS))
                for r in rows:
                    field_name = key_map.get(r["key"])
                    if field_name and r["value"]:
                        setattr(cfg, field_name, r["value"])
                    elif r["key"].startswith("scan_clr_") and r["value"]:
                        # Color barcode: scan_clr_Black → CLR-BLACK
                        color_name = r["key"][9:]  # strip "scan_clr_"
                        cfg.color_barcodes[color_name] = r["value"]
        except Exception:
            pass
        return cfg

    def save(self) -> None:
        with get_connection() as conn:
            for db_key, field_name in zip(self._KEYS, self._FIELDS):
                conn.execute(
                    "INSERT OR REPLACE INTO app_config (key, value) VALUES (?,?)",
                    (db_key, getattr(self, field_name)),
                )
            # Save color barcodes
            for color_name, barcode in self.color_barcodes.items():
                conn.execute(
                    "INSERT OR REPLACE INTO app_config (key, value) VALUES (?,?)",
                    (f"scan_clr_{color_name}", barcode),
                )
        ScanConfig.invalidate()

    @staticmethod
    def _norm(text: str) -> str:
        """Strip the scanner-mark prefix so comparisons survive scanner /
        renderer changes. Same logic as the inventory barcode lookup —
        see ``normalize_barcode`` in app/services/barcode_gen_service.py.
        Inlined as a staticmethod to avoid a circular import.
        """
        if not text or len(text) < 2:
            return text or ""
        if text[0].islower() and text[0].isascii() and text[0].isalpha():
            nxt = text[1]
            if nxt.isupper() or nxt.isdigit():
                return text[1:]
        return text

    def is_command(self, barcode: str) -> bool:
        bc = self._norm(barcode)
        return bc in (self._norm(self.cmd_takeout),
                      self._norm(self.cmd_insert),
                      self._norm(self.cmd_confirm))

    def command_type(self, barcode: str) -> Optional[str]:
        bc = self._norm(barcode)
        if bc == self._norm(self.cmd_takeout): return "TAKEOUT"
        if bc == self._norm(self.cmd_insert):  return "INSERT"
        if bc == self._norm(self.cmd_confirm): return "CONFIRM"
        return None

    def is_color_barcode(self, barcode: str) -> bool:
        """Check if barcode matches any configured color."""
        bc = self._norm(barcode)
        return bc in {self._norm(v) for v in self.color_barcodes.values()}

    def color_name(self, barcode: str) -> Optional[str]:
        """Return the color name for a color barcode, or None."""
        bc = self._norm(barcode)
        for name, stored in self.color_barcodes.items():
            if self._norm(stored) == bc:
                return name
        return None
