"""app/core/config.py — Shop configuration stored in app_config DB table."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from app.core.database import get_connection


@dataclass
class ShopConfig:
    name:              str = "Stock Manager Pro"
    currency:          str = "€"
    currency_position: str = "prefix"   # "prefix" | "suffix"
    default_language:  str = "EN"
    theme:             str = "pro_dark"  # "pro_dark" | "pro_light" | "dark" | "light"
    logo_path:         str = ""
    admin_pin:         str = ""         # empty = no PIN gate
    contact_info:      str = ""
    # Auto-backup settings (stored as strings in app_config)
    auto_backup_enabled:        str = "0"   # "1" = enabled, "0" = disabled
    auto_backup_interval_hours: str = "24"  # interval in hours (string for DB)
    auto_backup_retain:         str = "10"  # how many backups to keep
    auto_backup_dir:            str = ""    # empty = use default backups/ folder
    # Auto-update settings
    update_auto_check:          str = "1"   # "1" = check on startup, "0" = manual only
    # UI — persistent table zoom level (50-200%, footer slider)
    zoom_level:                 str = "100"
    # UI — whole-app size preset (admin setting, requires restart)
    # Values: "small" | "normal" | "large" | "xlarge"
    ui_scale:                   str = "normal"
    # UI — show/hide "sell total" (stock × sell-price) displays in the
    # matrix tabs. Owners who don't want a shop assistant to see the
    # valuation turn this off. Default "1" = shown (backward compatible).
    # Affects: TOTAL column in matrix table · per-part-type card value ·
    # grand-total card at the end of the cards strip.
    show_sell_totals:           str = "1"
    show_color_totals:          str = "1"

    _KEYS = (
        "name", "currency", "currency_position", "default_language",
        "theme", "logo_path", "admin_pin", "contact_info",
        "auto_backup_enabled", "auto_backup_interval_hours",
        "auto_backup_retain", "auto_backup_dir",
        "update_auto_check",
        "zoom_level",
        "ui_scale",
        "show_sell_totals",
        "show_color_totals",
    )

    # ── Typed accessors for auto-backup ──────────────────────────────────────

    @property
    def is_auto_backup_enabled(self) -> bool:
        return self.auto_backup_enabled == "1"

    @property
    def auto_backup_interval_hours_int(self) -> int:
        try:
            return max(1, int(self.auto_backup_interval_hours))
        except (ValueError, TypeError):
            return 24

    @property
    def auto_backup_retain_int(self) -> int:
        try:
            return max(1, int(self.auto_backup_retain))
        except (ValueError, TypeError):
            return 10

    @property
    def is_update_auto_check_enabled(self) -> bool:
        return self.update_auto_check != "0"

    @property
    def zoom_level_int(self) -> int:
        """Parsed zoom percentage, clamped to 50–200."""
        try:
            v = int(self.zoom_level)
        except (ValueError, TypeError):
            return 100
        return max(50, min(200, v))

    @property
    def is_show_sell_totals(self) -> bool:
        """Typed accessor — is the matrix 'sell total' display enabled?"""
        return (self.show_sell_totals or "1") != "0"

    @property
    def is_show_color_totals(self) -> bool:
        return (self.show_color_totals or "1") != "0"

    @property
    def ui_scale_factor(self) -> float:
        """UI scale factor mapped from preset name to float multiplier.

        Requires app restart to take effect. Affects sidebar width,
        header height, footer height, and application base font size.
        """
        return {
            "small":  0.85,
            "normal": 1.00,
            "large":  1.15,
            "xlarge": 1.30,
        }.get((self.ui_scale or "normal").lower(), 1.0)

    _instance: Optional["ShopConfig"] = None

    @classmethod
    def get(cls) -> "ShopConfig":
        """Return cached instance, loading from DB on first call."""
        if cls._instance is None:
            cls._instance = cls.load()
        return cls._instance

    @classmethod
    def invalidate(cls) -> None:
        """Force reload on next get() call (call after save())."""
        cls._instance = None

    @classmethod
    def load(cls) -> "ShopConfig":
        cfg = cls()
        try:
            placeholders = ",".join("?" * len(cls._KEYS))
            with get_connection() as conn:
                rows = conn.execute(
                    f"SELECT key, value FROM app_config WHERE key IN ({placeholders})",
                    cls._KEYS,
                ).fetchall()
                for r in rows:
                    if hasattr(cfg, r["key"]):
                        setattr(cfg, r["key"], r["value"])
        except Exception:
            pass
        return cfg

    def save(self) -> None:
        with get_connection() as conn:
            for k in self._KEYS:
                conn.execute(
                    "INSERT OR REPLACE INTO app_config (key, value) VALUES (?,?)",
                    (k, getattr(self, k)),
                )

    def format_currency(self, amount) -> str:
        """Format a numeric amount with the shop currency symbol.

        Always renders with exactly 2 decimals and a thousands separator
        so floating-point artefacts like 160.92999999999998 never leak
        into the UI. Non-numeric input is stringified as-is (legacy
        behaviour — some callers pass pre-formatted strings).
        """
        try:
            v = float(amount)
            s = f"{v:,.2f}"
        except (TypeError, ValueError):
            s = str(amount)
        if self.currency_position == "suffix":
            return f"{s} {self.currency}"
        return f"{self.currency}{s}"
