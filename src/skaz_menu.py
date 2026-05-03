#!/usr/bin/env python3
"""skaz menu bar app: click to start/stop a session.

Title stays a single short character so it never hides behind the notch.
Timer + screenshot count appear inside the dropdown menu only.

External control: write `stop` to ~/.skaz-control to trigger a graceful stop
from outside (used by `skaz stop` CLI). The tick timer polls this file every
second from the main Cocoa thread.
"""
from __future__ import annotations

# Hide Dock icon BEFORE any other AppKit code runs. Setting activation policy
# to Accessory makes us a "menu-bar-only" agent — no rocket in the Dock, no
# entry in cmd-Tab. Must happen before rumps initializes NSApplication.
from AppKit import NSApplication, NSApplicationActivationPolicyAccessory  # noqa: E402

NSApplication.sharedApplication().setActivationPolicy_(
    NSApplicationActivationPolicyAccessory
)

import subprocess  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
from datetime import datetime  # noqa: E402
from pathlib import Path  # noqa: E402

import objc  # noqa: E402
import rumps  # noqa: E402
from AppKit import (  # noqa: E402
    NSApp,
    NSBackingStoreBuffered,
    NSBezelStyleRounded,
    NSColor,
    NSFont,
    NSPanel,
    NSScreen,
    NSTextField,
    NSButton,
    NSView,
    NSWindowStyleMaskTitled,
    NSWindowStyleMaskClosable,
    NSStatusWindowLevel,
)
from Foundation import (  # noqa: E402
    NSObject,
    NSRunLoop,
    NSRunLoopCommonModes,
    NSTimer,
    NSMakeRect,
)

import skaz  # noqa: E402


class _LiveTimerTarget(NSObject):
    """NSObject wrapper so NSTimer can call into Python."""

    def initWithCallback_(self, callback):
        self = objc.super(_LiveTimerTarget, self).init()
        if self is None:
            return None
        self._cb = callback
        return self

    def fire_(self, sender):
        try:
            self._cb()
        except Exception:
            import traceback
            traceback.print_exc()


class _NameDialogTarget(NSObject):
    """Routes Save/Auto button clicks back to the modal runloop."""

    def initWithApp_(self, app):
        self = objc.super(_NameDialogTarget, self).init()
        if self is None:
            return None
        self._app = app
        return self

    def save_(self, sender):
        self._app.stopModalWithCode_(1)

    def cancel_(self, sender):
        self._app.stopModalWithCode_(0)


def _ask_name_dialog(default: str) -> str:
    """Show a compact native name-input dialog. No icon, left-aligned content."""
    width, height = 360, 130
    panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(0, 0, width, height),
        NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
        NSBackingStoreBuffered,
        False,
    )
    panel.setTitle_("Skaz")
    panel.setLevel_(NSStatusWindowLevel)
    panel.setReleasedWhenClosed_(False)

    content = panel.contentView()
    pad = 18
    inner_w = width - 2 * pad

    # "Name this session" label
    label = NSTextField.alloc().initWithFrame_(
        NSMakeRect(pad, height - pad - 18, inner_w, 18)
    )
    label.setStringValue_("Name this session")
    label.setEditable_(False)
    label.setBordered_(False)
    label.setBezeled_(False)
    label.setDrawsBackground_(False)
    label.setSelectable_(False)
    label.setFont_(NSFont.systemFontOfSize_(13))
    label.setTextColor_(NSColor.secondaryLabelColor())
    content.addSubview_(label)

    # Text field with prefilled value
    field_h = 26
    field_y = height - pad - 18 - 8 - field_h
    text_field = NSTextField.alloc().initWithFrame_(
        NSMakeRect(pad, field_y, inner_w, field_h)
    )
    text_field.setStringValue_(default)
    text_field.setFont_(NSFont.systemFontOfSize_(13))
    content.addSubview_(text_field)

    # Buttons (right-aligned, bottom)
    btn_w, btn_h = 80, 26
    btn_y = 12
    save_btn = NSButton.alloc().initWithFrame_(
        NSMakeRect(width - pad - btn_w, btn_y, btn_w, btn_h)
    )
    save_btn.setTitle_("Save")
    save_btn.setBezelStyle_(NSBezelStyleRounded)
    save_btn.setKeyEquivalent_("\r")
    content.addSubview_(save_btn)

    auto_btn = NSButton.alloc().initWithFrame_(
        NSMakeRect(width - pad - btn_w - 8 - btn_w, btn_y, btn_w, btn_h)
    )
    auto_btn.setTitle_("Auto")
    auto_btn.setBezelStyle_(NSBezelStyleRounded)
    auto_btn.setKeyEquivalent_("\x1b")
    content.addSubview_(auto_btn)

    target = _NameDialogTarget.alloc().initWithApp_(NSApp)
    save_btn.setTarget_(target)
    save_btn.setAction_(b"save:")
    auto_btn.setTarget_(target)
    auto_btn.setAction_(b"cancel:")

    panel.center()
    panel.makeFirstResponder_(text_field)
    text_field.selectText_(None)
    panel.makeKeyAndOrderFront_(None)
    NSApp.activateIgnoringOtherApps_(True)

    response = NSApp.runModalForWindow_(panel)
    typed = str(text_field.stringValue())
    panel.orderOut_(None)

    if response == 1:
        cleaned = "".join(c if (c.isalnum() or c in "-_ ") else "-" for c in typed.strip())
        cleaned = "-".join(cleaned.split())
        return cleaned or default
    return default


