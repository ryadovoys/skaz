#!/usr/bin/env python3
"""Generate skaz brand assets: white square with serif S in Playfair Display.

Outputs:
- assets/logo.png (1024) — README header / social, with rounded corners
- assets/logo-mark.png (256) — inline / smaller, with rounded corners
- assets/icon.iconset/ — PNGs at standard macOS sizes (square, no rounding;
  macOS applies its own mask)
- assets/icon.icns — compiled iconset

Run from repo root:
    .venv/bin/python scripts/build_logo.py
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = REPO_ROOT / "assets"
ICONSET_DIR = ASSETS_DIR / "icon.iconset"
FONT_PATH = ASSETS_DIR / "fonts" / "PlayfairDisplay-Bold.ttf"
WEIGHT = 900  # Playfair has wght axis 400-900; 900 = Black for strongest mark


def _make_font(font_size: int) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(FONT_PATH), font_size)
    # Variable font: set weight axis if supported
    try:
        font.set_variation_by_axes([WEIGHT])
    except Exception:
        pass
    return font


def render_square(size: int, rounded: bool = False) -> Image.Image:
    """White square with black slab-serif S centered.

    If rounded=True, return RGBA with rounded corners (radius ~= size/8).
    Otherwise return RGB pure square.
    """
    if rounded:
        radius = max(int(size * 0.18), 4)
        # Build mask + image
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, size - 1, size - 1), radius=radius, fill=255
        )
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        white_layer = Image.new("RGBA", (size, size), (255, 255, 255, 255))
        img.paste(white_layer, (0, 0), mask)
    else:
        img = Image.new("RGB", (size, size), "white")

    draw = ImageDraw.Draw(img)
    font_size = int(size * 0.72)
    font = _make_font(font_size)
    text = "S"
    bbox = font.getbbox(text)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) / 2 - bbox[0]
    y = (size - text_h) / 2 - bbox[1]
    draw.text((x, y), text, fill="black", font=font)
    return img


def build_iconset() -> None:
    if ICONSET_DIR.exists():
        shutil.rmtree(ICONSET_DIR)
    ICONSET_DIR.mkdir(parents=True)
    pairs = [(16, 32), (32, 64), (128, 256), (256, 512), (512, 1024)]
    for base, hi in pairs:
        # iconset: pure square, macOS applies its own rounded mask
        render_square(base, rounded=False).save(ICONSET_DIR / f"icon_{base}x{base}.png")
        render_square(hi, rounded=False).save(ICONSET_DIR / f"icon_{base}x{base}@2x.png")


def build_icns() -> None:
    icns_path = ASSETS_DIR / "icon.icns"
    subprocess.run(
        ["iconutil", "-c", "icns", "-o", str(icns_path), str(ICONSET_DIR)],
        check=True,
    )


def build_logo_pngs() -> None:
    # Standalone logos use rounded corners so the white square is a visible
    # object even on white-background pages.
    render_square(1024, rounded=True).save(ASSETS_DIR / "logo.png")
    render_square(256, rounded=True).save(ASSETS_DIR / "logo-mark.png")


def main() -> None:
    if not FONT_PATH.exists():
        raise SystemExit(f"missing font: {FONT_PATH}")
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    print("rendering iconset…")
    build_iconset()
    print("compiling icns…")
    build_icns()
    print("rendering logo PNGs…")
    build_logo_pngs()
    print(f"done → {ASSETS_DIR}")


if __name__ == "__main__":
    main()
