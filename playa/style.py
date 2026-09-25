"""Design: dunkles Stylesheet + dezente Palme im Hintergrund (Referenz-Stil)."""

from __future__ import annotations
from PySide6.QtGui import QColor

QSS = """
* { font-family: 'Lato', 'Segoe UI', sans-serif; }
QMainWindow, QWidget#central { background: #131417; }
QWidget#central { background: transparent; }

QLabel { color: #d6dade; }
/* Playa keeps its own casual font, stays green, +10% larger */
QLabel#brand { font-family: 'Ink Free','Segoe Print','Comic Sans MS',cursive;
               font-size: 31px; font-weight: 800; letter-spacing: 2px; color: #5fd08a; }
QLabel#sub  { color: #565b62; font-size: 11px; letter-spacing: 3px; }
QLabel#bigtime { color: #dce0e5; font-size: 30px; font-weight: 700;
                 font-family: 'Consolas','Cascadia Mono',monospace; }
QLabel#dim { color: #8b9098; font-size: 12px; }

/* Transport — neutral greyscale hierarchy */
QPushButton#go {
    background: #34373c; color: #f2f4f6; font-size: 16px; font-weight: 800;
    letter-spacing: 6px; border: 1px solid #44484e; border-radius: 9px; padding: 10px;
}
QPushButton#go:hover { background: #3e4248; }
QPushButton#go:pressed { background: #2b2e33; }
QPushButton#go:disabled { background: #1b1d20; color: #4a4e54; border-color: #26282c; }

QPushButton#stop, QPushButton#schnitzel {
    border-radius: 9px; font-weight: 700; letter-spacing: 1px; font-size: 16px;
    padding: 10px; border: 1px solid #2c2f34; background: #1d1f22; color: #c2c7ce;
}
QPushButton#stop:hover, QPushButton#schnitzel:hover { background: #25282c; }
QPushButton#schnitzel { color: #e0b35a; border-color: #5a4a24; }

QPushButton.tool {
    background: #1d1f22; color: #c2c7ce; border: 1px solid #2c2f34;
    border-radius: 7px; padding: 7px 13px; font-weight: 600;
}
QPushButton.tool:hover { background: #25282c; }

/* Cue table — readable font, grey selection */
QTableWidget {
    background: transparent; border: 1px solid #232529; border-radius: 8px;
    gridline-color: transparent; color: #d6dade; font-size: 16px;
    font-family: 'Lato','Segoe UI',sans-serif;
    selection-background-color: rgba(210,216,222,0.16);
}
QTableWidget::item { padding: 6px 8px; border: none; }
QTableWidget::item:selected { color: #f2f4f6; }
QHeaderView::section {
    background: #16181b; color: #565b62; padding: 8px; border: none;
    border-bottom: 1px solid #232529; font-size: 10px; letter-spacing: 2px;
}
QTableWidget QTableCornerButton::section { background: #16181b; border: none; }
QLineEdit { font-family: 'Consolas','Segoe UI',monospace; font-size: 13px; }

QSlider::groove:horizontal { height: 4px; background: #2c2f34; border-radius: 2px; }
QSlider::handle:horizontal {
    width: 13px; height: 13px; margin: -5px 0; border-radius: 7px; background: #8b9098;
}
QSlider::handle:horizontal:hover { background: #d6dade; }
QSlider::sub-page:horizontal { background: #5a5f66; border-radius: 2px; }

QComboBox, QLineEdit, QSpinBox {
    background: #1d1f22; color: #d6dade; border: 1px solid #2c2f34;
    border-radius: 6px; padding: 5px 8px;
}
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView {
    background: #18191c; color: #d6dade; selection-background-color: #2c2f34;
    border: 1px solid #2c2f34;
}
QMenu { background: #18191c; color: #d6dade; border: 1px solid #2c2f34; }
QMenu::item:selected { background: #2c2f34; }
QMenuBar { background: #16181b; color: #b6bbc2; }
QMenuBar::item:selected { background: #2c2f34; }
QStatusBar { background: #16181b; color: #565b62; }
QScrollBar:vertical { background: transparent; width: 10px; }
QScrollBar::handle:vertical { background: #2c2f34; border-radius: 5px; min-height: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
"""


def draw_palm(painter, w, h):
    """Dezente Palmen-Silhouette unten rechts (Referenz-Stil, sehr transparent)."""
    from PySide6.QtCore import QRectF
    from .assets import _draw_palm
    painter.save()
    size = int(min(w, h) * 1.1)
    box = QRectF(w - size * 0.85, h - size * 1.02, size, size)
    # sehr dezent: leicht grünliches Grau, niedrige Deckkraft
    _draw_palm(painter, box, QColor(70, 110, 90, 18), water=True, sun=False)
    painter.restore()
