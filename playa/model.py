"""
Datenmodell und reine Sequencing-Logik für Playa.

Dieses Modul hat bewusst KEINE Audio- oder GUI-Abhängigkeiten, damit die
Ablauf-Logik (Follow / Stop / GO TO) isoliert getestet werden kann.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import itertools


class EndMode(str, Enum):
    """Was passiert, wenn ein Audio-Cue zu Ende gespielt ist."""
    FOLLOW = "follow"   # ▼  nächsten Cue automatisch starten
    STOP = "stop"       # ▶❘ anhalten
    LOOP = "loop"       # ⟳  diesen Cue wiederholen


_id_counter = itertools.count(1)


def _new_id() -> int:
    return next(_id_counter)


@dataclass
class AudioCue:
    kind: str = field(default="audio", init=False)
    id: int = field(default_factory=_new_id)
    name: str = ""
    path: str = ""
    # Wiedergabe-Parameter
    volume: float = 1.0            # 0.0 .. 1.0 (linear)
    trim_start: float = 0.0        # Sekunden ab Dateianfang
    trim_end: float = 0.0          # Sekunden ab Dateianfang; 0 oder >Dauer = bis Ende
    end_mode: EndMode = EndMode.STOP
    hotkey: str = ""               # z.B. "f5", "ctrl+1" (leer = keiner)
    # Wird beim Laden gefüllt (nicht serialisiert)
    duration: float = 0.0          # Gesamtlänge der Datei in Sekunden
    samples: object = None         # np.ndarray (n, 2) float32 @ engine-rate
    src_sr: int = 0                # ursprüngliche Samplerate
    peaks: object = None           # vorberechnete Hüllkurve fürs Wellenform-Bild
    load_error: str = ""           # falls Datei nicht geladen werden konnte

    @property
    def effective_end(self) -> float:
        """Effektiver Endpunkt in Sekunden (ab Dateianfang)."""
        if self.trim_end and 0 < self.trim_end <= self.duration:
            return self.trim_end
        return self.duration

    @property
    def play_duration(self) -> float:
        """Effektive Spieldauer zwischen Start- und End-Trim."""
        return max(0.0, self.effective_end - self.trim_start)

    def to_dict(self) -> dict:
        return {
            "kind": "audio",
            "name": self.name,
            "path": self.path,
            "volume": round(self.volume, 4),
            "trim_start": round(self.trim_start, 4),
            "trim_end": round(self.trim_end, 4),
            "end_mode": self.end_mode.value,
            "hotkey": self.hotkey,
        }

    @staticmethod
    def from_dict(d: dict) -> "AudioCue":
        return AudioCue(
            name=d.get("name", ""),
            path=d.get("path", ""),
            volume=float(d.get("volume", 1.0)),
            trim_start=float(d.get("trim_start", 0.0)),
            trim_end=float(d.get("trim_end", 0.0)),
            end_mode=EndMode(d.get("end_mode", "stop")),
            hotkey=d.get("hotkey", ""),
        )


@dataclass
class GoToCue:
    kind: str = field(default="goto", init=False)
    id: int = field(default_factory=_new_id)
    target: int = 1                # 1-basierte Cue-Nummer (wie in der Liste angezeigt)
    hotkey: str = ""

    @property
    def name(self) -> str:
        return f"GO TO {self.target}"

    def to_dict(self) -> dict:
        return {"kind": "goto", "target": int(self.target), "hotkey": self.hotkey}

    @staticmethod
    def from_dict(d: dict) -> "GoToCue":
        return GoToCue(target=int(d.get("target", 1)), hotkey=d.get("hotkey", ""))


# ---------------------------------------------------------------------------
# Reine Sequencing-Funktion – ohne Seiteneffekte, daher leicht testbar.
# ---------------------------------------------------------------------------

def resolve_play_target(items: list, index: int):
    """
    Folgt ab `index` der GO-TO-Kette und liefert (audio_index, new_playhead).

    - audio_index: Index des AudioCue, der tatsächlich abgespielt werden soll,
      oder None, wenn die Liste (ohne GO TO) zu Ende ist.
    - new_playhead: Position, an der der Playhead danach steht (für den
      nächsten GO-Befehl). Bei Listenende == len(items).

    Schutz gegen reine GO-TO-Schleifen ohne Audio dazwischen: nach mehr
    Sprüngen als Items vorhanden sind wird abgebrochen (audio_index=None).
    """
    n = len(items)
    jumps = 0
    while True:
        if index < 0 or index >= n:
            return None, n
        item = items[index]
        if item.kind == "audio":
            return index, index + 1
        # GO TO
        jumps += 1
        if jumps > n + 1:
            # Endlosschleife aus reinen GO-TOs -> sicher abbrechen
            return None, n
        index = item.target - 1  # 1-basiert -> 0-basiert
