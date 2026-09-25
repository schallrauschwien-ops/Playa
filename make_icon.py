"""
Erzeugt assets/playa.ico (Multi-Size) aus dem prozeduralen Palmen-Icon.
Wird von build.bat vor dem PyInstaller-Lauf aufgerufen, damit die EXE das
Palmen-Icon trägt. Benötigt PySide6 und Pillow (beide in requirements/Build-Env).
"""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # läuft auch ohne Display

import io
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QBuffer, QByteArray

from playa.assets import app_icon

SIZES = [16, 24, 32, 48, 64, 128, 256]


def main():
    app = QApplication([])
    icon = app_icon()

    from PIL import Image
    images = []
    for s in SIZES:
        pm = icon.pixmap(s, s)
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QBuffer.WriteOnly)
        pm.save(buf, "PNG")
        buf.close()
        img = Image.open(io.BytesIO(bytes(ba))).convert("RGBA")
        images.append(img)

    os.makedirs("assets", exist_ok=True)
    out = os.path.join("assets", "playa.ico")
    images[-1].save(out, format="ICO",
                    sizes=[(im.width, im.height) for im in images])
    print("Wrote", out)


if __name__ == "__main__":
    main()
