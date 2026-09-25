"""Playa main window: ties model, audio engine, waveform and hotkeys together."""

from __future__ import annotations
import json
import os

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QSlider, QLineEdit, QSpinBox,
    QFileDialog, QMessageBox, QAbstractItemView, QStatusBar,
)
from PySide6.QtCore import Qt, QTimer, QSize, Signal, QSettings
from PySide6.QtGui import QPainter, QAction, QColor, QActionGroup, QPixmap

from .model import AudioCue, GoToCue, EndMode, resolve_play_target
from .audio_engine import AudioEngine, load_audio
from .waveform import WaveformWidget
from .hotkeys import HotkeyManager
from .style import QSS, draw_palm
from .assets import app_icon, palm_pixmap, follow_icon, stop_icon, loop_icon
from .resources import resource_path
from . import __version__, __build__

AUDIO_FILTER = ("Audio (*.wav *.flac *.ogg *.aiff *.aif *.mp3 *.m4a *.mp4 *.aac);;"
                "All files (*.*)")
SHOW_FILTER = "Playa show (*.playa);;All files (*.*)"

COL_NUM, COL_NAME, COL_VOL, COL_TIME, COL_MODE, COL_HOTKEY = range(6)
ROW_HEIGHT = 42


def fmt_time(s: float) -> str:
    if s is None or s < 0:
        return "--:--"
    s = int(round(s))
    return f"{s // 60:02d}:{s % 60:02d}"


class CueTable(QTableWidget):
    """Cue list with custom mouse drag-to-reorder and external audio-file drops.

    We deliberately do NOT use Qt's InternalMove: with cell widgets it moves the
    row itself in addition to our rebuild, which duplicated cell contents. Instead
    we track the drag manually and only reorder the backing list, then rebuild.
    """

    rowsReordered = Signal(int, int)   # source_row, target_row
    filesDropped = Signal(list)        # list of local file paths

    def __init__(self, rows, cols, parent=None):
        super().__init__(rows, cols, parent)
        self.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.setAcceptDrops(True)          # still accept external file drops
        self._press_row = -1
        self._press_pos = None
        self._dragging = False

    # ---- custom row drag ----
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            idx = self.indexAt(e.position().toPoint())
            self._press_row = idx.row() if idx.isValid() else -1
            self._press_pos = e.position().toPoint()
            self._dragging = False
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._press_row >= 0 and (e.buttons() & Qt.LeftButton):
            if not self._dragging and self._press_pos is not None:
                if (e.position().toPoint() - self._press_pos).manhattanLength() > 8:
                    self._dragging = True
                    self.setCursor(Qt.ClosedHandCursor)
            if self._dragging:
                return   # suppress rubber-band selection while reordering
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._dragging and self._press_row >= 0:
            idx = self.indexAt(e.position().toPoint())
            target = idx.row() if idx.isValid() else self.rowCount() - 1
            src = self._press_row
            self.unsetCursor()
            self._dragging = False
            self._press_row = -1
            if target >= 0 and target != src:
                self.rowsReordered.emit(src, target)
            return
        self._press_row = -1
        self._dragging = False
        super().mouseReleaseEvent(e)

    # ---- external file drops ----
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
            if paths:
                self.filesDropped.emit(paths)
                e.acceptProposedAction()


class SchnitzelOverlay(QWidget):
    """A full-area overlay that shows the schnitzel. Click it to dismiss.
    Purely cosmetic — it never touches audio."""
    def __init__(self, parent, pixmap):
        super().__init__(parent)
        self._pm = pixmap
        self.setCursor(Qt.PointingHandCursor)
        self.hide()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.fillRect(self.rect(), QColor(0, 0, 0, 190))
        if self._pm is not None and not self._pm.isNull():
            maxw = int(self.width() * 0.72)
            maxh = int(self.height() * 0.72)
            scaled = self._pm.scaled(maxw, maxh, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)
            p.setPen(QColor(255, 255, 255, 130))
            p.drawText(0, y + scaled.height() + 22, self.width(), 20,
                       Qt.AlignHCenter, "(click to dismiss)")

    def mousePressEvent(self, e):
        self.hide()


