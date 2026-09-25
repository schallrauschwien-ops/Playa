"""
Globale Hotkeys (Stream-Deck-tauglich) über die 'keyboard'-Bibliothek.

Die keyboard-Callbacks laufen in einem eigenen Thread; das Signal wird per
Qt-Signal (QueuedConnection) sicher in den GUI-Thread gereicht.
"""

from __future__ import annotations
from PySide6.QtCore import QObject, Signal

try:
    import keyboard as _kb
    HAVE_KEYBOARD = True
except Exception:
    _kb = None
    HAVE_KEYBOARD = False


class HotkeyManager(QObject):
    triggered = Signal(int)   # cue_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._handles = {}    # cue_id -> keyboard handle
        self._combos = {}     # cue_id -> combo string

    @property
    def available(self) -> bool:
        return HAVE_KEYBOARD

    def set_bindings(self, bindings: dict):
        """
        bindings: {cue_id: "f5" / "ctrl+1" ...}. Registriert alles neu.
        Ungültige oder leere Kombinationen werden übersprungen.
        """
        self.clear()
        if not HAVE_KEYBOARD:
            return
        for cue_id, combo in bindings.items():
            combo = (combo or "").strip()
            if not combo:
                continue
            try:
                handle = _kb.add_hotkey(
                    combo,
                    lambda cid=cue_id: self.triggered.emit(cid),
                    suppress=False,
                )
                self._handles[cue_id] = handle
                self._combos[cue_id] = combo
            except Exception:
                # ungültige Kombination -> ignorieren, App läuft weiter
                pass

    def clear(self):
        if not HAVE_KEYBOARD:
            self._handles.clear()
            self._combos.clear()
            return
        for handle in self._handles.values():
            try:
                _kb.remove_hotkey(handle)
            except Exception:
                pass
        self._handles.clear()
        self._combos.clear()
