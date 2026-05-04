#!/usr/bin/env python3
"""Generate skaz brand assets from custom SVG logos.

Inputs:
- assets/skaz-logo-default.svg   — square with S cutout (idle state)
- assets/skaz-logo-recording.svg — circle with S cutout (recording state)

Outputs:
- assets/logo.png (1024)         — README header / social
- assets/logo-mark.png (256)     — inline / smaller
- assets/menu-bar/idle.png       — menu bar icon, idle (template, padded, rounded)
- assets/menu-bar/idle@2x.png    — retina
- assets/menu-bar/recording.png
- assets/menu-bar/recording@2x.png
- assets/icon.iconset/           — macOS iconset PNGs (full square, no padding)
- assets/icon.icns               — compiled iconset

Run:
    .venv/bin/python scripts/build_logo.py
"""
from __future__ import annotations

import io
import shutil
import subprocess
from pathlib import Path

import cairosvg
from PIL import Image, ImageChops, ImageDraw

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = REPO_ROOT / "assets"
ICONSET_DIR = ASSETS_DIR / "icon.iconset"
MENU_BAR_DIR = ASSETS_DIR / "menu-bar"

DEFAULT_SVG = ASSETS_DIR / "skaz-logo-default.svg"
RECORDING_SVG = ASSETS_DIR / "skaz-logo-recording.svg"

# Menu bar tuning. 22pt is the macOS status item slot height. Content at 18pt
# gives ~82% fill — visible but not overpowering. Subtle rounding on the
# square so it reads as a card, not a wall of color. Recording variant is a
# circle, no rounding needed.
MB_CANVAS = 22
MB_CONTENT = 18
MB_CORNER_RATIO = 0.15
MB_SCALE = 2  # @2x retina


def rasterize(svg_path: Path, size: int) -> Image.Image:
    png_bytes = cairosvg.svg2png(
        url=str(svg_path), output_width=size, output_height=size
    )
    return Image.open(io.BytesIO(png_bytes)).convert("RGBA")


def round_corners(img: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, img.size[0] - 1, img.size[1] - 1), radius=radius, fill=255
    )
    existing_alpha = img.split()[3]
    new_alpha = ImageChops.multiply(existing_alpha, mask)
    out = img.copy()
    out.putalpha(new_alpha)
    return out


def render_menu_bar_icon(svg_path: Path, out_path: Path, canvas: int, content: int, rounded: bool) -> None:
    inner = rasterize(svg_path, content)
    if rounded:
        inner = round_corners(inner, max(2, int(content * MB_CORNER_RATIO)))
    canvas_img = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    offset = ((canvas - content) // 2, (canvas - content) // 2)
    canvas_img.paste(inner, offset, inner)
    canvas_img.save(out_path)


def build_iconset() -> None:
    if ICONSET_DIR.exists():
        shutil.rmtree(ICONSET_DIR)
    ICONSET_DIR.mkdir(parents=True)
    pairs = [(16, 32), (32, 64), (128, 256), (256, 512), (512, 1024)]
    for base, hi in pairs:
        rasterize(DEFAULT_SVG, base).save(ICONSET_DIR / f"icon_{base}x{base}.png")
        rasterize(DEFAULT_SVG, hi).save(ICONSET_DIR / f"icon_{base}x{base}@2x.png")


def build_icns() -> None:
    icns_path = ASSETS_DIR / "icon.icns"
    subprocess.run(
        ["iconutil", "-c", "icns", "-o", str(icns_path), str(ICONSET_DIR)],
        check=True,
    )


def build_logo_pngs() -> None:
    rasterize(DEFAULT_SVG, 1024).save(ASSETS_DIR / "logo.png")
    rasterize(DEFAULT_SVG, 256).save(ASSETS_DIR / "logo-mark.png")


def build_menu_bar() -> None:
    MENU_BAR_DIR.mkdir(parents=True, exist_ok=True)
    render_menu_bar_icon(DEFAULT_SVG, MENU_BAR_DIR / "idle.png", MB_CANVAS, MB_CONTENT, rounded=True)
    render_menu_bar_icon(
        DEFAULT_SVG,
        MENU_BAR_DIR / "idle@2x.png",
        MB_CANVAS * MB_SCALE,
        MB_CONTENT * MB_SCALE,
        rounded=True,
    )
    render_menu_bar_icon(RECORDING_SVG, MENU_BAR_DIR / "recording.png", MB_CANVAS, MB_CONTENT, rounded=False)
    render_menu_bar_icon(
        RECORDING_SVG,
        MENU_BAR_DIR / "recording@2x.png",
        MB_CANVAS * MB_SCALE,
        MB_CONTENT * MB_SCALE,
        rounded=False,
    )


def main() -> None:
    if not DEFAULT_SVG.exists() or not RECORDING_SVG.exists():
        raise SystemExit(f"missing source SVGs in {ASSETS_DIR}")
    print("rendering iconset…")
    build_iconset()
    print("compiling icns…")
    build_icns()
    print("rendering logo PNGs…")
    build_logo_pngs()
    print("rendering menu-bar icons…")
    build_menu_bar()
    print(f"done → {ASSETS_DIR}")


if __name__ == "__main__":
    main()
