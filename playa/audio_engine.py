"""
Audio-Engine für Playa.

- Ein einziger PortAudio-OutputStream (Stereo, float32).
- Geräteauswahl inkl. ASIO (via sounddevice; SD_ENABLE_ASIO wird in run.py gesetzt).
- Immer genau EIN aktiver Cue. Ein neuer Start blendet den laufenden in 0,5 s aus.
- Fades werden sample-genau im Audio-Callback gerechnet (kein UI-Timer).
- Ereignisse (Cue zu Ende) gehen über eine threadsichere Queue an die GUI.

`load_audio` und die `Voice`-Klasse benötigen kein sounddevice und sind isoliert
testbar. `sounddevice` wird erst in AudioEngine.open() importiert.
"""

from __future__ import annotations
import os
import queue
import subprocess
import threading
import numpy as np
import soundfile as sf
import soxr

# Extensions libsndfile can't decode -> use bundled ffmpeg instead.
FFMPEG_EXTS = {".m4a", ".mp4", ".aac", ".m4b", ".mov"}

INTERRUPT_FADE = 0.5   # Sekunden Ausblendung beim Unterbrechen (Feature 9)
START_FADE = 0.012     # kurze Einblendung gegen Klicks (~12 ms)
PEAK_BUCKETS = 2000    # Auflösung der vorberechneten Wellenform-Hüllkurve


# ---------------------------------------------------------------------------
# Laden + Aufbereiten (Stereo, Resampling auf Engine-Rate, Peak-Hüllkurve)
# ---------------------------------------------------------------------------

