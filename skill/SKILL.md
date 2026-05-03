---
name: skaz
description: Open the latest skaz session and assemble case-study material from it. Use when user says "open last skaz", "what did I record", "build case study from my voice notes", "summarize my last session", or references their skaz dictation. Reads from sessions folder configured in ~/.config/skaz/config.json.
---

# skaz — case-study assembly skill

Triggered when the user wants to work with a skaz session: read it, summarize it, turn it into a case study, post, or any narrative document.

## Step 1: Find the session

Read `~/.config/skaz/config.json` to get `sessions_dir`. List its subdirectories sorted by modification time (newest first).

If the user named a specific session ("read the figma-redesign one"), match by name. Otherwise default to the most recent.

## Step 2: Read the session

The session folder contains:
- `notes.md` — transcript with screenshots inlined by timestamp (primary input)
- `transcript.txt` — raw transcript with [start → end] timecodes (fallback if notes.md missing)
- `audio.wav` — original recording (don't read; for reference only)
- `screenshots/` — PNG files referenced by notes.md

Read `notes.md`. The Markdown has the structure:
```
# session-name

Recorded: <iso timestamp>
Duration: MM:SS
Screenshots: N

---

**[00:00]** First sentence of dictation.

![filename.png](/absolute/path/to/screenshots/filename.png)
*screenshot at MM:SS*

**[00:08]** Next sentence...
```

Image paths are absolute. You can read them as part of the conversation if the user wants visual analysis.

## Step 3: Do what was asked

The skill itself doesn't dictate output — that comes from the user's request. Common follow-ons:

- **"What did I say"** → quick summary of the dictation, key points
- **"Build a case study"** → if `case-study` skill exists in this Claude environment, hand off to it with the notes.md content + screenshots. Otherwise: assemble a structured case-study draft (problem, approach, decisions, screenshots, outcome) using only material from the session — never invent.
- **"Make it a post"** → if `write-post` skill exists, hand off. Otherwise draft a post in the user's voice using only what they said.
- **"Tell me what's in screenshot N"** → read the PNG file, describe it.

## Hard rules

- Don't invent material. Everything in your output must be traceable to the transcript or what the user adds in conversation. If something is unclear, ask.
- Preserve the user's voice. They dictated this — keep their phrasing, idioms, energy. Don't sanitize into corporate-speak.
- If the session is empty (transcript is silent or near-empty), say so clearly. Don't fabricate content from nothing.
- If multiple sessions match, list them and let the user pick. Don't guess.

## Maintenance

This skill ships with the skaz tool itself. If skaz is not installed, the config file won't exist — gracefully tell the user "skaz isn't installed; run `git clone https://github.com/<...>/skaz` and ask Claude to install it."
