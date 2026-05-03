# Installing skaz (instructions for Claude Code)

You are installing skaz on the user's Mac. Follow these steps in order. Use AskUserQuestion only where indicated. Run shell commands via Bash. Verify each step before moving on.

## Pre-flight checks

Before asking the user anything, verify:

1. macOS (Darwin). If not Mac → stop, tell user "skaz is macOS-only".
2. Python 3.11+ available. Check with `python3 --version`. If older → tell user to install Python 3.11+ via Homebrew or python.org and stop.
3. Xcode Command Line Tools present. Check with `xcode-select -p`. If missing → tell user to run `xcode-select --install` and stop.
4. No existing skaz menu app running. Check with `pgrep -f skaz_menu`. If running → ask user if they want to kill it and continue, or abort.

If all checks pass, briefly confirm to the user that you're proceeding.

## Step 1 — Ask the user 4 questions

Use AskUserQuestion with these exact questions, one batch:

1. **Where should sessions be saved?**
   - Default: `~/Documents/skaz-sessions`
   - Free-text path
2. **Download the Parakeet transcription model now (~1.2 GB) or on first use?**
   - Options: `Now` / `Later`
   - Recommend `Now` if user has decent internet — avoids confusing 60-90s wait on first stop
3. **Auto-start skaz menu app at login?**
   - Options: `Yes` / `No`
4. **Install the Claude skill so I can read your sessions in conversation?**
   - Options: `Yes` / `No`
   - If yes, copies `skill/SKILL.md` into `~/.claude/skills/skaz/`. Recommended.

Save the answers — you'll need them in later steps.

## Step 2 — Set up the venv

Run from the repo root (where this INSTALL.md lives):

```bash
python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt
```

If pip install fails on `parakeet-mlx` or `mlx-metal` → user is on Intel Mac. Tell them skaz requires Apple Silicon (M1+) and stop.

Verify: `.venv/bin/python -c "import rumps, sounddevice, AppKit, parakeet_mlx; print('ok')"` should print `ok`.

## Step 3 — Write config

Create `~/.config/skaz/config.json` with the user's chosen sessions folder:

```json
{
  "sessions_dir": "<absolute path from question 1, expanded>",
  "model_id": "mlx-community/parakeet-tdt-0.6b-v3"
}
```

Then create the sessions folder: `mkdir -p "<sessions_dir>"`.

## Step 4 — Generate the menu-bar .app bundle

The repo has `templates/launcher.applescript` with a `{{INSTALL_DIR}}` placeholder. Replace that with the absolute path of the repo root (where you ran `python3 -m venv .venv`), compile to a .app, and ad-hoc sign it.

```bash
INSTALL_DIR="$(pwd)"
TMP=$(mktemp).applescript
sed "s|{{INSTALL_DIR}}|${INSTALL_DIR}|g" templates/launcher.applescript > "$TMP"
osacompile -o SkazMenu.app "$TMP"
rm "$TMP"

# Set LSUIElement so it stays out of the Dock
/usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" SkazMenu.app/Contents/Info.plist 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Set :LSUIElement true" SkazMenu.app/Contents/Info.plist

# Mic permission description (otherwise macOS may deny silently)
/usr/libexec/PlistBuddy -c "Add :NSMicrophoneUsageDescription string 'skaz records voice during dictation sessions'" SkazMenu.app/Contents/Info.plist 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Set :NSMicrophoneUsageDescription 'skaz records voice during dictation sessions'" SkazMenu.app/Contents/Info.plist

# Ad-hoc sign so macOS treats it as a valid local app
codesign --force --deep --sign - SkazMenu.app
```

Verify: `codesign -dv SkazMenu.app 2>&1 | grep -i adhoc` should show `Signature=adhoc`.

## Step 5 — Install the CLI symlink

```bash
mkdir -p "$HOME/.local/bin"
ln -sf "$(pwd)/skaz" "$HOME/.local/bin/skaz"
```

Tell the user that if `$HOME/.local/bin` is not on their PATH, they should add it to their shell config (zsh: `~/.zshrc`). Don't edit their shell config without permission.

## Step 6 — Optional: download model now

If the user answered `Now` to question 2, trigger the model download. This takes 1-3 minutes on a fast connection.

```bash
.venv/bin/python -c "from parakeet_mlx import from_pretrained; from_pretrained('mlx-community/parakeet-tdt-0.6b-v3'); print('model ready')"
```

Show the user that it's downloading (this command will block until done). When it prints `model ready`, the model is cached at `~/.cache/huggingface/`.

## Step 6.5 — Optional: install the Claude skill

If the user answered `Yes` to question 4:

```bash
mkdir -p ~/.claude/skills/skaz
cp skill/SKILL.md ~/.claude/skills/skaz/SKILL.md
```

This makes the skill available in any future Claude Code session — when the user says "read my last skaz session" or "build a case study from my voice", Claude finds the skill and acts on it.

## Step 7 — Optional: auto-start at login

If the user answered `Yes` to question 3, add the .app to Login Items:

```bash
osascript -e "tell application \"System Events\" to make login item at end with properties {path:\"$(pwd)/SkazMenu.app\", hidden:false}"
```

If macOS prompts for Automation permission for Terminal — that's normal, user grants once.

## Step 8 — Smoke test

1. Verify CLI: run `skaz help` (or `~/.local/bin/skaz help`). Should print usage.
2. Verify menu app launches: run `open "$(pwd)/SkazMenu.app"`. After 2-3 seconds, check `pgrep -fl skaz_menu`. Should show one Python process running `skaz_menu.py`.
3. Tell the user to look at their menu bar (top-right of screen). They should see the letter `S`. Ask them to confirm.

If they don't see `S` → check `/tmp/skaz-menu.log` for errors. Common issues: mic permission not yet granted (ask user to click S → Start session, macOS will prompt; once granted, recording works).

## Step 9 — Done

Tell the user:

- Click `S` in menu bar → Start session, talk, screenshot, Stop, name it.
- Sessions live in `<sessions_dir>`.
- Stop a stuck session from terminal: `skaz stop`.
- Re-run this install if you change config.

Suggest they try a 30-second test session right now to confirm the full pipeline works end-to-end.

## Troubleshooting (if any step fails)

- **`pip install` fails on numba/llvmlite**: user has Python 3.14 but llvmlite hasn't released wheel yet. Have them retry on Python 3.13.
- **`open SkazMenu.app` shows Python rocket in Dock**: re-run codesign step. If still wrong, the LSUIElement key wasn't added — re-run PlistBuddy line.
- **Mic permission silently denied**: the .app's Info.plist must have `NSMicrophoneUsageDescription`. Re-run that step.
- **`skaz` command not found**: the symlink is in `~/.local/bin/`, but PATH may not include it. Tell user to add `export PATH="$HOME/.local/bin:$PATH"` to their shell config.

If you hit something unfamiliar, don't speculate — read `AGENTS.md` for codebase orientation, then debug from there.
