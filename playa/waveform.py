"""Waveform display with draggable start- and end-trim handles."""

from __future__ import annotations
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush


class WaveformWidget(QWidget):
    """Shows a cue's envelope and lets you drag the start and end points."""

    # emits (trim_start_seconds, trim_end_seconds)  (trim_end == duration means "to end")
    trimChanged = Signal(float, float)
    # emits seconds — clicking the waveform (not on a handle) requests playback there
    seekRequested = Signal(float)

    HANDLE_HIT = 9   # px tolerance to grab a handle

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(138)
        self.setMouseTracking(True)
        self._peaks = None
        self._duration = 0.0
        self._start = 0.0
        self._end = 0.0           # absolute seconds; == duration means full
        self._playpos = None
        self._drag = None         # 'start' | 'end' | None
        self._hover = None

    # ---- public API ----
    def set_cue(self, peaks, duration, trim_start, trim_end=0.0):
        self._peaks = peaks
        self._duration = max(0.0, float(duration))
        self._start = max(0.0, min(float(trim_start), self._duration))
        end = float(trim_end)
        if not end or end <= 0 or end > self._duration:
            end = self._duration
        self._end = max(self._start + 0.01, end)
        self._playpos = None
        self.update()

    def clear(self):
        self._peaks = None
        self._duration = 0.0
        self._start = 0.0
        self._end = 0.0
        self._playpos = None
        self.update()

    def set_playpos(self, seconds):
        self._playpos = seconds
        self.update()

    # ---- geometry ----
    def _x(self, t):
        if self._duration <= 0:
            return 0
        return int(t / self._duration * self.width())

    def _t(self, x):
        if self._duration <= 0 or self.width() <= 0:
            return 0.0
        return max(0.0, min(self._duration, x / self.width() * self._duration))

    def _which_handle(self, x):
        if self._peaks is None:
            return None
        if abs(x - self._x(self._start)) <= self.HANDLE_HIT:
            return "start"
        if abs(x - self._x(self._end)) <= self.HANDLE_HIT:
            return "end"
        return None

    # ---- mouse ----
    def mousePressEvent(self, e):
        if self._peaks is None:
            return
        if e.button() == Qt.LeftButton:
            x = e.position().x()
            h = self._which_handle(x)
            if h is not None:
                # grab a trim handle to drag it
                self._drag = h
                self._apply(x)
            else:
                # plain click -> request playback from this point (no handle move)
                self.seekRequested.emit(self._t(x))

    def mouseMoveEvent(self, e):
        if self._peaks is None:
            return
        if self._drag:
            self._apply(e.position().x())
        else:
            self._hover = self._which_handle(e.position().x())
            self.setCursor(Qt.SizeHorCursor if self._hover else Qt.ArrowCursor)
            self.update()

    def mouseReleaseEvent(self, e):
        if self._drag:
            self._drag = None
            self._emit()

    def _apply(self, x):
        t = self._t(x)
        if self._drag == "start":
            self._start = min(t, self._end - 0.01)
            self._start = max(0.0, self._start)
        else:
            self._end = max(t, self._start + 0.01)
            self._end = min(self._duration, self._end)
        self.update()
        self._emit()

    def _emit(self):
        # report end as duration when it's at the very end (means "no end trim")
        end = self._end if self._end < self._duration - 1e-4 else self._duration
        self.trimChanged.emit(self._start, end)

    # ---- painting ----
    RULER_H = 20   # bottom strip reserved for the time ruler

    def _fmt(self, s):
        s = max(0, int(round(s)))
        return f"{s // 60:d}:{s % 60:02d}"

    def _tick_interval(self, duration):
        target = max(0.001, duration / 7.0)
        for n in (1, 2, 5, 10, 15, 20, 30, 60, 120, 300, 600, 900, 1800, 3600):
            if n >= target:
                return n
        return 3600

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        wave_h = max(20, h - self.RULER_H)
        mid = wave_h / 2

        p.fillRect(self.rect(), QColor("#121315"))
        p.setPen(QPen(QColor("#26282c"), 1))
        p.drawLine(0, int(mid), w, int(mid))

        if self._peaks is None or self._duration <= 0:
            p.setPen(QColor("#4a4e54"))
            p.drawText(self.rect(), Qt.AlignCenter, "No waveform")
            return

        buckets = self._peaks.shape[0]
        sx = self._x(self._start)
        ex = self._x(self._end)

        for x in range(w):
            bi = int(x / w * buckets)
            if bi >= buckets:
                bi = buckets - 1
            lo = self._peaks[bi, 0]
            hi = self._peaks[bi, 1]
            y1 = mid - hi * (mid - 4)
            y2 = mid - lo * (mid - 4)
            inside = (sx <= x <= ex)
            p.setPen(QPen(QColor("#5fd08a") if inside else QColor("#33453c"), 1))
            p.drawLine(x, int(y1), x, int(y2))

        # dim the trimmed-off regions (before start, after end)
        if sx > 0:
            p.fillRect(QRectF(0, 0, sx, wave_h), QColor(8, 9, 11, 165))
        if ex < w:
            p.fillRect(QRectF(ex, 0, w - ex, wave_h), QColor(8, 9, 11, 165))

        # playback cursor
        if self._playpos is not None and self._playpos >= 0:
            px = self._x(self._playpos)
            p.setPen(QPen(QColor("#e8edf2"), 1))
            p.drawLine(px, 0, px, wave_h)

        # ---- time ruler ----
        ry = wave_h
        p.setPen(QPen(QColor("#2c2f34"), 1))
        p.drawLine(0, ry, w, ry)
        interval = self._tick_interval(self._duration)
        f = p.font(); f.setPointSize(7); p.setFont(f)
        t = 0.0
        while t <= self._duration + 1e-6:
            x = self._x(t)
            p.setPen(QPen(QColor("#3a3f46"), 1))
            p.drawLine(x, ry, x, ry + 4)
            p.setPen(QColor("#7d828a"))
            label = self._fmt(t)
            tw = p.fontMetrics().horizontalAdvance(label)
            lx = min(max(0, x - tw // 2), w - tw)
            p.drawText(lx, ry + self.RULER_H - 4, label)
            t += interval
        # total length at the far right
        total = self._fmt(self._duration)
        p.setPen(QColor("#9aa1aa"))
        tw = p.fontMetrics().horizontalAdvance(total)
        p.drawText(w - tw - 2, ry - 4, total)

        # handles (full height)
        self._draw_handle(p, sx, h, self._hover == "start" or self._drag == "start", left=True)
        self._draw_handle(p, ex, h, self._hover == "end" or self._drag == "end", left=False)

    def _draw_handle(self, p, x, h, active, left):
        col = QColor("#ffffff") if active else QColor("#9aa1aa")
        p.setPen(QPen(col, 2))
        p.drawLine(x, 0, x, h)
        p.setBrush(QBrush(col)); p.setPen(Qt.NoPen)
        if left:
            p.drawPolygon([QPointF(x, 0), QPointF(x + 9, 0), QPointF(x, 10)])
        else:
            p.drawPolygon([QPointF(x, 0), QPointF(x - 9, 0), QPointF(x, 10)])
