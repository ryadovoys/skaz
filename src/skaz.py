#!/usr/bin/env python3
"""skaz: voice + clipboard screenshots → merged Markdown.

While you talk, every new image landing in the macOS clipboard (CleanShot,
cmd+ctrl+shift+4, anything) is captured with a relative timestamp. On stop,
the audio is transcribed locally via Parakeet TDT v3 multilingual, and
screenshots are woven into the transcript at the moments they were taken.
"""
from __future__ import annotations

import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf
from AppKit import NSPasteboard, NSPasteboardTypePNG, NSPasteboardTypeTIFF

import config

POLL_INTERVAL = 0.3
SAMPLE_RATE = config.SAMPLE_RATE
CONTROL_FILE = config.CONTROL_FILE
PID_FILE = config.PID_FILE


def fmt(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


class ClipboardWatcher(threading.Thread):
    def __init__(self, shots_dir: Path, start_time: float, stop_event: threading.Event) -> None:
        super().__init__(daemon=True)
        self.shots_dir = shots_dir
        self.start_time = start_time
        self.stop_event = stop_event
        self.timeline: list[tuple[float, str]] = []
        self.pb = NSPasteboard.generalPasteboard()
        self.last_change = self.pb.changeCount()

    def run(self) -> None:
        while not self.stop_event.is_set():
            time.sleep(POLL_INTERVAL)
            cc = self.pb.changeCount()
            if cc == self.last_change:
                continue
            self.last_change = cc
            data = self.pb.dataForType_(NSPasteboardTypePNG)
            ext = "png"
            if data is None:
                data = self.pb.dataForType_(NSPasteboardTypeTIFF)
                ext = "tiff"
            if data is None:
                continue
            elapsed = time.time() - self.start_time
            idx = len(self.timeline) + 1
            name = f"{idx:02d}_{fmt(elapsed).replace(':', '-')}.{ext}"
            data.writeToFile_atomically_(str(self.shots_dir / name), True)
            self.timeline.append((elapsed, name))
            sys.stdout.write(f"\r📸 [{fmt(elapsed)}] {name}\n")
            sys.stdout.flush()


class AudioRecorder(threading.Thread):
    def __init__(self, wav_path: Path, stop_event: threading.Event) -> None:
        super().__init__(daemon=True)
        self.wav_path = wav_path
        self.stop_event = stop_event
        self.frames: list[np.ndarray] = []

    def run(self) -> None:
        def callback(indata, *_):
            self.frames.append(indata.copy())

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=callback):
            while not self.stop_event.is_set():
                time.sleep(0.1)
        if self.frames:
            audio = np.concatenate(self.frames, axis=0)
            sf.write(str(self.wav_path), audio, SAMPLE_RATE)


def merge(
    sentences: list,
    timeline: list[tuple[float, str]],
    shots_path: str | Path = "screenshots",
) -> str:
    base = str(shots_path)
    out: list[str] = []
    shot_idx = 0

    def emit_screenshots_until(t: float) -> None:
        nonlocal shot_idx
        while shot_idx < len(timeline) and timeline[shot_idx][0] <= t:
            elapsed, fname = timeline[shot_idx]
            out.append(f"\n![{fname}]({base}/{fname})\n*screenshot at {fmt(elapsed)}*\n")
            shot_idx += 1

    for sent in sentences:
        emit_screenshots_until(sent.end)
        out.append(f"\n**[{fmt(sent.start)}]** {sent.text.strip()}\n")
    while shot_idx < len(timeline):
        elapsed, fname = timeline[shot_idx]
        out.append(f"\n![{fname}]({base}/{fname})\n*screenshot at {fmt(elapsed)}*\n")
        shot_idx += 1
    return "".join(out)


RESERVED_CMDS = {"stop", "quit", "start", "menu", "help", "--help", "-h"}


def _menu_running() -> bool:
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        return False
    try:
        import os
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _send_control(cmd: str) -> None:
    if not _menu_running():
        print(f"skaz menu app is not running. start it: skaz menu")
        sys.exit(1)
    CONTROL_FILE.write_text(cmd)
    print(f"sent '{cmd}' to skaz menu app")


def _print_help() -> None:
    print(f"""skaz — voice + clipboard screenshots → merged Markdown

CLI mode (records in this terminal):
  skaz <name>              start a session named <name>
  skaz                     start with auto-generated name
  Ctrl+C                   stop and transcribe

Menu bar app control:
  skaz menu                launch the menu bar app (or focus it)
  skaz start [<name>]      tell the menu app to start a session
  skaz stop                tell the menu app to stop and transcribe
  skaz quit                tell the menu app to quit

Sessions land in {config.sessions_dir()}
Config:        {config.CONFIG_FILE}
""")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in RESERVED_CMDS:
        cmd = sys.argv[1]
        if cmd in {"help", "--help", "-h"}:
            _print_help()
            return
        if cmd == "menu":
            app_path = Path(__file__).resolve().parent.parent / "SkazMenu.app"
            import subprocess as _sp
            _sp.run(["open", str(app_path)])
            return
        if cmd == "stop":
            _send_control("stop")
            return
        if cmd == "quit":
            _send_control("quit")
            return
        if cmd == "start":
            _send_control("start")
            return

    name = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("session-%Y-%m-%d-%H%M")
    session = config.sessions_dir() / name
    shots = session / "screenshots"
    shots.mkdir(parents=True, exist_ok=True)
    wav_path = session / "audio.wav"

    print(f"session : {name}")
    print(f"output  : {session}")
    print(f"recording mic + watching clipboard for screenshots")
    print(f"press Ctrl+C to stop and transcribe\n")

    stop_event = threading.Event()
    start = time.time()
    cw = ClipboardWatcher(shots, start, stop_event)
    ar = AudioRecorder(wav_path, stop_event)
    cw.start()
    ar.start()

    def on_term(*_):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, on_term)

    try:
        while True:
            elapsed = time.time() - start
            sys.stdout.write(f"\r⏺  recording {fmt(elapsed)}  shots: {len(cw.timeline)}  ")
            sys.stdout.flush()
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass

    print("\n\nstopping…")
    duration = time.time() - start
    stop_event.set()
    ar.join(timeout=3)
    cw.join(timeout=2)

    if not wav_path.exists() or wav_path.stat().st_size < 1024:
        print("no audio captured; aborting transcription")
        return

    print(f"transcribing {wav_path.name} via Parakeet v3 (first run downloads ~600MB)…")
    from parakeet_mlx import from_pretrained

    model = from_pretrained(config.model_id())
    result = model.transcribe(wav_path)

    notes = session / "notes.md"
    raw = session / "transcript.txt"

    body = merge(result.sentences, cw.timeline, shots)

    with notes.open("w") as f:
        f.write(f"# {name}\n\n")
        f.write(f"Recorded: {datetime.fromtimestamp(start).isoformat(timespec='seconds')}\n")
        f.write(f"Duration: {fmt(duration)}\n")
        f.write(f"Screenshots: {len(cw.timeline)}\n\n")
        f.write("---\n")
        f.write(body)

    with raw.open("w") as f:
        for sent in result.sentences:
            f.write(f"[{fmt(sent.start)} → {fmt(sent.end)}] {sent.text.strip()}\n")

    print(f"\n✓ notes  : {notes}")
    print(f"✓ raw    : {raw}")
    print(f"✓ shots  : {len(cw.timeline)} in {shots}")


if __name__ == "__main__":
    main()
