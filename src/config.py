"""skaz user-level configuration.

Reads JSON from ~/.config/skaz/config.json. Created at install time.
Falls back to defaults if missing so the code never crashes outright.
"""
from __future__ import annotations

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "skaz"
CONFIG_FILE = CONFIG_DIR / "config.json"
CONTROL_FILE = CONFIG_DIR / "control"
PID_FILE = CONFIG_DIR / "menu.pid"

DEFAULT_SESSIONS_DIR = Path.home() / "Documents" / "skaz-sessions"
DEFAULT_MODEL_ID = "mlx-community/parakeet-tdt-0.6b-v3"
DEFAULT_HOTKEY = {
    "enabled": True,
    "modifiers": ["right_option", "right_shift"],
    "key_code": None,  # modifier-only chord (no character output)
}
SAMPLE_RATE = 16000


def load() -> dict:
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text())
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}
    data.setdefault("sessions_dir", str(DEFAULT_SESSIONS_DIR))
    data.setdefault("model_id", DEFAULT_MODEL_ID)
    data.setdefault("hotkey", DEFAULT_HOTKEY)
    return data


def save(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


def sessions_dir() -> Path:
    return Path(load()["sessions_dir"]).expanduser()


def model_id() -> str:
    return load()["model_id"]


def hotkey() -> dict:
    return load().get("hotkey", DEFAULT_HOTKEY)
