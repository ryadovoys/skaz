# Installing skaz (instructions for Claude Code)

You are installing skaz on the user's Mac. Follow these steps in order. Use AskUserQuestion only where indicated. Run shell commands via Bash. Verify each step before moving on.

## Pre-flight checks

Before asking the user the install questions, verify their machine has the basics. Don't just bail when something is missing — help them get it.

### 1. macOS

`uname` must be `Darwin`. If not Mac → stop, tell user "skaz is macOS-only".

### 2. Apple Silicon

`uname -m` should be `arm64`. If `x86_64` (Intel Mac) → stop, tell user that Parakeet via MLX requires Apple Silicon (M1+). No fallback exists in skaz today.

### 3. Xcode Command Line Tools

`xcode-select -p` should return a path. If it returns an error:
- Run `xcode-select --install`. This opens a GUI installer dialog.
- Tell the user "macOS opened a dialog — click Install and accept the license. Tell me when it finishes (~5 minutes), then I'll continue."
- Wait for user confirmation before proceeding.

### 4. Homebrew (only if we'll need to install Python)

Skip this step if Python 3.11+ is already present (check with `python3 --version`).

If we'll need Homebrew to install Python:
- `command -v brew` — if exists, good.
- If missing, ask the user: "You don't have Homebrew installed. It's the standard macOS package manager and we need it to install Python. Install it now? (Yes/No)". 
- If yes, run:
  ```bash
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ```
  This is interactive — Homebrew prompts for sudo password and shows progress. Tell user "Homebrew installer is running — enter your password when prompted, watch for the 'Installation successful' message."
- After install, source the brew shellenv so `brew` is on PATH for this session: `eval "$(/opt/homebrew/bin/brew shellenv)"`.
- If user declines Homebrew → stop. They can install Python manually from python.org and re-run.

### 5. Python 3.11+

Check `python3 --version`. Acceptable: 3.11, 3.12, 3.13, 3.14.

If Python is missing or older than 3.11:
- Ask user: "You need Python 3.11+. Install Python 3.13 via Homebrew now? (Yes/No)"
- If yes:
  ```bash
  brew install python@3.13
  ```
  After install, the binary is at `/opt/homebrew/bin/python3.13`. Use that explicitly in subsequent venv steps (replace `python3` with `python3.13` in Step 2).
- If no → stop, user can install manually.

### 6. No existing skaz session running

`pgrep -f skaz_menu` should return nothing. If a skaz menu app is already running:
- Ask user: "skaz menu app is already running (PID X). Quit it and continue, or abort?".
- If continue → run `pkill -f skaz_menu` then proceed.

### 7. Confirm and proceed

Briefly tell the user "Pre-flight passed. Now I need 4 quick things before I install."

## Step 1 — Ask the user 5 questions

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
5. **Set up a global hotkey to start/stop sessions?**
   - Default: `Right Cmd + Right Option` (toggle — same combo starts and stops)
   - Options: `Default (right cmd + right option)` / `No hotkey` / `Custom`
   - If `Custom`, ask follow-up: which modifiers? Accept any combination of `left_cmd`, `right_cmd`, `left_option`, `right_option`, `left_shift`, `right_shift`, `left_control`, `right_control`. Modifier-only chord (no letter key).

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

Create `~/.config/skaz/config.json` with the user's chosen sessions folder and hotkey settings:

```json
{
  "sessions_dir": "<absolute path from question 1, expanded>",
  "model_id": "mlx-community/parakeet-tdt-0.6b-v3",
  "hotkey": {
    "enabled": true,
    "modifiers": ["right_cmd", "right_option"]
  }
}
```

Apply user's answer from question 5:
- `Default` → use `["right_cmd", "right_option"]` and `enabled: true`
- `No hotkey` → set `enabled: false`, leave modifiers default (so user can flip later)
- `Custom` → use the modifier names they listed

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
- Or use the hotkey (default: hold `Right Cmd + Right Option`) — same combo toggles start and stop.
- Sessions live in `<sessions_dir>`.
- Stop a stuck session from terminal: `skaz stop`.
- Re-run this install if you change config (or edit `~/.config/skaz/config.json` directly).

**About the hotkey:** the first time the user presses it, macOS may show a dialog asking to grant **Accessibility** permission to skaz (System Settings → Privacy & Security → Accessibility). They need to allow it for the global hotkey to work. Without it, the menu bar still works fine.

Suggest they try a 30-second test session right now to confirm the full pipeline works end-to-end.

## Troubleshooting (if any step fails)

- **`pip install` fails on numba/llvmlite**: usually means a too-new Python with no wheels yet. Retry on a stable LTS like 3.13.
- **`open SkazMenu.app` shows Python rocket in Dock**: re-run codesign step. If still wrong, the LSUIElement key wasn't added — re-run PlistBuddy line.
- **Mic permission silently denied**: the .app's Info.plist must have `NSMicrophoneUsageDescription`. Re-run that step.
- **`skaz` command not found**: the symlink is in `~/.local/bin/`, but PATH may not include it. Tell user to add `export PATH="$HOME/.local/bin:$PATH"` to their shell config.

If you hit something unfamiliar, don't speculate — read `AGENTS.md` for codebase orientation, then debug from there.
