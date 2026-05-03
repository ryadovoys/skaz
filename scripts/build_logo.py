#!/usr/bin/env python3
"""Generate skaz brand assets from custom SVG logos.

Inputs:
- assets/skaz-logo-default.svg   — square with S cutout (idle state)
- assets/skaz-logo-recording.svg — circle with S cutout (recording state)

Outputs:
- assets/logo.png (1024)         — README header / social
- assets/logo-mark.png (256)     — inline / smaller
- assets/menu-bar/idle.png       — menu bar icon, idle (template image)
- assets/menu-bar/idle@2x.png    — retina
- assets/menu-bar/recording.png
- assets/menu-bar/recording@2x.png
- assets/icon.iconset/           — macOS iconset PNGs
- assets/icon.icns               — compiled iconset

Run:
    .venv/bin/python scripts/build_logo.py
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import cairosvg

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = REPO_ROOT / "assets"
ICONSET_DIR = ASSETS_DIR / "icon.iconset"
MENU_BAR_DIR = ASSETS_DIR / "menu-bar"

DEFAULT_SVG = ASSETS_DIR / "skaz-logo-default.svg"
RECORDING_SVG = ASSETS_DIR / "skaz-logo-recording.svg"


def rasterize(svg_path: Path, out_path: Path, size: int) -> None:
    cairosvg.svg2png(
        url=str(svg_path),
        write_to=str(out_path),
        output_width=size,
        output_height=size,
    )


def build_iconset() -> None:
    if ICONSET_DIR.exists():
        shutil.rmtree(ICONSET_DIR)
    ICONSET_DIR.mkdir(parents=True)
    pairs = [(16, 32), (32, 64), (128, 256), (256, 512), (512, 1024)]
    for base, hi in pairs:
        rasterize(DEFAULT_SVG, ICONSET_DIR / f"icon_{base}x{base}.png", base)
        rasterize(DEFAULT_SVG, ICONSET_DIR / f"icon_{base}x{base}@2x.png", hi)


def build_icns() -> None:
    icns_path = ASSETS_DIR / "icon.icns"
    subprocess.run(
        ["iconutil", "-c", "icns", "-o", str(icns_path), str(ICONSET_DIR)],
        check=True,
    )


def build_logo_pngs() -> None:
    rasterize(DEFAULT_SVG, ASSETS_DIR / "logo.png", 1024)
    rasterize(DEFAULT_SVG, ASSETS_DIR / "logo-mark.png", 256)


def build_menu_bar() -> None:
    MENU_BAR_DIR.mkdir(parents=True, exist_ok=True)
    # macOS menu bar icons are ~22pt (44px @2x)
    rasterize(DEFAULT_SVG, MENU_BAR_DIR / "idle.png", 22)
    rasterize(DEFAULT_SVG, MENU_BAR_DIR / "idle@2x.png", 44)
    rasterize(RECORDING_SVG, MENU_BAR_DIR / "recording.png", 22)
    rasterize(RECORDING_SVG, MENU_BAR_DIR / "recording@2x.png", 44)


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