def _ffmpeg_exe():
    """Pfad zur ffmpeg-Binärdatei (gebündelt via imageio-ffmpeg)."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"   # Fallback: System-ffmpeg im PATH


def _decode_with_ffmpeg(path: str, engine_sr: int):
    """Dekodiert AAC/MP4/M4A nach Stereo float32 @ engine_sr via ffmpeg."""
    exe = _ffmpeg_exe()
    cmd = [
        exe, "-v", "error", "-nostdin", "-i", path,
        "-f", "f32le", "-acodec", "pcm_f32le",
        "-ac", "2", "-ar", str(engine_sr), "-",
    ]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          creationflags=flags)
    if proc.returncode != 0 or not proc.stdout:
        msg = proc.stderr.decode("utf-8", "ignore").strip() or "ffmpeg decode failed"
        raise RuntimeError(msg)
    data = np.frombuffer(proc.stdout, dtype=np.float32)
    n = data.size // 2
    return np.ascontiguousarray(data[:n * 2].reshape(n, 2)), engine_sr


def load_audio(path: str, engine_sr: int):
    """
    Liest eine Audiodatei, wandelt sie nach Stereo float32, resampelt auf
    engine_sr und berechnet eine Peak-Hüllkurve fürs Wellenform-Bild.

    WAV/FLAC/OGG/AIFF/MP3 -> libsndfile (soundfile)
    M4A/MP4/AAC          -> ffmpeg (imageio-ffmpeg)

    Rückgabe: (samples (n,2) float32, src_sr, duration_sec, peaks (PEAK_BUCKETS,2))
    """
    ext = os.path.splitext(path)[1].lower()
    if ext in FFMPEG_EXTS:
        data, sr = _decode_with_ffmpeg(path, engine_sr)
    else:
        try:
            data, sr = sf.read(path, dtype="float32", always_2d=True)
        except Exception:
            data, sr = _decode_with_ffmpeg(path, engine_sr)   # last-resort

    ch = data.shape[1]
    if ch == 1:
        data = np.repeat(data, 2, axis=1)
    elif ch > 2:
        data = data[:, :2]
    data = np.ascontiguousarray(data, dtype=np.float32)

    if sr != engine_sr:
        data = soxr.resample(data, sr, engine_sr)
        data = np.ascontiguousarray(data, dtype=np.float32)

    duration = data.shape[0] / float(engine_sr)
    peaks = compute_peaks(data, PEAK_BUCKETS)
    return data, sr, duration, peaks


def compute_peaks(data: np.ndarray, buckets: int) -> np.ndarray:
    """Min/Max-Hüllkurve pro Bucket (gemittelt über beide Kanäle) -> (buckets, 2)."""
    n = data.shape[0]
    if n == 0:
        return np.zeros((buckets, 2), dtype=np.float32)
    mono = data.mean(axis=1)
    buckets = min(buckets, n)
    # in (buckets) Abschnitte aufteilen
    idx = np.linspace(0, n, buckets + 1, dtype=np.int64)
    out = np.zeros((buckets, 2), dtype=np.float32)
    for i in range(buckets):
        a, b = idx[i], idx[i + 1]
        if b <= a:
            continue
        seg = mono[a:b]
        out[i, 0] = seg.min()
        out[i, 1] = seg.max()
    return out


# ---------------------------------------------------------------------------
# Voice: eine konkrete Wiedergabe-Instanz eines Cues
# ---------------------------------------------------------------------------

class Voice:
    """
    Eine laufende Wiedergabe. Lautstärke = env * level * master:
      - env   : 0..1 Fade-Hüllkurve (für Ein-/Ausblenden), rampt im Callback
      - level : Cue-Lautstärke (live vom Slider änderbar)
      - master: globaler Faktor (live, von der Engine gelesen)
    """
    def __init__(self, cue_id, data, sr, level, start_frame=0, end_frame=None, loop=False):
        self.cue_id = cue_id
        self.data = data                      # (n, 2) float32
        self.sr = sr
        self.level = float(level)
        self.start_frame = int(start_frame)
        self.pos = int(start_frame)
        n = data.shape[0]
        self.end_frame = n if end_frame is None else min(int(end_frame), n)
        self.loop = bool(loop)
        self.env = 0.0
        self.env_target = 1.0
        self.env_inc = 1.0 / max(1, int(START_FADE * sr))   # Einblendung
        self.is_active = True                 # False = wird ausgeblendet/verworfen

    def begin_fade_out(self, seconds):
        steps = max(1, int(seconds * self.sr))
        self.env_target = 0.0
        self.env_inc = -self.env / steps if self.env > 0 else -1.0 / steps
        self.is_active = False

    def render(self, outbuf, frames, master):
        """
        Mischt `frames` Samples additiv in outbuf (frames, 2).
        Bei loop=True wird am End-Trim nahtlos zum Start-Trim zurückgesprungen.
        Rückgabe: True wenn die Voice fertig ist (ausgefadet oder am Ende ohne Loop).
        """
        filled = 0
        while filled < frames:
            if self.pos >= self.end_frame:
                if self.loop:
                    self.pos = self.start_frame
                    if self.pos >= self.end_frame:   # Schutz vor 0-Länge
                        break
                else:
                    break
            avail = self.end_frame - self.pos
            n = min(frames - filled, avail)
            if n <= 0:
                break
            chunk = self.data[self.pos:self.pos + n]

            if self.env_inc != 0.0:
                env = self.env + self.env_inc * np.arange(1, n + 1, dtype=np.float32)
                lo, hi = (self.env, self.env_target) if self.env_inc > 0 else (self.env_target, self.env)
                np.clip(env, lo, hi, out=env)
                self.env = float(env[-1])
                if (self.env_inc > 0 and self.env >= self.env_target) or \
                   (self.env_inc < 0 and self.env <= self.env_target):
                    self.env = self.env_target
                    self.env_inc = 0.0
            else:
                env = np.full(n, self.env, dtype=np.float32)

            gain = env * (self.level * master)
            outbuf[filled:filled + n] += chunk * gain[:, None]
            self.pos += n
            filled += n

        faded_out = (self.env_target == 0.0 and self.env <= 0.0)
        at_end = (self.pos >= self.end_frame) and not self.loop
        return faded_out or at_end


# ---------------------------------------------------------------------------
# AudioEngine
# ---------------------------------------------------------------------------

class AudioEngine:
    def __init__(self):
        self._sd = None
        self.stream = None
        self.samplerate = 48000
        self.device = None              # PortAudio-Geräteindex oder None (Default)
        self.master = 1.0

        self._lock = threading.Lock()
        self._active = None             # aktuell spielende Voice
        self._fading = []               # ausblendende Voices
        self.events = queue.Queue()     # ("ended", cue_id) / ("cleanup", cue_id)

    # ---- Geräte ----
    def _ensure_sd(self):
        if self._sd is None:
            import sounddevice as sd     # erst hier importieren (ASIO-Env muss gesetzt sein)
            self._sd = sd
        return self._sd

    def list_devices(self):
        """Liefert Liste von (index, label, hostapi_name, max_out_channels)."""
        sd = self._ensure_sd()
        out = []
        apis = sd.query_hostapis()
        for i, d in enumerate(sd.query_devices()):
            if d["max_output_channels"] < 1:
                continue
            api = apis[d["hostapi"]]["name"]
            out.append((i, d["name"], api, d["max_output_channels"]))
        return out

    def device_default_samplerate(self, device):
        sd = self._ensure_sd()
        try:
            info = sd.query_devices(device)
            return int(info["default_samplerate"])
        except Exception:
            return 48000

    # ---- Stream ----
    def open(self, device=None, samplerate=None):
        """Öffnet (oder reöffnet) den Output-Stream für das gewählte Gerät."""
        sd = self._ensure_sd()
        self.close()
        self.device = device
        self.samplerate = int(samplerate or self.device_default_samplerate(device))
        with self._lock:
            self._active = None
            self._fading = []
        self.stream = sd.OutputStream(
            samplerate=self.samplerate,
            device=device,
            channels=2,
            dtype="float32",
            blocksize=0,            # PortAudio wählt optimale Blockgröße
            callback=self._callback,
        )
        self.stream.start()
        return self.samplerate

    def close(self):
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

    # ---- Audio-Callback (läuft im PortAudio-Thread!) ----
    def _callback(self, outdata, frames, time_info, status):
        outdata.fill(0.0)
        master = self.master
        with self._lock:
            active = self._active
            fading = self._fading

        if active is not None:
            done = active.render(outdata, frames, master)
            if done:
                with self._lock:
                    if self._active is active:
                        self._active = None
                self.events.put(("ended", active.cue_id))

        if fading:
            still = []
            for v in fading:
                done = v.render(outdata, frames, master)
                if done:
                    self.events.put(("cleanup", v.cue_id))
                else:
                    still.append(v)
            with self._lock:
                # nur die noch laufenden behalten (neue könnten dazugekommen sein)
                self._fading = [v for v in self._fading if v in still or v is self._active]

        np.clip(outdata, -1.0, 1.0, out=outdata)

    # ---- Steuerung (aus GUI-Thread) ----
    def play(self, cue, start_override=None):
        """Startet `cue` sofort; ein laufender Cue wird in 0,5 s ausgeblendet.
        start_override (Sekunden) überschreibt den Startpunkt (für Klick-Seek)."""
        if cue.samples is None:
            return
        n = cue.samples.shape[0]
        loop = (getattr(cue, "end_mode", None) is not None
                and cue.end_mode.value == "loop")
        if start_override is not None:
            start_frame = int(max(0.0, start_override) * self.samplerate)
        else:
            start_frame = int(max(0.0, cue.trim_start) * self.samplerate)
        start_frame = min(start_frame, max(0, n - 1))
        end_frame = n
        if cue.trim_end and 0 < cue.trim_end <= cue.duration:
            end_frame = int(cue.trim_end * self.samplerate)
            end_frame = max(start_frame + 1, min(end_frame, n))
        # loop always wraps within [trim_start, trim_end), independent of seek start
        loop_start = int(max(0.0, cue.trim_start) * self.samplerate)
        loop_start = min(loop_start, max(0, end_frame - 1))
        voice = Voice(cue.id, cue.samples, self.samplerate, cue.volume,
                      start_frame, end_frame, loop=loop)
        voice.start_frame = loop_start   # loop point = trim start, even if we seeked in
        with self._lock:
            if self._active is not None:
                self._active.begin_fade_out(INTERRUPT_FADE)
                self._fading.append(self._active)
            self._active = voice

    def seek(self, seconds):
        """Setzt die Position des laufenden Cues. True wenn etwas lief."""
        with self._lock:
            v = self._active
            if v is None:
                return False
            frame = int(max(0.0, seconds) * self.samplerate)
            frame = min(frame, max(0, v.data.shape[0] - 1))
            v.pos = frame
            return True

    def stop(self, fade=INTERRUPT_FADE):
        """Blendet den aktiven Cue aus (Standard 0,5 s)."""
        with self._lock:
            if self._active is not None:
                self._active.begin_fade_out(fade)
                self._fading.append(self._active)
                self._active = None

    def panic(self):
        """Sofort-Stopp ohne Fade."""
        with self._lock:
            self._active = None
            self._fading = []

    def set_master(self, value):
        self.master = float(max(0.0, min(1.0, value)))

    def set_active_level(self, cue_id, level):
        """Live-Lautstärke des gerade laufenden Cues anpassen."""
        with self._lock:
            if self._active is not None and self._active.cue_id == cue_id:
                self._active.level = float(level)

    def set_active_loop(self, cue_id, loop):
        """Loop-Verhalten des gerade laufenden Cues live umschalten."""
        with self._lock:
            if self._active is not None and self._active.cue_id == cue_id:
                self._active.loop = bool(loop)

    def active_status(self):
        """(cue_id, position_frames, end_frame) des aktiven Cues oder None."""
        with self._lock:
            v = self._active
            if v is None:
                return None
            return (v.cue_id, v.pos, v.end_frame)
