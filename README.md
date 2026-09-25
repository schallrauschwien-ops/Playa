# Playa — Audio Show Control

A simple, rock-solid audio cue player in the spirit of QLab, for **Windows**.
Stereo output via **ASIO** (pro sound card) or the regular Windows / laptop output.

---

## Features

- **One cue active at a time** — starting a new cue **auto-fades the running one
  out in 0.5 s** (no hard cut).
- **GO** (Space) starts the standing cue and arms the next one; press Space
  again to play the next, and so on. **STOP** (Esc) fades out, **PANIC** stops
  instantly.
- **Per-cue volume** plus a master fader.
- **Waveform** that always shows the **current cue**, with a draggable
  **start point** (trim) and a live playback cursor.
- **Countdown** (remaining time) shown large at the top and per cue row.
- **Per-cue end mode** with icons matching the sketch:
  **↓** = follow (start the next cue automatically),
  **→|** = stop (stop after this cue). Click the icon to toggle.
- **GO TO** list entries for looping playlists (e.g. "GO TO 1" after cue 10
  loops the whole list until you stop). Loop-protection is built in.
- **Per-cue global hotkeys** (Stream-Deck friendly: the Deck just sends a
  keystroke).
- **Save / load shows** (`.playa` file) including all settings and file paths.
- ASIO and the local output are switchable in the **Audio device** menu.
- Plays **WAV, FLAC, OGG, AIFF and MP3** (all patent-free / cleanly licensed).

---

## Quick start (run from source, to test)

Requires **Python 3.11 or 3.12 (64-bit)** from python.org (tick "Add Python to
PATH" during install).

Double-click **`run_from_source.bat`** — the first run installs the
dependencies, then Playa starts.

---

## Build the EXE

> **Important:** Put the `playa` folder in a normal location you can write to,
> e.g. `C:\Users\<you>\Desktop\playa`. Do **not** build inside
> `C:\Program Files\...` — Windows blocks writing there and the build will fail
> with "permission denied". The finished installer is what puts Playa into
> Program Files later.

Double-click **`build.bat`**. It creates the app at:

```
dist\Playa\Playa.exe
```

The whole `dist\Playa\` folder is portable — copy it to other Windows machines.

---

## Installer + desktop shortcut

To get a proper install with a **desktop shortcut** created automatically:

1. Run `build.bat` (creates `dist\Playa\`).
2. Install **Inno Setup** (free): https://jrsoftware.org/isdl.php
3. Open `installer\playa.iss` in Inno Setup and click **Compile**.
   The installer appears at `installer\Setup\Playa-Setup.exe`.
4. Run that installer — it installs Playa and (with the checkbox ticked) puts a
   **Playa** icon on the desktop.

Don't want an installer? After `build.bat`, run **`make_desktop_shortcut.bat`**
to drop a desktop shortcut to the EXE.

---

## ASIO

`sounddevice` ships two PortAudio DLLs on Windows (with and without ASIO).
Playa sets `SD_ENABLE_ASIO=1` before importing it (see `run.py`), so the
ASIO-capable build is loaded. Your ASIO devices then appear in the
**Audio device** menu under "— ASIO —".

Note: ASIO drivers usually allow only **one** active application at a time.
Close other programs using the same card.

---

## Hotkeys / Stream Deck

Type a key or combo in the **HOTKEY** column, e.g. `f5`, `f6`, `ctrl+1`,
`num 1`. In the Stream Deck app, add a "System: Hotkey" action with the same
key.

Global hotkeys use the `keyboard` library. If keys aren't detected, start Playa
**as administrator** once (some systems require that for system-wide keyboard
hooks). While Playa is in the foreground the transport keys (Space / Esc /
arrows) always work.

---

## Keyboard

| Key          | Action                            |
|--------------|-----------------------------------|
| Space        | GO (play the standing cue)        |
| Esc          | STOP (0.5 s fade)                 |
| ↑ / ↓        | Move the standing (ready) cue     |
| Ctrl+I       | Add audio                         |
| Ctrl+O / S   | Open / save show                  |
| Del          | Remove cue                        |
| Ctrl+↑ / ↓   | Move cue up / down                |

---

## Notes

- The UI uses the **Ink Free** font (with fallbacks) for the casual beach feel;
  the cue list itself uses a clean readable font.
- For maximum reliability in a live show, **WAV** or **FLAC** are recommended.
  All supported formats are decoded losslessly into memory on load.
