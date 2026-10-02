# Playa — Audio Show Control

A simple, rock-solid audio cue player in the spirit of QLab, for **Windows**.
Stereo output via WASAPI, or via **ASIO** once you add the driver DLL
(see below) — pro sound card or the regular laptop output.

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
- All outputs are switchable in the **Audio device** menu (ASIO appears
  there once its DLL is in place, see below).
- Plays **WAV, FLAC, OGG, AIFF and MP3** (all patent-free / cleanly licensed).

---

## Download

Grab `Playa-Setup.exe` from the
[latest release](https://github.com/schallrauschwien-ops/Playa/releases/latest),
run it, done. No Python, no account, nothing to configure.

Everything below is for building Playa yourself from the source — worth
reading if you would rather not trust a downloaded installer, or if you want
to change something.

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

ASIO is supported, but **not shipped**. The ASIO-capable PortAudio DLL
contains code from Steinberg's ASIO SDK, whose licence forbids passing the
SDK or parts of it on. That does not sit well with the GPLv3 this project is
under, so the installer leaves it out. Audacity does the same, for the same
reason.

Without it, Playa uses WASAPI and the other Windows audio paths. For most
sound cards WASAPI in exclusive mode gets close to ASIO latency.

To use ASIO, fetch the DLL for your machine from
[portaudio-binaries](https://github.com/spatialaudio/portaudio-binaries) —
`libportaudio64bit-asio.dll` on a normal 64-bit PC — and drop it into

```
Playa\_internal\_sounddevice_data\portaudio-binaries\
```

Windows will ask for permission to write there; that is expected. Playa
notices the file on the next start and switches ASIO on by itself. Your ASIO
devices then appear in the **Audio device** menu under "— ASIO —".

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

---

## License

Playa is free software under the **GNU General Public License v3.0**. You may
use it, pass it on and change it, as long as changes are passed on under the
same licence. The full text is in [LICENSE](LICENSE).

Playa stands on free components, each under its own licence — among them
PySide6, PortAudio, libsndfile and soxr.

---

## Who made this

Playa was written by **Dejan Mandic**, a freelance sound engineer in Vienna.
It grew out of the work it was built for: mixing sound for concerts, theatre
and events, where a cue has to fire on time and nothing may crash.

More of that work — recordings, photographs, and how to get in touch:
**[dejan.schallrausch.at](https://dejan.schallrausch.at/)**

Bugs and ideas are welcome in the
[issues](https://github.com/schallrauschwien-ops/Playa/issues).