class LiveTimer:
    """NSTimer registered in NSRunLoopCommonModes so it keeps firing while a
    menu is open (default `rumps.Timer` is bound to NSDefaultRunLoopMode and
    pauses during menu tracking)."""

    def __init__(self, callback, interval: float = 1.0) -> None:
        self._target = _LiveTimerTarget.alloc().initWithCallback_(callback)
        self._interval = interval
        self._timer = None

    def start(self) -> None:
        if self._timer is not None:
            return
        self._timer = NSTimer.timerWithTimeInterval_target_selector_userInfo_repeats_(
            self._interval, self._target, b"fire:", None, True
        )
        NSRunLoop.currentRunLoop().addTimer_forMode_(self._timer, NSRunLoopCommonModes)

    def stop(self) -> None:
        if self._timer is not None:
            self._timer.invalidate()
            self._timer = None

TITLE_IDLE = "S"
TITLE_RECORDING = "●"
TITLE_TRANSCRIBING = "…"
SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
SPINNER_INTERVAL = 0.1

CONTROL_FILE = skaz.CONTROL_FILE
PID_FILE = skaz.PID_FILE


class SkazApp(rumps.App):
    def __init__(self) -> None:
        super().__init__(TITLE_IDLE, quit_button=None)

        self.start_item = rumps.MenuItem("Start session", callback=self._start_clicked)
        self.elapsed_item = rumps.MenuItem("")
        self.shots_item = rumps.MenuItem("")
        self.stop_item = rumps.MenuItem("Stop session", callback=self._stop_clicked)
        self.open_last_item = rumps.MenuItem(
            "Open last session", callback=self._open_last
        )
        self.open_folder_item = rumps.MenuItem(
            "Open sessions folder", callback=self._open_folder
        )
        self.quit_item = rumps.MenuItem("Quit", callback=self._quit)

        self.session: dict | None = None
        self.tick_timer: LiveTimer | None = None
        self.spinner_timer: LiveTimer | None = None
        self._spinner_idx = 0
        self._transcribing = False
        self.control_timer = LiveTimer(lambda: self._poll_control(None), 1)
        self.control_timer.start()

        self._render_idle_menu()
        PID_FILE.write_text(str(__import__("os").getpid()))

    def _render_idle_menu(self) -> None:
        self.menu.clear()
        self.menu = [
            self.start_item,
            None,
            self.open_last_item,
            self.open_folder_item,
            None,
            self.quit_item,
        ]

    def _render_recording_menu(self) -> None:
        self.menu.clear()
        self.elapsed_item.title = "⏺ Recording 00:00"
        self.shots_item.title = "📸 0 shots"
        self.menu = [
            self.elapsed_item,
            self.shots_item,
            None,
            self.stop_item,
            None,
            self.open_folder_item,
            None,
            self.quit_item,
        ]

    def _start_clicked(self, _) -> None:
        self._start()

    def _stop_clicked(self, _) -> None:
        self._stop()

    def _start(self) -> None:
        if self.session is not None:
            return
        name = datetime.now().strftime("session-%Y-%m-%d-%H%M%S")
        session_dir = skaz.config.sessions_dir() / name
        shots_dir = session_dir / "screenshots"
        shots_dir.mkdir(parents=True, exist_ok=True)
        wav_path = session_dir / "audio.wav"

        stop_event = threading.Event()
        start_time = time.time()
        cw = skaz.ClipboardWatcher(shots_dir, start_time, stop_event)
        ar = skaz.AudioRecorder(wav_path, stop_event)
        cw.start()
        ar.start()

        self.session = {
            "name": name,
            "dir": session_dir,
            "wav": wav_path,
            "stop_event": stop_event,
            "start_time": start_time,
            "cw": cw,
            "ar": ar,
        }

        self.title = TITLE_RECORDING
        self._render_recording_menu()
        self.tick_timer = LiveTimer(lambda: self._tick(None), 1)
        self.tick_timer.start()

    def _tick(self, _) -> None:
        if self.session is None:
            return
        elapsed = time.time() - self.session["start_time"]
        shots = len(self.session["cw"].timeline)
        self.elapsed_item.title = f"⏺ Recording {skaz.fmt(elapsed)}"
        self.shots_item.title = f"📸 {shots} shot{'' if shots == 1 else 's'}"

    def _stop(self) -> None:
        s = self.session
        if s is None:
            return
        duration = time.time() - s["start_time"]
        s["stop_event"].set()
        s["ar"].join(timeout=5)
        s["cw"].join(timeout=2)
        if self.tick_timer:
            self.tick_timer.stop()
            self.tick_timer = None

        # Ask for a name; prefill with the auto-generated timestamp.
        new_name = self._ask_name(s["name"])
        if new_name and new_name != s["name"]:
            new_dir = skaz.config.sessions_dir() / new_name
            if not new_dir.exists():
                s["dir"].rename(new_dir)
                s["dir"] = new_dir
                s["wav"] = new_dir / "audio.wav"
                s["name"] = new_name

        self._render_idle_menu()
        self.session = None

        # Start spinner; runs on main thread, watches `_transcribing` flag
        self._transcribing = True
        self._spinner_idx = 0
        self.spinner_timer = LiveTimer(self._spinner_tick, SPINNER_INTERVAL)
        self.spinner_timer.start()

        threading.Thread(
            target=self._finalize, args=(s, duration), daemon=False
        ).start()

    def _spinner_tick(self) -> None:
        if not self._transcribing:
            self.title = TITLE_IDLE
            if self.spinner_timer:
                self.spinner_timer.stop()
                self.spinner_timer = None
            return
        self.title = SPINNER_FRAMES[self._spinner_idx]
        self._spinner_idx = (self._spinner_idx + 1) % len(SPINNER_FRAMES)

    def _ask_name(self, default: str) -> str:
        return _ask_name_dialog(default)

    def _finalize(self, s: dict, duration: float) -> None:
        try:
            if not s["wav"].exists() or s["wav"].stat().st_size < 1024:
                rumps.notification("skaz", "no audio captured", s["name"])
                return

            from parakeet_mlx import from_pretrained

            model = from_pretrained(skaz.config.model_id())
            result = model.transcribe(s["wav"])

            notes = s["dir"] / "notes.md"
            raw = s["dir"] / "transcript.txt"
            body = skaz.merge(result.sentences, s["cw"].timeline, s["dir"] / "screenshots")
            with notes.open("w") as f:
                f.write(f"# {s['name']}\n\n")
                f.write(
                    f"Recorded: {datetime.fromtimestamp(s['start_time']).isoformat(timespec='seconds')}\n"
                )
                f.write(f"Duration: {skaz.fmt(duration)}\n")
                f.write(f"Screenshots: {len(s['cw'].timeline)}\n\n")
                f.write("---\n")
                f.write(body)
            with raw.open("w") as f:
                for sent in result.sentences:
                    f.write(
                        f"[{skaz.fmt(sent.start)} → {skaz.fmt(sent.end)}] {sent.text.strip()}\n"
                    )

            rumps.notification(
                "skaz",
                f"{s['name']} ready",
                f"{skaz.fmt(duration)} · {len(s['cw'].timeline)} shots",
                sound=True,
            )
        except Exception as e:
            rumps.notification("skaz error", str(e)[:120], s["name"])
        finally:
            self._transcribing = False  # spinner self-stops + restores idle title

    def _poll_control(self, _) -> None:
        if not CONTROL_FILE.exists():
            return
        cmd = CONTROL_FILE.read_text().strip()
        try:
            CONTROL_FILE.unlink()
        except FileNotFoundError:
            pass
        if cmd == "stop" and self.session is not None:
            self._stop()
        elif cmd == "start" and self.session is None:
            self._start()
        elif cmd == "quit":
            self._quit(None)

    def _latest_session(self) -> Path | None:
        sessions = [p for p in skaz.config.sessions_dir().glob("*") if p.is_dir()]
        if not sessions:
            return None
        return max(sessions, key=lambda p: p.stat().st_mtime)

    def _open_last(self, _) -> None:
        latest = self._latest_session()
        if latest is None:
            rumps.alert("No sessions yet")
            return
        notes = latest / "notes.md"
        target = notes if notes.exists() else latest
        subprocess.run(["open", str(target)])

    def _open_folder(self, _) -> None:
        skaz.config.sessions_dir().mkdir(parents=True, exist_ok=True)
        subprocess.run(["open", str(skaz.config.sessions_dir())])

    def _quit(self, _) -> None:
        if self.session:
            self._stop()
        try:
            PID_FILE.unlink()
        except FileNotFoundError:
            pass
        rumps.quit_application()


if __name__ == "__main__":
    skaz.config.sessions_dir().mkdir(parents=True, exist_ok=True)
    SkazApp().run()
