"""Locating bundled resources (fonts, icon) in both dev and PyInstaller builds."""

from __future__ import annotations
import os
import sys


def resource_path(*parts) -> str:
    """Absolute path to a bundled resource.

    Works when running from source (repo root) and when frozen by PyInstaller
    (files live under sys._MEIPASS).
    """
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        # repo root = parent of this package directory
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def load_fonts() -> str:
    """Register bundled Lato fonts with Qt. Returns the family name to use
    ('Lato' if loaded, else a safe fallback)."""
    from PySide6.QtGui import QFontDatabase
    family = None
    for fname in ("Lato-Regular.ttf", "Lato-Bold.ttf", "Lato-Black.ttf"):
        path = resource_path("assets", "fonts", fname)
        if os.path.exists(path):
            fid = QFontDatabase.addApplicationFont(path)
            if fid != -1:
                fams = QFontDatabase.applicationFontFamilies(fid)
                if fams:
                    family = fams[0]
    return family or "Lato"
