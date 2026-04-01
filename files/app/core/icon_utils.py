"""
Icon utilities for loading and displaying SVG icons.
Supports recoloring for dark/light themes.
"""
import os
import sys
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QImage


def _icon_path(name: str) -> str:
    """Resolve icon path whether running from source or PyInstaller bundle."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    return os.path.join(base, "img", name)


def load_svg_icon(icon_path: str, size: int = 16) -> str:
    """Return emoji for display. If icon_path is already an emoji, return it directly."""
    if not icon_path:
        return "📁"
    # If it's not an SVG path (no / or .svg), it's already an emoji
    if "/" not in icon_path and ".svg" not in icon_path:
        return icon_path
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


def _recolor_icon(icon: QIcon, color: QColor, size: int = 24) -> QIcon:
    """Recolor a QIcon by painting it with the given color.

    Works by converting to pixmap, then using CompositionMode_SourceIn
    to replace all non-transparent pixels with the target color.
    """
    px = icon.pixmap(size, size)
    if px.isNull():
        return icon

    # Create a colored overlay
    img = px.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    overlay = QImage(img.size(), QImage.Format.Format_ARGB32)
    overlay.fill(color)

    # Use SourceIn composition: keep alpha from original, RGB from overlay
    p = QPainter(img)
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    p.drawImage(0, 0, overlay)
    p.end()

    return QIcon(QPixmap.fromImage(img))


def get_qicon(icon_path: str) -> QIcon:
    """Load an SVG icon as QIcon."""
    try:
        full_path = _icon_path(icon_path)
        if os.path.exists(full_path):
            return QIcon(full_path)
        return QIcon()
    except Exception:
        return QIcon()


def get_button_icon(icon_name: str) -> QIcon:
    """Get QIcon for common buttons, recolored for current theme."""
    from app.core.theme import THEME

    icon_map = {
        "refresh": "icons/update_sync_reload_reset_icon_229508.svg",
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
    if not icon_path:
        return QIcon()

    icon = get_qicon(icon_path)
    if icon.isNull():
        return icon

    # Recolor to theme text color so icons are visible in both dark and light
    tk = THEME.tokens
    color = QColor(tk.t2)  # secondary text color — visible on both themes
    return _recolor_icon(icon, color)
