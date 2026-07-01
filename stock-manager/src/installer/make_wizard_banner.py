"""
make_wizard_banner.py — Generate the Inno Setup wizard images from the app icon,
stamped with the current version, so the installer never shows a stale version.

Run at release time (CI) or locally:
    python make_wizard_banner.py [VERSION]

If VERSION is omitted it is read from app/core/version.py (APP_VERSION).
Outputs (BMP, as Inno Setup requires):
    assets/wizard_banner.bmp   164x314  WizardImageFile      (left sidebar)
    assets/wizard_icon.bmp      55x58   WizardSmallImageFile (inner-page corner)
"""
from __future__ import annotations

import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ICON = os.path.normpath(os.path.join(
    HERE, "..", "files", "img", "icon_cube_256.png"))
ASSETS = os.path.join(HERE, "assets")

BG = (20, 20, 20)          # #141414 — app dark background
EMERALD = (16, 185, 129)   # #10B981 — app accent
WHITE = (238, 238, 238)
GREY = (150, 150, 150)


def _version() -> str:
    if len(sys.argv) > 1 and sys.argv[1].strip():
        return sys.argv[1].strip().lstrip("v")
    vpy = os.path.normpath(os.path.join(
        HERE, "..", "files", "app", "core", "version.py"))
    with open(vpy, encoding="utf-8") as f:
        m = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', f.read())
    return m.group(1) if m else "0.0.0"


def _font(size: int, bold: bool = False):
    candidates = (
        ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
        if bold else
        ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    )
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _center(draw, text, font, y, cx, fill):
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    draw.text((cx - (r - l) / 2, y), text, font=font, fill=fill)
    return b - t


def make_banner(version: str) -> None:
    W, H = 164, 314
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # Slim emerald accent stripe down the left edge (matches app chrome).
    d.rectangle([0, 0, 3, H], fill=EMERALD)

    # App icon, centred near the top.
    icon = Image.open(ICON).convert("RGBA").resize((88, 88), Image.LANCZOS)
    img.paste(icon, ((W - 88) // 2, 46), icon)

    cx = W // 2
    _center(d, "Stock Manager", _font(15, bold=True), 152, cx, WHITE)
    _center(d, "Pro", _font(15, bold=True), 172, cx, EMERALD)
    _center(d, f"v{version}", _font(12), 200, cx, GREY)

    img.save(os.path.join(ASSETS, "wizard_banner.bmp"), "BMP")


def make_small_icon() -> None:
    W, H = 55, 58
    img = Image.new("RGB", (W, H), BG)
    icon = Image.open(ICON).convert("RGBA").resize((44, 44), Image.LANCZOS)
    img.paste(icon, ((W - 44) // 2, (H - 44) // 2), icon)
    img.save(os.path.join(ASSETS, "wizard_icon.bmp"), "BMP")


def main() -> None:
    v = _version()
    os.makedirs(ASSETS, exist_ok=True)
    make_banner(v)
    make_small_icon()
    print(f"Wizard images generated for v{v}")


if __name__ == "__main__":
    main()
