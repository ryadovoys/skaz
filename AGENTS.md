# skaz — codebase orientation for Claude

## What this tool does

skaz captures a voice + screenshots dictation session on macOS and produces a Markdown document with the screenshots woven into the transcript at the moments they were taken. Built for designers who narrate over a screen while screenshotting points of interest.

Output of one session:
```
<sessions_dir>/<session-name>/
  audio.wav
  transcript.txt        # transcript with [start → end] timecodes
  notes.md              # Markdown with transcript + inline screenshots
  screenshots/          # PNGs captured from clipboard during session
```

## How a session flows

1. User clicks `S` in menu bar → Start session
2. Two threads spawn:
   - `AudioRecorder` records mic at 16 kHz mono into a numpy buffer
   - `ClipboardWatcher` polls `NSPasteboard.changeCount()` every 0.3s. When clipboard gains a new image, it's saved to `screenshots/NN_MM-SS.png` and timestamp logged.
3. User clicks `S` → Stop. Threads stop, wav is flushed.
4. Dialog asks for session name (prefilled with auto-timestamp).
5. Background thread runs Parakeet TDT v3 multilingual (MLX) on the wav. Returns `AlignedSentence`s with `start`, `end`, `text`.
6. `merge()` interleaves sentences with screenshots: each screenshot is inserted right after the sentence whose `end` time is ≥ the screenshot's elapsed time.
7. notes.md + transcript.txt written. macOS notification fired.

## File map

```
src/
  config.py        — load/save ~/.config/skaz/config.json. Module-level paths
                     (CONFIG_DIR, CONTROL_FILE, PID_FILE) are constants.
  skaz.py          — CLI entry. Defines ClipboardWatcher, AudioRecorder, merge().
                     Reserved subcommands: `menu`, `start`, `stop`, `quit`, `help`.
                     Anything else is treated as a session name → CLI mode.
  skaz_menu.py     — rumps menu-bar app. Imports skaz module. Owns NSPanel
                     name dialog, LiveTimer (NSRunLoopCommonModes), spinner.

skaz               — bash launcher that execs .venv/bin/python src/skaz.py
templates/
  launcher.applescript — AppleScript template with {{INSTALL_DIR}} placeholder.
                         Compiled to SkazMenu.app at install time.
SkazMenu.app/      — generated at install (gitignored). AppleScript wrapper that
                     spawns the menu Python process detached. NOT a Python .app
                     bundle (those break with PyObjC + venv interpolation).

requirements.txt   — pinned core deps
INSTALL.md         — installer script for Claude Code
README.md          — human-facing pitch
```

## Architecture decisions worth knowing

- **Why AppleScript wrapper, not py2app or shell .app:** When a .app's MacOS executable is a shell script that execs Python, NSBundle.mainBundle() in the Python process points at the system Python framework, not our .app. LSUIElement gets ignored, dock icon appears. AppleScript-as-launcher detaches Python as a "user-session daemon" — Python becomes a regular process not tied to any bundle, and `setActivationPolicy(Accessory)` (set at top of skaz_menu.py before any other AppKit) keeps it out of the Dock.

- **Why activation policy at top of skaz_menu.py:** rumps sets it inside `App.run()` but by then NSApplication is already up and dock icon may have flickered. Setting it as the very first AppKit call prevents any visible dock entry.

- **Why custom NSTimer (LiveTimer) instead of rumps.Timer:** rumps.Timer schedules in `NSDefaultRunLoopMode`, which freezes when an NSMenu is open. `NSRunLoopCommonModes` keeps the timer firing during menu tracking so live elapsed/shots updates stay responsive while user has the menu open.

- **Why control via file (~/.config/skaz/control), not signals:** A polling pattern via filesystem keeps the menu app drivable from the CLI (`skaz stop`) without inter-process signal handling. The menu's tick timer reads the control file once per second on the main Cocoa thread.

- **Why polling NSPasteboard, not screen recording:** ScreenCaptureKit requires Screen Recording TCC permission (intrusive). Polling pasteboard via NSBundle.changeCount() is universal — works for CleanShot, system cmd+ctrl+shift+4, drag&drop images, anything that copies an image to clipboard.

- **Why merge by sentence end (not start):** Screenshots are inserted *after* the sentence whose end-time spans the screenshot moment. Reads naturally as "I just described what you see in this screenshot."

- **Why absolute paths in notes.md (not relative):** notes.md is a personal document, not portable artifact. Absolute paths render in any markdown previewer regardless of which folder the file is opened from. The session folder never moves so brittleness isn't an issue.

- **Threading model:** AudioRecorder + ClipboardWatcher are daemon threads inside the Python process. Stop is via threading.Event. The menu's main loop is the Cocoa runloop. Transcription runs on a non-daemon background thread (so it survives the menu app being told to quit until done).

- **Global hotkey via NSEvent monitor:** `HotkeyMonitor` listens for `NSEventMaskFlagsChanged` events across the whole system. On each modifier change it computes `flags & ALL_MODIFIER_MASK` and exact-matches against the configured set (so `cmd+opt+shift` won't fire a `cmd+opt` rule). Rising-edge trigger only — calls toggle once per chord press, not on release. Distinguishes left vs right modifiers via NX_DEVICELCMDKEYMASK / NX_DEVICERCMDKEYMASK device-specific bits in the low 16 bits of NSEvent.modifierFlags(). Requires Accessibility permission granted to the running app. Without it, menu bar still works.

## Common operations

- Run a CLI session: `skaz <name>` (or `python src/skaz.py <name>`). Ctrl+C stops.
- Launch menu: `skaz menu` (opens SkazMenu.app)
- Stop a stuck menu session from terminal: `skaz stop`
- Quit the menu app from terminal: `skaz quit`
- Help: `skaz help`

## Common edits

- **Add a config field:** `src/config.py` → add to defaults + add accessor. Persist via `save()`.
- **Change spinner frames:** `src/skaz_menu.py` `SPINNER_FRAMES`.
- **Change merge format:** `src/skaz.py` `merge()`. Note: changing markdown format may break user's existing pipelines — be conservative.
- **Add menu item:** `src/skaz_menu.py` `__init__` (build item) + `_render_idle_menu` or `_render_recording_menu` (place it).

## What NOT to change without thinking

- The activation-policy-at-top-of-file trick (line 16-20 of skaz_menu.py). Moving it later breaks dock-hiding.
- The AppleScript launcher pattern. We tried shell-launched Python — Dock icon and LSUIElement issues.
- The control-file polling interval (1s). Faster wastes battery; slower makes `skaz stop` feel laggy.
