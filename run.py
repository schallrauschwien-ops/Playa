"""
Playa — Startpunkt.

WICHTIG: SD_ENABLE_ASIO muss gesetzt sein, BEVOR sounddevice importiert wird.
Deshalb passiert das hier ganz oben, vor allen anderen Playa-Importen.
"""

import os
os.environ.setdefault("SD_ENABLE_ASIO", "1")   # ASIO-PortAudio-DLL aktivieren (nur Windows relevant)

import sys
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
