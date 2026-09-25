"""
Procedurally drawn assets for Playa (no binary files needed at runtime):

- palm_pixmap()      : the palm-on-an-island logo (matches the reference sketch)
- app_icon()         : QIcon for the window / taskbar
- follow_icon()      : downward arrow  (cue end -> play next)   ↓
- stop_icon()        : arrow into a bar (cue end -> stop)       →|

The arrow icons are drawn to match the user's hand sketch: a clean down-arrow
with a V head, and a rightward arrow with a V head running into a vertical bar.
"""

from __future__ import annotations
import math
from PySide6.QtGui import (
    QPixmap, QIcon, QPainter, QPen, QColor, QBrush, QPainterPath, QPolygonF
)
from PySide6.QtCore import Qt, QPointF, QRectF

INK = "#0d0f12"          # outline colour for the light icon
PALM_LINE = "#0f1722"


# --------------------------------------------------------------------------
# Palm tree (island + sun) — reference-sketch style, black line art
# --------------------------------------------------------------------------

def _draw_palm(p: QPainter, box: QRectF, line: QColor, water: bool, sun: bool):
    p.setRenderHint(QPainter.Antialiasing, True)
    w, h = box.width(), box.height()
    ox, oy = box.x(), box.y()

    stroke = max(1.5, w * 0.018)
    pen = QPen(line, stroke, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    # --- sun (open circle, upper right) ---
    if sun:
        r = w * 0.06
        p.drawEllipse(QPointF(ox + w * 0.82, oy + h * 0.20), r, r)

    # --- island mound ---
    base_y = oy + h * 0.80
    island = QPainterPath()
    island.moveTo(ox + w * 0.28, base_y)
    island.cubicTo(ox + w * 0.30, oy + h * 0.74,
                   ox + w * 0.44, oy + h * 0.73,
                   ox + w * 0.50, oy + h * 0.735)
    island.cubicTo(ox + w * 0.58, oy + h * 0.73,
                   ox + w * 0.70, oy + h * 0.74,
                   ox + w * 0.72, base_y)
    island.cubicTo(ox + w * 0.66, oy + h * 0.84,
                   ox + w * 0.34, oy + h * 0.84,
                   ox + w * 0.28, base_y)
    p.drawPath(island)

    # --- water lines (left & right) ---
    if water:
        for sx in (0.10, 0.78):
            for dy in (0.0, 0.05):
                y = oy + h * (0.80 + dy)
                path = QPainterPath()
                path.moveTo(ox + w * sx, y)
                path.quadTo(ox + w * (sx + 0.05), y - h * 0.012,
                            ox + w * (sx + 0.10), y)
                p.drawPath(path)

    # --- trunk (slightly leaning, segmented) ---
    crown = QPointF(ox + w * 0.50, oy + h * 0.20)
    foot = QPointF(ox + w * 0.49, oy + h * 0.74)
    trunk = QPainterPath()
    trunk.moveTo(foot.x() - stroke, foot.y())
    trunk.cubicTo(ox + w * 0.50, oy + h * 0.55,
                  ox + w * 0.515, oy + h * 0.38, crown.x(), crown.y())
    p.drawPath(trunk)
    trunk2 = QPainterPath()
    trunk2.moveTo(foot.x() + stroke, foot.y())
    trunk2.cubicTo(ox + w * 0.53, oy + h * 0.55,
                   ox + w * 0.545, oy + h * 0.38, crown.x() + stroke, crown.y())
    p.drawPath(trunk2)
    # trunk segment ticks
    for t in (0.30, 0.42, 0.54, 0.66):
        y = foot.y() - (foot.y() - crown.y()) * t
        xx = ox + w * (0.495 + 0.02 * (1 - t))
        seg = QPainterPath(); seg.moveTo(xx - stroke, y); seg.quadTo(xx, y + stroke, xx + stroke * 1.6, y)
        p.drawPath(seg)

    # --- fronds: full, arching leaves that lift then droop at the tips ---
    # Each frond is a closed leaf shape (lens) so it reads as a real palm leaf,
    # with serrated mid-rib ticks like the reference sketch.
    fronds = [
        (-158, 0.30, 0.55),
        (-132, 0.33, 0.60),
        (-108, 0.30, 0.62),
        (-84,  0.26, 0.55),
        (-72,  0.33, 0.62),
        (-48,  0.34, 0.62),
        (-22,  0.31, 0.58),
        (-2,   0.27, 0.52),
    ]
    for a, lf, droop in fronds:
        rad = math.radians(a)
        length = w * lf
        dirx, diry = math.cos(rad), math.sin(rad)
        tip = QPointF(crown.x() + dirx * length,
                      crown.y() + diry * length + h * droop * 0.18)
        c1 = QPointF(crown.x() + dirx * length * 0.45,
                     crown.y() + diry * length * 0.55 - h * 0.05)
        c2 = QPointF(crown.x() + dirx * length * 0.85,
                     crown.y() + diry * length * 0.85 - h * 0.005)
        px, py = -diry, dirx
        wsp = w * 0.028
        leaf = QPainterPath()
        leaf.moveTo(crown)
        leaf.cubicTo(QPointF(c1.x() + px * wsp, c1.y() + py * wsp),
                     QPointF(c2.x() + px * wsp * 0.6, c2.y() + py * wsp * 0.6), tip)
        leaf.cubicTo(QPointF(c2.x() - px * wsp * 0.6, c2.y() - py * wsp * 0.6),
                     QPointF(c1.x() - px * wsp, c1.y() - py * wsp), crown)
        p.drawPath(leaf)
        for s in (0.45, 0.66, 0.85):
            mt = 1 - s
            bx = (mt**3) * crown.x() + 3*(mt**2)*s*c1.x() + 3*mt*(s**2)*c2.x() + (s**3)*tip.x()
            by = (mt**3) * crown.y() + 3*(mt**2)*s*c1.y() + 3*mt*(s**2)*c2.y() + (s**3)*tip.y()
            p.drawLine(QPointF(bx, by), QPointF(bx + px * wsp * 0.8, by + py * wsp * 0.8))
            p.drawLine(QPointF(bx, by), QPointF(bx - px * wsp * 0.8, by - py * wsp * 0.8))


def palm_pixmap(size: int = 256, line_color: str = PALM_LINE,
                water: bool = True, sun: bool = True, top_pad: float = 0.0) -> QPixmap:
    """Render the palm. `top_pad` (0..0.3) shifts the drawing down to leave
    headroom for the fronds so they don't clip at the top edge."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    box = QRectF(0, size * top_pad, size, size)
    _draw_palm(p, box, QColor(line_color), water, sun)
    p.end()
    return pm


def app_icon() -> QIcon:
    """Window/taskbar icon: palm on a soft rounded badge."""
    icon = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(s, s)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, True)
        # rounded badge background (deep teal-night)
        p.setBrush(QBrush(QColor("#0e2a33")))
        p.setPen(Qt.NoPen)
        r = s * 0.18
        p.drawRoundedRect(QRectF(0, 0, s, s), r, r)
        _draw_palm(p, QRectF(s * 0.06, s * 0.06, s * 0.88, s * 0.88),
                   QColor("#7fe0a0"), water=False, sun=False)
        p.end()
        icon.addPixmap(pm)
    return icon


# --------------------------------------------------------------------------
# End-mode arrow icons (match the hand drawing)
# --------------------------------------------------------------------------

def _arrow_base(size: int) -> tuple[QPixmap, QPainter, float]:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    stroke = max(2.0, size * 0.09)
    return pm, p, stroke


def follow_icon(size: int = 28, color: str = "#27d65a") -> QIcon:
    """Downward arrow with a V head — 'play next cue after this one'."""
    pm, p, stroke = _arrow_base(size)
    pen = QPen(QColor(color), stroke, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    cx = size * 0.5
    top = size * 0.16
    bot = size * 0.80
    p.drawLine(QPointF(cx, top), QPointF(cx, bot))
    head = size * 0.20
    p.drawLine(QPointF(cx, bot), QPointF(cx - head, bot - head))
    p.drawLine(QPointF(cx, bot), QPointF(cx + head, bot - head))
    p.end()
    return QIcon(pm)


def stop_icon(size: int = 28, color: str = "#e0533d") -> QIcon:
    """Rightward arrow running into a vertical bar — 'stop at end of cue'."""
    pm, p, stroke = _arrow_base(size)
    pen = QPen(QColor(color), stroke, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    midy = size * 0.5
    x0 = size * 0.16
    x1 = size * 0.62          # arrow tip
    bar_x = size * 0.80
    # shaft
    p.drawLine(QPointF(x0, midy), QPointF(x1, midy))
    # V head
    head = size * 0.18
    p.drawLine(QPointF(x1, midy), QPointF(x1 - head, midy - head))
    p.drawLine(QPointF(x1, midy), QPointF(x1 - head, midy + head))
    # vertical bar
    p.drawLine(QPointF(bar_x, size * 0.24), QPointF(bar_x, size * 0.76))
    p.end()
    return QIcon(pm)


def loop_icon(size: int = 28, color: str = "#ffffff") -> QIcon:
    """A hand-drawn-style circular loop arrow (like the reference sketch):
    a near-full circle open at the top, with the arrowhead on the upper-left
    end pointing up and to the right."""
    from PySide6.QtCore import QRectF
    import math
    pm, p, stroke = _arrow_base(size)
    pen = QPen(QColor(color), stroke, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    cx, cy = size * 0.5, size * 0.53
    r = size * 0.28
    rect = QRectF(cx - r, cy - r, 2 * r, 2 * r)
    # gap at the top: tail on the upper-right (~65°), sweep clockwise around
    # to the upper-left (~115°). Qt angles: 0 = 3 o'clock, CCW positive.
    start_deg = 65
    end_deg = 115
    span_deg = -(360 - (end_deg - start_deg))   # clockwise the long way round
    p.drawArc(rect, int(start_deg * 16), int(span_deg * 16))
    # arrowhead at the upper-left end, pointing along the clockwise tangent
    end_ang = math.radians(end_deg)
    ex = cx + r * math.cos(end_ang)
    ey = cy - r * math.sin(end_ang)             # screen y inverted
    tip_dir = end_ang - math.pi / 2             # clockwise tangent -> up/right
    tx = ex + math.cos(tip_dir) * size * 0.10
    ty = ey - math.sin(tip_dir) * size * 0.10   # extend the tip a touch past the arc
    hlen = size * 0.20
    for off in (0.62, -0.62):                   # chevron opening backwards
        a = tip_dir + math.pi + off
        p.drawLine(QPointF(tx, ty),
                   QPointF(tx + hlen * math.cos(a), ty - hlen * math.sin(a)))
    p.end()
    return QIcon(pm)
