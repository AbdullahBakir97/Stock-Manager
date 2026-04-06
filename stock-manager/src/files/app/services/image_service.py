"""app/services/image_service.py — Product image storage and retrieval."""
from __future__ import annotations

import os
import sys
import shutil
from pathlib import Path
from typing import Optional

from app.core.logger import get_logger

_log = get_logger(__name__)

# ── Image storage folder ────────────────────────────────────────────────────

def _images_dir() -> Path:
    """Return the directory for storing product images."""
    if getattr(sys, "frozen", False):
        try:
            from platformdirs import user_data_dir
            base = user_data_dir("StockManagerPro", "StockPro")
        except ImportError:
            base = os.path.join(
                os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                "StockPro", "StockManagerPro",
            )
    else:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    img_dir = Path(base) / "product_images"
    img_dir.mkdir(parents=True, exist_ok=True)
    return img_dir


IMAGES_DIR = _images_dir()


class ImageService:
    """Copy product images to app storage and return relative paths."""

    def save_image(self, source_path: str, item_id: int) -> str:
        """Copy an image file to storage. Returns the stored filename."""
        src = Path(source_path)
        if not src.exists():
            raise FileNotFoundError(f"Image not found: {source_path}")

        ext = src.suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".bmp"):
            raise ValueError(f"Unsupported image format: {ext}")

        # Resize large images to save space
        dest_name = f"item_{item_id}{ext}"
        dest_path = IMAGES_DIR / dest_name

        try:
            from PIL import Image
            img = Image.open(source_path)
            # Resize if larger than 800x800
            max_size = (800, 800)
            if img.width > max_size[0] or img.height > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
            # Convert to RGB if RGBA (for JPEG compat)
            if img.mode == "RGBA" and ext in (".jpg", ".jpeg"):
                img = img.convert("RGB")
            img.save(str(dest_path), quality=85, optimize=True)
        except ImportError:
            # Fallback: simple copy if Pillow unavailable
            shutil.copy2(str(src), str(dest_path))

        _log.info(f"Saved product image: {dest_name}")
        return dest_name

    def get_image_path(self, filename: str) -> Optional[str]:
        """Return full path to a stored image, or None if missing."""
        if not filename:
            return None
        path = IMAGES_DIR / filename
        return str(path) if path.exists() else None

    def delete_image(self, filename: str) -> None:
        """Delete a stored product image."""
        if not filename:
            return
        path = IMAGES_DIR / filename
        if path.exists():
            path.unlink()
            _log.info(f"Deleted product image: {filename}")
