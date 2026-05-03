# skaz

> сказ — то что было рассказано и показано

Local voice + clipboard screenshots → merged Markdown. Built for designers narrating over a screen who want a transcript with screenshots inlined at the moments they were taken — ready to drop into Claude (or any LLM) as case-study material.

```
You speak    → 🎙 audio.wav (16 kHz mono)
You screenshot → 📋 clipboard image → screenshots/01_00-12.png
You stop     → notes.md with transcript and screenshots interleaved by timestamp
```

Everything stays on your Mac. Transcription is local via Parakeet TDT v3 multilingual (~25 European languages including English, Russian, German, Spanish, etc.).

## Install (via Claude Code)

skaz installs itself by handing the install instructions to Claude Code. No installer GUI, no manual config.

```bash
git clone https://github.com/<you>/skaz
cd skaz
claude
```

Then in Claude Code, say: **"install this"**

Claude reads `INSTALL.md`, asks 3 questions (where to save sessions, download model now or later, auto-start at login), runs the install, verifies. After that, skaz is a normal Mac menu-bar app — you don't need Claude in the loop to use it.

## Use

Click `S` in your menu bar:

- **Start session** → recording begins
- Talk while looking at the screen. Cmd+Ctrl+Shift+4 (or CleanShot, or anything) to grab screenshots into clipboard.
- **Stop session** → name it (or hit Enter to keep auto-name) → wait for transcription
- Notification → click "Open last session" to read the result

Each session lives in its own folder with `notes.md`, `audio.wav`, `transcript.txt`, and `screenshots/`. Drag `notes.md` into a Claude conversation and you have rich case-study material with images woven in by time.

Stop a stuck session from the terminal:

```bash
skaz stop
```

## Requirements

- Apple Silicon Mac (M1+)
- macOS 14+
- Python 3.11–3.13
- Microphone permission (granted on first session)
- Claude Code for the install step — [download](https://claude.com/claude-code)

## What it doesn't do

- No cloud sync (sessions are local files)
- No video / screen recording — clipboard images only
- No multi-speaker diarization (single-mic dictation only)
- No in-app transcript editor — open notes.md in your editor

## Why

Existing tools split the workflow: recording apps don't know about clipboard images, screenshot tools don't know about voice timing, transcription apps don't merge with anything. skaz does only the bridge: time-anchored voice + visual evidence → one document. After that, your editor or your LLM does the rest.

## Acknowledgments

- [Parakeet TDT 0.6B v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3) by NVIDIA
- [parakeet-mlx](https://github.com/senstella/parakeet-mlx) — Apple MLX port
- [rumps](https://github.com/jaredks/rumps) — menu-bar plumbing
- Inspired by [Relay](https://github.com/msllrs/relay)

## License

MIT
