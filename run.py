"""
Playa — Startpunkt.

ASIO wird nur eingeschaltet, wenn die passende PortAudio-DLL wirklich da
ist. Das ausgelieferte Paket enthaelt sie nicht: die ASIO-Fassung steckt
voll Code aus Steinbergs ASIO-SDK, dessen Lizenz die Weitergabe
untersagt, und das vertraegt sich nicht mit der GPLv3, unter der Playa
steht. Ohne die DLL laeuft Playa ueber WASAPI und die uebrigen
Windows-Wege.

Wer ASIO braucht, holt sich die DLL von
https://github.com/spatialaudio/portaudio-binaries und legt sie nach
    Playa\\_internal\\_sounddevice_data\\portaudio-binaries\\
Beim naechsten Start wird sie von allein benutzt.

Die Pruefung muss hier oben stehen: SD_ENABLE_ASIO wirkt nur, wenn es
gesetzt ist, BEVOR sounddevice importiert wird.
"""

import os
import platform
import sys


def _asio_dll_name() -> str:
    """Wie die ASIO-Fassung der PortAudio-DLL auf diesem Rechner heisst."""
    if platform.machine().lower() in ("arm64", "aarch64"):
        return "libportaudioarm64-asio.dll"
    if sys.maxsize > 2 ** 32:
        return "libportaudio64bit-asio.dll"
    return "libportaudio32bit-asio.dll"


def _asio_vorhanden() -> bool:
    """True, wenn die ASIO-DLL an einer der Stellen liegt, wo sounddevice sucht."""
    if sys.platform != "win32":
        return False

    name = _asio_dll_name()
    orte = []

    # Im gepackten Programm liegt alles unter _internal.
    gepackt = getattr(sys, "_MEIPASS", None)
    if gepackt:
        orte.append(os.path.join(gepackt, "_sounddevice_data", "portaudio-binaries"))

    # Aus dem Quellcode heraus: dort, wo das Paket installiert ist.
    try:
        import _sounddevice_data
        orte.append(os.path.join(os.path.dirname(_sounddevice_data.__file__),
                                 "portaudio-binaries"))
    except Exception:
        pass

    # Falls jemand die DLL neben die exe gelegt hat.
    neben_exe = os.path.dirname(os.path.abspath(sys.argv[0]))
    orte.append(os.path.join(neben_exe, "_internal",
                             "_sounddevice_data", "portaudio-binaries"))
    orte.append(neben_exe)

    for ort in orte:
        try:
            if os.path.isfile(os.path.join(ort, name)):
                return True
        except Exception:
            continue
    return False


if _asio_vorhanden():
    os.environ.setdefault("SD_ENABLE_ASIO", "1")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from playa.main_window import MainWindow


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("Playa")
    from playa.resources import load_fonts
    load_fonts()
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
