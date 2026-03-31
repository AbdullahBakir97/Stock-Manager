"""app/core/scan_config.py — Command barcode configuration for Quick Scan."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from app.core.database import get_connection


@dataclass
class ScanConfig:
    cmd_takeout: str = "CMD-TAKEOUT"
    cmd_insert:  str = "CMD-INSERT"
    cmd_confirm: str = "CMD-CONFIRM"

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
                    "SELECT key, value FROM app_config WHERE key IN (?,?,?)",
                    cls._KEYS,
                ).fetchall()
                key_map = dict(zip(cls._KEYS, cls._FIELDS))
                for r in rows:
                    field = key_map.get(r["key"])
                    if field and r["value"]:
                        setattr(cfg, field, r["value"])
        except Exception:
            pass
        return cfg

    def save(self) -> None:
        with get_connection() as conn:
            for db_key, field in zip(self._KEYS, self._FIELDS):
                conn.execute(
                    "INSERT OR REPLACE INTO app_config (key, value) VALUES (?,?)",
                    (db_key, getattr(self, field)),
                )
        ScanConfig.invalidate()

    def is_command(self, barcode: str) -> bool:
        return barcode in (self.cmd_takeout, self.cmd_insert, self.cmd_confirm)

    def command_type(self, barcode: str) -> Optional[str]:
        if barcode == self.cmd_takeout: return "TAKEOUT"
        if barcode == self.cmd_insert:  return "INSERT"
        if barcode == self.cmd_confirm: return "CONFIRM"
        return None
