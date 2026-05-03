#!/usr/bin/env python3
"""Generate skaz brand assets: white square with slab-serif S.

Outputs:
- assets/logo.png (1024x1024) — for README header and social preview
- assets/icon.iconset/ — macOS iconset folder (PNGs at all required sizes)
- assets/icon.icns — compiled icns for SkazMenu.app

Run from the repo root:
    .venv/bin/python scripts/build_logo.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = REPO_ROOT / "assets"
ICONSET_DIR = ASSETS_DIR / "icon.iconset"

# Rockwell on macOS is the classic slab serif. Bold for stronger letterform.
FONT_PATH = "/System/Library/Fonts/Supplemental/Rockwell.ttc"
FONT_INDEX_BOLD = 2  # macOS Rockwell.ttc: 0=Regular, 1=Italic, 2=Bold, 3=Bold Italic


def render_logo(size: int, square_fill="white", text_fill="black") -> Image.Image:
    img = Image.new("RGB", (size, size), square_fill)
    draw = ImageDraw.Draw(img)
    # Letter occupies ~62% of square height visually for clean breathing room
    font_size = int(size * 0.78)
    try:
        font = ImageFont.truetype(FONT_PATH, font_size, index=FONT_INDEX_BOLD)
    except OSError:
        font = ImageFont.truetype(FONT_PATH, font_size)
    text = "S"
    bbox = font.getbbox(text)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) / 2 - bbox[0]
    y = (size - text_h) / 2 - bbox[1]
    draw.text((x, y), text, fill=text_fill, font=font)
    return img


def build_iconset() -> None:
    if ICONSET_DIR.exists():
        shutil.rmtree(ICONSET_DIR)
    ICONSET_DIR.mkdir(parents=True)

    # macOS iconset spec: pairs of @1x and @2x at standard sizes
    pairs = [(16, 32), (32, 64), (128, 256), (256, 512), (512, 1024)]
    for base, hi in pairs:
        render_logo(base).save(ICONSET_DIR / f"icon_{base}x{base}.png")
        render_logo(hi).save(ICONSET_DIR / f"icon_{base}x{base}@2x.png")


def build_icns() -> None:
    icns_path = ASSETS_DIR / "icon.icns"
    subprocess.run(
        ["iconutil", "-c", "icns", "-o", str(icns_path), str(ICONSET_DIR)],
        check=True,
    )


def build_logo_png() -> None:
    render_logo(1024).save(ASSETS_DIR / "logo.png")
    render_logo(256).save(ASSETS_DIR / "logo-mark.png")


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    print("rendering iconset…")
    build_iconset()
    print("compiling icns…")
    build_icns()
    print("rendering logo PNGs…")
    build_logo_png()
    print(f"done → {ASSETS_DIR}")


if __name__ == "__main__":
    main()
