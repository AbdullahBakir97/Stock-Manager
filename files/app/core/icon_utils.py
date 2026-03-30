"""
Icon utilities for loading and displaying SVG icons.
"""
import os
import sys
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QStyle
from PyQt6.QtCore import Qt


def _icon_path(name: str) -> str:
    """Resolve icon path whether running from source or PyInstaller bundle."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    return os.path.join(base, "img", name)


def load_svg_icon(icon_path: str, size: int = 16) -> str:
    """
    Load an SVG icon and return it as a Unicode character or emoji for display.
    If the SVG cannot be loaded, returns a fallback emoji.
    """
    try:
        full_path = _icon_path(icon_path)
        if os.path.exists(full_path):
            # For now, return a simple emoji fallback since SVG rendering in tabs is complex
            # This can be enhanced later to properly render SVG icons
            icon_map = {
                "icons/chart_icon_184274.svg": "📊",
                "icons/plus_icon_184263.svg": "🔋", 
                "icons/edit_square_icon_184295.svg": "📱",
                "icons/graph_icon_184279.svg": "📷",
                "icons/refresh_paper_load_update_icon_141966.svg": "⚡",
                "icons/close_square_icon_184289.svg": "🔲",
                "icons/delete_icon_184291.svg": "🗑️",
                "icons/search_icon_184335.svg": "🔍",
                "icons/setting_icon_184259.svg": "⚙️",
                "icons/filter_icon_184287.svg": "🔽",
                "icons/arrow_up_icon_184240.svg": "⬆️",
                "icons/arrow_down_icon_184268.svg": "⬇️",
            }
            return icon_map.get(icon_path, "📁")
        else:
            return "📁"
    except Exception:
        return "📁"


def get_qicon(icon_path: str) -> QIcon:
    """Load an SVG icon as QIcon for use in buttons, menus, etc."""
    try:
        full_path = _icon_path(icon_path)
        if os.path.exists(full_path):
            return QIcon(full_path)
        else:
            return QIcon()
    except Exception:
        return QIcon()


def get_button_icon(icon_name: str) -> QIcon:
    """Get appropriate QIcon for common button types."""
    icon_map = {
        "refresh": "icons/refresh_paper_load_update_icon_141966.svg",
        "edit": "icons/edit_square_icon_184295.svg", 
        "delete": "icons/delete_icon_184291.svg",
        "search": "icons/search_icon_184335.svg",
        "settings": "icons/setting_icon_184259.svg",
        "filter": "icons/filter_icon_184287.svg",
        "add": "icons/plus_icon_184263.svg",
        "up": "icons/arrow_up_icon_184240.svg",
        "down": "icons/arrow_down_icon_184268.svg",
    }
    icon_path = icon_map.get(icon_name)
    return get_qicon(icon_path) if icon_path else QIcon()