class CentralWidget(QWidget):
    """Central area with a faint palm in the background."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("central")

    def paintEvent(self, ev):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#0d0f12"))
        draw_palm(p, self.width(), self.height())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Playa v{__version__}")
        self.setWindowIcon(app_icon())
        self.resize(1040, 740)
        self.setStyleSheet(QSS)

        self.items = []                # AudioCue | GoToCue
        self.playhead = 0              # index of the standing (ready) cue
        self.current_cue_id = None     # id of the cue currently playing
        self.show_path = None
        self._undo_stack = []          # snapshots for Undo (structural changes)
        self.settings = QSettings("Playa", "Playa")   # persists recent projects

        self.engine = AudioEngine()
        self.hotkeys = HotkeyManager(self)
        self.hotkeys.triggered.connect(self.on_hotkey)

        self._build_ui()
        self._build_menu()

        # cosmetic schnitzel overlay (does not affect audio)
        self.schnitzel = SchnitzelOverlay(self.centralWidget(),
                                          QPixmap(resource_path("assets", "schnitzel.png")))

        self.setAcceptDrops(True)
        # Catch transport keys at application level so the table can't swallow them
        from PySide6.QtWidgets import QApplication
        QApplication.instance().installEventFilter(self)

        self.poll = QTimer(self)
        self.poll.setInterval(40)
        self.poll.timeout.connect(self._tick)
        self.poll.start()

        self._open_default_device()
        self._refresh_table()
        self._update_waveform()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        central = CentralWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(12)

        # Header: palm logo + title, big countdown, master
        head = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(palm_pixmap(64, "#5fd08a", water=False, sun=False, top_pad=0.16))
        logo.setFixedSize(66, 66)
        head.addWidget(logo)

        title_box = QVBoxLayout(); title_box.setSpacing(0)
        brand = QLabel("Playa"); brand.setObjectName("brand")
        sub = QLabel(f"AUDIO SHOW CONTROL · v{__version__}"); sub.setObjectName("sub")
        title_box.addWidget(brand); title_box.addWidget(sub)
        head.addLayout(title_box)
        head.addStretch(1)

        self.big_time = QLabel("--:--"); self.big_time.setObjectName("bigtime")
        head.addWidget(self.big_time)
        head.addSpacing(20)

        mvbox = QVBoxLayout(); mvbox.setSpacing(2)
        ml = QLabel("MASTER"); ml.setObjectName("sub")
        self.master = QSlider(Qt.Horizontal); self.master.setRange(0, 100)
        self.master.setValue(100); self.master.setFixedWidth(130)
        self.master.valueChanged.connect(self._on_master)
        mvbox.addWidget(ml); mvbox.addWidget(self.master)
        head.addLayout(mvbox)
        root.addLayout(head)

        # Transport
        tr = QHBoxLayout(); tr.setSpacing(10)
        self.go_btn = QPushButton("GO"); self.go_btn.setObjectName("go")
        self.go_btn.clicked.connect(self.go)
        self.stop_btn = QPushButton("STOP"); self.stop_btn.setObjectName("stop")
        self.stop_btn.setFixedWidth(120); self.stop_btn.clicked.connect(self.stop)
        self.schnitzel_btn = QPushButton("SCHNITZEL"); self.schnitzel_btn.setObjectName("schnitzel")
        self.schnitzel_btn.setFixedWidth(148); self.schnitzel_btn.clicked.connect(self.toggle_schnitzel)
        tr.addWidget(self.go_btn, 1)
        tr.addWidget(self.stop_btn)
        tr.addWidget(self.schnitzel_btn)
        root.addLayout(tr)

        # Cue table
        self.table = CueTable(0, 6)
        self.table.setHorizontalHeaderLabels(["#", "NAME", "VOLUME", "TIME", "END", "HOTKEY"])
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(COL_NUM, QHeaderView.Fixed)
        hh.setSectionResizeMode(COL_NAME, QHeaderView.Stretch)
        hh.setSectionResizeMode(COL_VOL, QHeaderView.Fixed)
        hh.setSectionResizeMode(COL_TIME, QHeaderView.Fixed)
        hh.setSectionResizeMode(COL_MODE, QHeaderView.Fixed)
        hh.setSectionResizeMode(COL_HOTKEY, QHeaderView.Fixed)
        self.table.setColumnWidth(COL_NUM, 44)
        self.table.setColumnWidth(COL_VOL, 150)
        self.table.setColumnWidth(COL_TIME, 88)
        self.table.setColumnWidth(COL_MODE, 64)
        self.table.setColumnWidth(COL_HOTKEY, 120)
        self.table.itemSelectionChanged.connect(self._on_select)
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.cellDoubleClicked.connect(self._on_double_click)
        self.table.rowsReordered.connect(self._on_rows_reordered)
        self.table.filesDropped.connect(self._add_paths)
        self.table.viewport().setAutoFillBackground(False)
        root.addWidget(self.table, 1)

        # Waveform (no caption above it)
        self.wave = WaveformWidget()
        self.wave.trimChanged.connect(self._on_trim)
        self.wave.seekRequested.connect(self._on_seek)
        root.addWidget(self.wave)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(f"Playa v{__version__} (build {__build__}) — ready")

    def _build_menu(self):
        m = self.menuBar()
        filem = m.addMenu("File")
        a_open = QAction("Open show…", self); a_open.setShortcut("Ctrl+O")
        a_open.triggered.connect(self.open_show); filem.addAction(a_open)
        self.recent_menu = filem.addMenu("Recent projects")
        self._rebuild_recent_menu()
        a_save = QAction("Save show", self); a_save.setShortcut("Ctrl+S")
        a_save.triggered.connect(self.save_show); filem.addAction(a_save)
        a_saveas = QAction("Save show as…", self)
        a_saveas.triggered.connect(lambda: self.save_show(True)); filem.addAction(a_saveas)
        filem.addSeparator()
        a_quit = QAction("Quit", self); a_quit.triggered.connect(self.close)
        filem.addAction(a_quit)

        editm = m.addMenu("Edit")
        self.a_undo = QAction("Undo", self); self.a_undo.setShortcut("Ctrl+Z")
        self.a_undo.setEnabled(False)
        self.a_undo.triggered.connect(self.undo); editm.addAction(self.a_undo)

        cuem = m.addMenu("Cues")
        a_add = QAction("Add audio…", self); a_add.setShortcut("Ctrl+I")
        a_add.triggered.connect(self.add_audio); cuem.addAction(a_add)
        a_goto = QAction("Insert GO TO", self)
        a_goto.triggered.connect(self.add_goto); cuem.addAction(a_goto)
        cuem.addSeparator()
        a_del = QAction("Remove cue", self); a_del.setShortcut("Del")
        a_del.triggered.connect(self.remove_selected); cuem.addAction(a_del)
        a_up = QAction("Move up", self); a_up.setShortcut("Ctrl+Up")
        a_up.triggered.connect(lambda: self.move_selected(-1)); cuem.addAction(a_up)
        a_down = QAction("Move down", self); a_down.setShortcut("Ctrl+Down")
        a_down.triggered.connect(lambda: self.move_selected(1)); cuem.addAction(a_down)

        self.devm = m.addMenu("Audio device")
        self._rebuild_device_menu()

    def _rebuild_device_menu(self):
        self.devm.clear()
        group = QActionGroup(self); group.setExclusive(True)
        try:
            devices = self.engine.list_devices()
        except Exception as e:
            act = QAction(f"(No devices found: {e})", self); act.setEnabled(False)
            self.devm.addAction(act); return
        order = {"ASIO": 0, "Windows WASAPI": 1, "Windows WDM-KS": 2, "MME": 3}
        devices.sort(key=lambda d: (order.get(d[2], 9), d[2], d[1]))
        last_api = None
        for idx, name, api, ch in devices:
            if api != last_api:
                hdr = QAction(f"— {api} —", self); hdr.setEnabled(False)
                self.devm.addAction(hdr); last_api = api
            act = QAction(f"{name}  ({ch}ch)", self); act.setCheckable(True)
            act.setChecked(idx == self.engine.device)
            act.triggered.connect(lambda checked, i=idx: self._select_device(i))
            group.addAction(act); self.devm.addAction(act)

    # ----------------------------------------------------- device / engine
    def _open_default_device(self):
        try:
            sr = self.engine.open(device=None)
            self.statusBar().showMessage(f"Audio device ready · {sr} Hz")
        except Exception as e:
            self.statusBar().showMessage(f"No audio device: {e}")

    def _select_device(self, index):
        try:
            sr = self.engine.open(device=index)
        except Exception as e:
            QMessageBox.warning(self, "Audio device", f"Could not open device:\n{e}")
            self._open_default_device()
            self._rebuild_device_menu()
            return
        self.statusBar().showMessage(f"Device changed · {sr} Hz · reloading cues…")
        self._reprepare_all()
        self._rebuild_device_menu()
        self.statusBar().showMessage(f"Ready · {sr} Hz")

    def _reprepare_all(self):
        for cue in self.items:
            if cue.kind == "audio":
                self._prepare_cue(cue)
        self._refresh_table()
        self._update_waveform()

    def _prepare_cue(self, cue: AudioCue):
        try:
            data, src_sr, dur, peaks = load_audio(cue.path, self.engine.samplerate)
            cue.samples, cue.src_sr, cue.duration, cue.peaks = data, src_sr, dur, peaks
            cue.load_error = ""
            if cue.trim_start > dur:
                cue.trim_start = 0.0
        except Exception as e:
            cue.samples = None; cue.peaks = None; cue.duration = 0.0
            cue.load_error = str(e)

    # ----------------------------------------------------------- cue actions
    AUDIO_EXTS = (".wav", ".flac", ".ogg", ".aiff", ".aif", ".mp3",
                  ".m4a", ".mp4", ".aac")

    def add_audio(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Add audio", "", AUDIO_FILTER)
        if paths:
            self._add_paths(paths)

    def _add_paths(self, paths):
        audio = [p for p in paths if p.lower().endswith(self.AUDIO_EXTS)]
        if not audio:
            self.statusBar().showMessage("No supported audio files"); return
        self._push_undo()
        for p in audio:
            cue = AudioCue(name=os.path.splitext(os.path.basename(p))[0], path=p)
            self._prepare_cue(cue)
            self.items.append(cue)
        self._refresh_table(); self._reregister_hotkeys(); self._update_waveform()
        self.statusBar().showMessage(f"{len(audio)} cue(s) added")

    def add_goto(self):
        self._push_undo()
        row = self._selected_row()
        goto = GoToCue(target=1)
        if row is None:
            self.items.append(goto)
            new_row = len(self.items) - 1
        else:
            new_row = row + 1
            self.items.insert(new_row, goto)
        self._refresh_table(); self._reregister_hotkeys()
        self.table.selectRow(new_row)

    def _on_rows_reordered(self, source, target):
        if source == target or not (0 <= source < len(self.items)):
            return
        self._push_undo()
        moved = self.items[source]
        moved_id = moved.id
        self.items.pop(source)
        if target < 0:
            target = len(self.items)
        target = min(target, len(self.items))
        self.items.insert(target, moved)
        # keep the playhead on the same cue it pointed at, if possible
        new_index = self.items.index(moved)
        self.playhead = new_index if self.playhead == source else \
            min(self.playhead, max(0, len(self.items) - 1))
        self._refresh_table(); self._reregister_hotkeys(); self._update_waveform()
        self.table.selectRow(new_index)
        self.statusBar().showMessage("Cue moved")

    def remove_selected(self):
        rows = sorted({ix.row() for ix in self.table.selectionModel().selectedRows()},
                      reverse=True)
        if not rows:
            r = self.table.currentRow()
            if r < 0:
                return
            rows = [r]
        self._push_undo()
        for r in rows:
            if 0 <= r < len(self.items):
                if self.items[r].id == self.current_cue_id:
                    self.engine.stop(); self.current_cue_id = None
                del self.items[r]
        # keep the armed cue on a valid index
        self.playhead = min(self.playhead, len(self.items) - 1) if self.items else 0
        self._refresh_table(); self._reregister_hotkeys(); self._update_waveform()
        self.statusBar().showMessage(f"Removed {len(rows)} cue(s)")

    def move_selected(self, delta):
        row = self._selected_row()
        if row is None:
            return
        new = row + delta
        if 0 <= new < len(self.items):
            self._push_undo()
            self.items[row], self.items[new] = self.items[new], self.items[row]
            self._refresh_table()
            self.table.selectRow(new)

    # ------------------------------------------------------------------ undo
    def _push_undo(self):
        """Snapshot the cue list before a structural change (keeps loaded audio)."""
        self._undo_stack.append((list(self.items), self.playhead, self.current_cue_id))
        if len(self._undo_stack) > 8:
            self._undo_stack.pop(0)
        if hasattr(self, "a_undo"):
            self.a_undo.setEnabled(True)

    def undo(self):
        if not self._undo_stack:
            self.statusBar().showMessage("Nothing to undo"); return
        items, playhead, cur = self._undo_stack.pop()
        self.items = items
        self.playhead = min(playhead, max(0, len(self.items) - 1))
        # only keep current_cue_id if that cue still exists
        self.current_cue_id = cur if any(it.id == cur for it in self.items) else self.current_cue_id
        self._refresh_table(); self._reregister_hotkeys(); self._update_waveform()
        self._select_playhead()
        if hasattr(self, "a_undo"):
            self.a_undo.setEnabled(bool(self._undo_stack))
        self.statusBar().showMessage("Undo")

    # --------------------------------------------------------- drag and drop
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = []
        for url in e.mimeData().urls():
            if url.isLocalFile():
                paths.append(url.toLocalFile())
        if paths:
            self._add_paths(paths)
            e.acceptProposedAction()

    # -------------------------------------------------- application key filter
    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.KeyPress and self.isActiveWindow() and not self._editing():
            key = event.key()
            if key == Qt.Key_Space:
                self.go(); return True
            if key == Qt.Key_Escape:
                self.stop(); return True
        return super().eventFilter(obj, event)

    # --------------------------------------------------------------- table
    def _refresh_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.items))
        for r, item in enumerate(self.items):
            self.table.setRowHeight(r, ROW_HEIGHT)
            num = QTableWidgetItem(str(r + 1))
            num.setTextAlignment(Qt.AlignCenter)
            num.setFlags(num.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(r, COL_NUM, num)

            if item.kind == "audio":
                name = QTableWidgetItem(item.name)
                if item.load_error:
                    name.setForeground(QColor("#e0533d"))
                    name.setText(f"⚠ {item.name}  (file missing)")
                self.table.setItem(r, COL_NAME, name)

                sl = QSlider(Qt.Horizontal); sl.setRange(0, 100)
                sl.setValue(int(round(item.volume * 100)))
                sl.valueChanged.connect(lambda v, it=item: self._on_volume(it, v))
                self.table.setCellWidget(r, COL_VOL, sl)

                t = QTableWidgetItem(fmt_time(item.play_duration))
                t.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                t.setFlags(t.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(r, COL_TIME, t)

                mb = QPushButton()
                self._style_mode_button(mb, item.end_mode)
                mb.setFixedSize(50, 28)
                mb.clicked.connect(lambda _=False, it=item: self._toggle_mode(it))
                self.table.setCellWidget(r, COL_MODE, mb)

                hk = QLineEdit(item.hotkey); hk.setPlaceholderText("—")
                hk.setMinimumHeight(28); hk.setAlignment(Qt.AlignCenter)
                hk.editingFinished.connect(lambda e=hk, it=item: self._on_hotkey_edit(it, e.text()))
                self.table.setCellWidget(r, COL_HOTKEY, hk)
            else:
                name = QTableWidgetItem(f"↪  GO TO  {item.target}")
                name.setForeground(QColor("#8a93a0"))
                name.setFlags(name.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(r, COL_NAME, name)
                sp = QSpinBox(); sp.setRange(1, 999); sp.setValue(item.target)
                sp.setPrefix("→ "); sp.valueChanged.connect(lambda v, it=item: self._on_goto_target(it, v))
                self.table.setCellWidget(r, COL_VOL, sp)
                self.table.setItem(r, COL_TIME, QTableWidgetItem(""))
                self.table.removeCellWidget(r, COL_MODE)
                hk = QLineEdit(item.hotkey); hk.setPlaceholderText("—")
                hk.setMinimumHeight(28); hk.setAlignment(Qt.AlignCenter)
                hk.editingFinished.connect(lambda e=hk, it=item: self._on_hotkey_edit(it, e.text()))
                self.table.setCellWidget(r, COL_HOTKEY, hk)
        self.table.blockSignals(False)
        self.go_btn.setEnabled(len(self.items) > 0)
        self._refresh_highlight()

    def _style_mode_button(self, btn, mode):
        btn.setStyleSheet(
            "QPushButton{background:#101113;border:1px solid #3a3f46;border-radius:6px;}"
            "QPushButton:hover{background:#1b1d20;border-color:#5a5f66;}"
        )
        if mode == EndMode.FOLLOW:
            btn.setIcon(follow_icon(26, "#ffffff"))
            btn.setToolTip("Follow: automatically start the next cue")
        elif mode == EndMode.LOOP:
            btn.setIcon(loop_icon(26, "#ffffff"))
            btn.setToolTip("Loop: repeat this cue until you start another or stop")
        else:
            btn.setIcon(stop_icon(26, "#ffffff"))
            btn.setToolTip("Stop: stop after this cue")
        btn.setIconSize(QSize(26, 26))

    def _refresh_highlight(self):
        from PySide6.QtGui import QFont
        base = self.table.font().pointSize()
        if base <= 0:
            base = 11
        note_font = QFont(self.table.font()); note_font.setPointSize(int(base * 1.55)); note_font.setBold(True)
        next_font = QFont(self.table.font()); next_font.setPointSize(int(base * 1.35)); next_font.setBold(True)
        plain_font = QFont(self.table.font())
        for r in range(self.table.rowCount()):
            item = self.items[r]
            playing = (item.id == self.current_cue_id)
            standing = (r == self.playhead)
            nm = self.table.item(r, COL_NAME)
            num = self.table.item(r, COL_NUM)
            if num is not None:
                if playing:
                    num.setText("♪")
                    num.setForeground(QColor("#5fd08a"))
                    num.setFont(note_font)
                elif standing:
                    num.setText("▶")
                    num.setForeground(QColor("#ffffff"))
                    num.setFont(next_font)
                else:
                    num.setText(str(r + 1))
                    num.setForeground(QColor("#7d828a"))
                    num.setFont(plain_font)
            if nm is None:
                continue
            if standing:
                # clearest: strong light bar across the row
                nm.setBackground(QColor(255, 255, 255, 38))
            elif playing:
                nm.setBackground(QColor(255, 255, 255, 20))
            else:
                nm.setBackground(QColor(0, 0, 0, 0))

    def _select_playhead(self):
        """Move the row selection to the standing cue so the marker follows GO."""
        if 0 <= self.playhead < self.table.rowCount():
            self.table.blockSignals(True)
            self.table.selectRow(self.playhead)
            self.table.blockSignals(False)

    # ----------------------------------------------------------- callbacks
    def _on_master(self, v):
        self.engine.set_master(v / 100.0)

    def _on_volume(self, item, v):
        item.volume = v / 100.0
        self.engine.set_active_level(item.id, item.volume)

    def _toggle_mode(self, item):
        order = [EndMode.STOP, EndMode.FOLLOW, EndMode.LOOP]
        try:
            nxt = order[(order.index(item.end_mode) + 1) % len(order)]
        except ValueError:
            nxt = EndMode.FOLLOW
        item.end_mode = nxt
        r = self.items.index(item)
        btn = self.table.cellWidget(r, COL_MODE)
        if btn:
            self._style_mode_button(btn, item.end_mode)
        # if this cue is currently playing, apply loop change live
        if item.id == self.current_cue_id:
            self.engine.set_active_loop(item.id, item.end_mode == EndMode.LOOP)

    def _on_goto_target(self, item, v):
        item.target = int(v)
        r = self.items.index(item)
        nm = self.table.item(r, COL_NAME)
        if nm:
            nm.setText(f"↪  GO TO  {item.target}")

    def _on_hotkey_edit(self, item, text):
        item.hotkey = text.strip()
        self._reregister_hotkeys()

    def _on_item_changed(self, titem):
        if titem.column() == COL_NAME:
            r = titem.row()
            if 0 <= r < len(self.items) and self.items[r].kind == "audio":
                self.items[r].name = titem.text()

    def _on_double_click(self, row, col):
        if col == COL_NAME:
            return
        self.fire_index(row)

    def _on_select(self):
        # selecting a row makes it the standing (ready) cue and shows its waveform
        row = self._selected_row()
        if row is not None:
            self.playhead = row
            self._refresh_highlight()
        self._update_waveform()

    def _on_seek(self, seconds):
        cue = self._waveform_cue()
        if cue is None or cue.kind != "audio" or cue.samples is None:
            return
        if self.current_cue_id == cue.id and self.engine.seek(seconds):
            # already playing this cue -> jump live
            self.wave.set_playpos(seconds)
        else:
            # not playing -> start this cue from the clicked point
            self.engine.play(cue, start_override=seconds)
            self.current_cue_id = cue.id
            self.statusBar().showMessage(f"▶ {cue.name} (from {fmt_time(seconds)})")
            self._refresh_highlight()

    def _on_trim(self, start, end):
        cue = self._waveform_cue()
        if cue is not None and cue.kind == "audio":
            cue.trim_start = start
            cue.trim_end = 0.0 if end >= cue.duration - 1e-4 else end
            r = self.items.index(cue)
            t = self.table.item(r, COL_TIME)
            if t:
                t.setText(fmt_time(cue.play_duration))

    # ---- waveform always reflects the current cue (playing, else standing) ----
    def _waveform_cue(self):
        if self.current_cue_id is not None:
            for it in self.items:
                if it.id == self.current_cue_id and it.kind == "audio":
                    return it
        if 0 <= self.playhead < len(self.items) and self.items[self.playhead].kind == "audio":
            return self.items[self.playhead]
        # otherwise first audio cue, if any
        for it in self.items:
            if it.kind == "audio":
                return it
        return None

    def _update_waveform(self):
        cue = self._waveform_cue()
        if cue is not None and cue.peaks is not None:
            self.wave.set_cue(cue.peaks, cue.duration, cue.trim_start, cue.trim_end)
        else:
            self.wave.clear()

    # ----------------------------------------------------------- sequencing
    def go(self):
        # GO / Space only ever STARTS a cue, it never stops playback.
        if not self.items:
            return
        ai, _ = resolve_play_target(self.items, self.playhead)
        if ai is None:
            self.statusBar().showMessage("End of list — nothing to start")
            return
        self.fire_index(self.playhead)

    def fire_index(self, index):
        ai, ph = resolve_play_target(self.items, index)
        if ai is None:
            # reached end of list with nothing playable -> keep last cue armed,
            # do NOT stop whatever may be playing (GO never stops)
            if self.items:
                self.playhead = len(self.items) - 1
            self.current_cue_id = None
            self._refresh_highlight(); self._select_playhead(); self._update_waveform()
            return
        cue = self.items[ai]
        if cue.samples is None:
            self.statusBar().showMessage(f"⚠ '{cue.name}' not loaded")
            self.current_cue_id = None
        else:
            self.engine.play(cue)
            self.current_cue_id = cue.id
            self.statusBar().showMessage(f"▶ {cue.name}")
        # advance the armed cue, but never past the last cue
        self.playhead = min(ph, len(self.items) - 1) if self.items else 0
        self._refresh_highlight()
        self._select_playhead()
        self._update_waveform()

    def stop(self):
        self.engine.stop(); self.current_cue_id = None
        self.statusBar().showMessage("Stop (0.5 s fade)")
        self._refresh_highlight(); self._update_waveform()

    def panic(self):
        self.engine.panic(); self.current_cue_id = None
        self.statusBar().showMessage("Stopped immediately")
        self._refresh_highlight(); self._update_waveform()

    def toggle_schnitzel(self):
        """Show/hide the schnitzel. Audio is never touched."""
        if self.schnitzel.isVisible():
            self.schnitzel.hide()
        else:
            self.schnitzel.setGeometry(self.centralWidget().rect())
            self.schnitzel.show()
            self.schnitzel.raise_()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "schnitzel") and self.schnitzel.isVisible():
            self.schnitzel.setGeometry(self.centralWidget().rect())

    def on_hotkey(self, cue_id):
        for i, it in enumerate(self.items):
            if it.id == cue_id:
                self.fire_index(i); return

    def _reregister_hotkeys(self):
        bindings = {it.id: it.hotkey for it in self.items if getattr(it, "hotkey", "")}
        self.hotkeys.set_bindings(bindings)
        if bindings and not self.hotkeys.available:
            self.statusBar().showMessage("Note: global hotkeys unavailable (library missing)")

    # ------------------------------------------------------------- tick loop
    def _tick(self):
        while True:
            try:
                ev, cue_id = self.engine.events.get_nowait()
            except Exception:
                break
            if ev == "ended":
                self._on_cue_ended(cue_id)

        st = self.engine.active_status()
        if st is None:
            self.big_time.setText("--:--")
            self.wave.set_playpos(None)
        else:
            cue_id, pos, total = st
            remaining = max(0.0, (total - pos) / max(1, self.engine.samplerate))
            self.big_time.setText("-" + fmt_time(remaining))
            for r, it in enumerate(self.items):
                if it.id == cue_id:
                    t = self.table.item(r, COL_TIME)
                    if t:
                        t.setText("-" + fmt_time(remaining))
                    break
            # live cursor on the waveform if the playing cue is the one shown
            shown = self._waveform_cue()
            if shown is not None and shown.id == cue_id:
                self.wave.set_playpos(pos / max(1, self.engine.samplerate))

    def _on_cue_ended(self, cue_id):
        if cue_id != self.current_cue_id:
            return
        cue = next((it for it in self.items if it.id == cue_id), None)
        for r, it in enumerate(self.items):
            if it.id == cue_id and it.kind == "audio" and self.table.item(r, COL_TIME):
                self.table.item(r, COL_TIME).setText(fmt_time(it.play_duration))
        if cue is not None and cue.kind == "audio" and cue.end_mode == EndMode.FOLLOW:
            self.fire_index(self.playhead)
        else:
            self.current_cue_id = None
            self._refresh_highlight(); self._update_waveform()

    # ----------------------------------------------------------- save/load
    def save_show(self, force_dialog=False):
        if self.show_path is None or force_dialog:
            path, _ = QFileDialog.getSaveFileName(self, "Save show", "show.playa", SHOW_FILTER)
            if not path:
                return
            if not path.lower().endswith(".playa"):
                path += ".playa"
            self.show_path = path
        data = {
            "version": 1,
            "master": self.master.value() / 100.0,
            "items": [it.to_dict() for it in self.items],
        }
        try:
            with open(self.show_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.statusBar().showMessage(f"Saved: {os.path.basename(self.show_path)}")
            self.setWindowTitle(f"Playa v{__version__} — {os.path.basename(self.show_path)}")
            self._add_recent(self.show_path)
        except Exception as e:
            QMessageBox.warning(self, "Save", f"Error:\n{e}")

    def open_show(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open show", "", SHOW_FILTER)
        if path:
            self._load_show(path)

    def _load_show(self, path):
        if not os.path.exists(path):
            QMessageBox.warning(self, "Open", f"File not found:\n{path}")
            self._remove_recent(path)
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.warning(self, "Open", f"Error:\n{e}"); return
        self.panic()
        self.items = []
        for d in data.get("items", []):
            if d.get("kind") == "goto":
                self.items.append(GoToCue.from_dict(d))
            else:
                cue = AudioCue.from_dict(d)
                self._prepare_cue(cue)
                self.items.append(cue)
        self.master.setValue(int(data.get("master", 1.0) * 100))
        self.playhead = 0; self.current_cue_id = None; self.show_path = path
        self._refresh_table(); self._reregister_hotkeys(); self._update_waveform()
        self.setWindowTitle(f"Playa v{__version__} — {os.path.basename(path)}")
        self._add_recent(path)
        missing = sum(1 for it in self.items if it.kind == "audio" and it.load_error)
        msg = f"Loaded: {len(self.items)} cues"
        if missing:
            msg += f" · {missing} file(s) not found"
        self.statusBar().showMessage(msg)

    # ---- recent projects (persisted via QSettings) ----
    def _recent_list(self):
        val = self.settings.value("recent_projects", [])
        if isinstance(val, str):
            val = [val]
        return [p for p in (val or []) if p]

    def _add_recent(self, path):
        path = os.path.abspath(path)
        items = self._recent_list()
        items = [p for p in items if os.path.normcase(p) != os.path.normcase(path)]
        items.insert(0, path)
        items = items[:8]
        self.settings.setValue("recent_projects", items)
        self._rebuild_recent_menu()

    def _remove_recent(self, path):
        items = [p for p in self._recent_list()
                 if os.path.normcase(p) != os.path.normcase(os.path.abspath(path))]
        self.settings.setValue("recent_projects", items)
        self._rebuild_recent_menu()

    def _rebuild_recent_menu(self):
        if not hasattr(self, "recent_menu"):
            return
        self.recent_menu.clear()
        items = self._recent_list()
        if not items:
            a = QAction("(none yet)", self); a.setEnabled(False)
            self.recent_menu.addAction(a)
            return
        for p in items:
            label = os.path.basename(p)
            act = QAction(label, self)
            act.setToolTip(p)
            act.triggered.connect(lambda checked, pp=p: self._load_show(pp))
            self.recent_menu.addAction(act)
        self.recent_menu.addSeparator()
        clr = QAction("Clear list", self)
        clr.triggered.connect(self._clear_recent)
        self.recent_menu.addAction(clr)

    def _clear_recent(self):
        self.settings.setValue("recent_projects", [])
        self._rebuild_recent_menu()

    # --------------------------------------------------------------- helpers
    def _selected_row(self):
        r = self.table.currentRow()
        return r if r >= 0 else None

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Space and not self._editing():
            self.go(); return
        if e.key() == Qt.Key_Escape:
            self.stop(); return
        if e.key() == Qt.Key_Down and not self._editing():
            self.playhead = min(self.playhead + 1, max(0, len(self.items) - 1))
            self.table.selectRow(self.playhead)
            self._refresh_highlight(); self._update_waveform(); return
        if e.key() == Qt.Key_Up and not self._editing():
            self.playhead = max(0, self.playhead - 1)
            self.table.selectRow(self.playhead)
            self._refresh_highlight(); self._update_waveform(); return
        super().keyPressEvent(e)

    def _editing(self):
        w = self.focusWidget()
        return isinstance(w, (QLineEdit, QSpinBox))

    def closeEvent(self, e):
        self.hotkeys.clear()
        self.engine.close()
        super().closeEvent(e)
