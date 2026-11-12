from __future__ import annotations

import html
from copy import deepcopy
import os
import threading
import time
import sys
from pathlib import Path

import chess
import cv2
from PySide6.QtCore import QObject, QTimer, Qt, Signal, QRect
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut, QFont, QTextOption
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPushButton, QDoubleSpinBox, QScrollArea, QSpinBox, QSplitter,
    QTabWidget, QTextBrowser, QVBoxLayout, QWidget, QStackedWidget, QToolButton, QMenu)

from . import __version__
from .toggle import ToggleButton as QCheckBox
from .capture import BoardRegion, bgr_pixmap, capture, input_point, screen_key
from .controls import ClickMove, Hotkeys
from .core import (DEFAULT_KEYS, PositionTracker, SearchSettings, board_from_symbols,
                   can_send_move, data_dir, find_engine, load_settings, ordered_symbols,
                   save_settings, simple_move, validate_keys)
from .engine import EngineJob, EngineSession
from .live import LiveWorker
from .multiboard import MultiBoards
from .phone import PhoneCompanion
from . import engine_config,engine_library
from .hints import LiveHintFilter
from .recognition import Recognizer, position_from_read
from .overlay import BoardOverlay
from .foreground import foreground_kind
from .vision import Templates, detect_boards
from .widgets import BoardView, CropDialog, EvalBar, BoardArea
from .analysis_presets import AnalysisPresets
from .target_lock import TargetLock
from .branding import BrandBanner, app_icon
from .ui_controls import ResponsiveScrollArea
from .threats import presentation as threat_presentation


STYLE = """
QMainWindow, QDialog, QWidget { background: #14231d; color: #e5efe8; font-size: 15px; }
QLabel#brand { font-size: 27px; font-weight: 700; color: #8ce6b3; }
QLabel#status { background: #20392c; border-radius: 7px; padding: 9px; }
QPushButton { background: #2d4839; border: 1px solid #496554; padding: 8px 10px; border-radius: 5px; }
QPushButton:hover { background: #3e624e; }
QPushButton:checked { background: #397955; border-color: #92dfb2; }
QPushButton#primary { background: #78c997; color: #10291c; font-weight: 700; }
QPushButton#stop { background: #743b36; border-color: #b66659; }
QSpinBox:disabled, QDoubleSpinBox:disabled { color: #81968a; background: #21372a; }
QPushButton:disabled { color: #81968a; background: #21372a; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextBrowser { background: #1c3025; border: 1px solid #415a49; border-radius: 4px; padding: 5px; selection-background-color: #47775b; }
QTextBrowser { padding: 10px; }
QGroupBox { border: 1px solid #3b5143; border-radius: 6px; margin-top: 13px; padding-top: 10px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 9px; padding: 0 4px; }
QTabBar::tab { background: #21372b; padding: 9px 8px; }
QTabBar::tab:selected { background: #3c624b; }
QScrollArea { border: none; }
QSplitter::handle { background: #2b4133; }
QPushButton[toggle="true"] { text-align: left; padding: 8px 38px 8px 10px; background: #243e2e; border: 1px solid #4d6857; border-radius: 8px; }
QPushButton[toggle="true"]:checked { color: #10291c; background: #7bc99a; border-color: #9de4b7; }
QPushButton[toggle="true"]:hover { border-color: #b6efcc; }
QPushButton[toggle="true"]:disabled { color: #6d8377; background: #1f3428; border-color: #344d3d; }

"""

STYLE+= '\nQSpinBox, QDoubleSpinBox { padding-right: 30px; min-height: 24px; }\nQSpinBox::up-button, QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 25px; background: #344f3f; border-top-right-radius: 4px; }\nQSpinBox::down-button, QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 25px; background: #344f3f; border-bottom-right-radius: 4px; }\nQSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover, QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover { background: #50745d; }\nQSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url("UP_ICON"); width: 12px; height: 8px; }\nQSpinBox::down-arrow, QDoubleSpinBox::down-arrow, QComboBox::down-arrow { image: url("DOWN_ICON"); width: 12px; height: 8px; }\nQComboBox { padding-right: 24px; }\nQComboBox::drop-down { border: none; width: 24px; }\n'
STYLE=STYLE.replace("UP_ICON",(Path(__file__).parent/"assets/ui/up.svg").as_posix()).replace("DOWN_ICON",(Path(__file__).parent/"assets/ui/down.svg").as_posix())
STYLE=STYLE.replace("CHECK_ICON",(Path(__file__).parent/"assets/ui/check.svg").as_posix())

STYLE += """
QMainWindow, QDialog, QWidget { background:#111f19; color:#e0eae4; }
QPushButton, QToolButton { background:#263e31; border:1px solid #3c5747; padding:8px 10px; border-radius:7px; }
QPushButton:hover, QToolButton:hover { background:#345540; border-color:#739d80; }
QPushButton:checked, QToolButton:checked { background:#397955; border-color:#8bd4a6; }
QPushButton#primary { background:#8bd6aa; border-color:#8bd6aa; color:#10291c; }
QToolButton::menu-indicator { subcontrol-position:right center; margin-right:3px; }
QMenu { background:#1c3025; border:1px solid #496554; padding:6px; }
QMenu::item { padding:9px 24px 9px 12px; border-radius:5px; }
QMenu::item:selected { background:#355a42; }
QTabWidget::pane { border:0; }
QTabBar::tab { background:#1b3024; color:#a7c0af; padding:10px 8px; border-bottom:2px solid transparent; }
QTabBar::tab:selected { color:#b6edcc; background:#284433; border-bottom:2px solid #8bd6aa; }
QGroupBox { border:1px solid #304b3a; border-radius:8px; margin-top:16px; padding:14px 8px 8px; }
QGroupBox::title { color:#a7c0af; font-size:13px; }
QListWidget, QTableWidget { background:#182b21; border:1px solid #304b3a; border-radius:7px; selection-background-color:#365e45; outline:0; }
QListWidget::item { padding:10px 8px; border-bottom:1px solid #263e30; }
QListWidget::item:selected { background:#31583f; color:#e2f4e8; }
QTableWidget { gridline-color:#2d4636; }
QHeaderView::section { background:#263f30; color:#b6cbbd; padding:9px; border:0; font-weight:600; }
QSlider::groove:horizontal { height:5px; background:#324e3b; border-radius:2px; }
QSlider::handle:horizontal { width:16px; margin:-6px 0; background:#8bd6aa; border-radius:8px; }
QScrollBar:vertical { width:9px; background:transparent; margin:2px; }
QScrollBar::handle:vertical { background:#456350; border-radius:3px; min-height:28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }
QToolTip { color:#e0eae4; background:#253e2e; border:1px solid #5e806a; padding:5px; }
"""

SCREEN_REFRESH_MS = 75
ANALYSIS_STYLE = "h2 {font-size:22px;margin:4px 0 8px;} h3 {font-size:18px;margin:12px 0 4px;} p {margin:4px 0 8px;} small {font-size:13px;}"


class EngineSignals(QObject):
    complete = Signal(int, object, str)
    progress = Signal(int, object)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._ready = False
        self._applying_preset=False
        self._compact = False
        self._compact_geometry = None
        self._expanded_geometry = None
        self._white_bottom = True
        self._live_token = 0
        self._scan_busy = False
        self._monitoring = False
        self._scan_again = False
        self._overlay_grace_until = 0.
        self._force_full_scan = False
        self._reviewing = False
        self._history = []
        self._history_index = -1
        self.engine_session = EngineSession()
        self._last_read = None
        self._last_read_at = 0
        self._screen_confirmed = False
        self._stable_key = None
        self._stable_frames = 0
        self._position_locked = False
        self._pending_screen_move = None
        self._lost_frames = 0
        self._scan_number = 0
        self._last_discovery_at = time.monotonic()
        self._turn_known = False
        self._recognizer = Recognizer()
        self.overlay = BoardOverlay()
        self.live_worker = LiveWorker(self)
        self.live_worker.signals.completed.connect(self.live_finished)
        self.setWindowTitle(f"BoardLens {__version__} · Live screen analysis")
        self.setWindowIcon(app_icon())
        self.resize(1400, 900)
        self.setMinimumSize(1180, 740)
        self.setStyleSheet(STYLE)
        self.settings = load_settings()
        self.tracker = PositionTracker()
        self.templates = Templates()
        try:
            template_path = data_dir() / "templates.npz"
            if template_path.exists():
                self.templates = Templates.load(template_path)
        except (OSError, ValueError, KeyError):
            pass
        self.region = None
        self.snapshot = None
        self.result = None
        self._pinned_result = None
        self.hint_filter=LiveHintFilter()
        self.job = None
        self.generation = 0
        self.last_observation = None
        self.stable_count = 0
        self.last_sent_fen = None
        self.pending_until = 0
        self.last_requested_fen = None
        self.closing = False
        self.engine_signals = EngineSignals(self)
        self.engine_signals.complete.connect(self.engine_finished)
        self.engine_signals.progress.connect(self.engine_progress)
        self.clicker = ClickMove(self)
        self.clicker.done.connect(lambda: self.status("Move clicked. Waiting for the board to confirm it."))
        self.clicker.failed.connect(self.input_failed)
        self.hotkeys = Hotkeys(self)
        self.hotkeys.action.connect(self.dispatch)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(SCREEN_REFRESH_MS)
        self.multi = MultiBoards(self)
        self.phone = PhoneCompanion(self)
        self.browser_reader=None
        self._scan_route=None;self._last_external_route=None;self._native_enabled=False
        from .native_chess import NativeChessReader
        self.native_reader=NativeChessReader()
        self.live_worker.provider=self.direct_reads
        self.analysis_presets=AnalysisPresets(self);self.target_lock=TargetLock()
        self._build_ui()
        if sys.platform == 'darwin' and not os.environ.get('BOARDLENS_TEST_MODE'):
            from .permissions import Permissions
            self.permissions = Permissions(self)
        from .evaluation import Evaluations
        self.evaluations=Evaluations(self);self.evaluations.changed.connect(self.evaluation_changed)
        self.analysis_presets.refresh_presets()
        self.reader_timer=QTimer(self);self.reader_timer.setInterval(75);self.reader_timer.timeout.connect(self.publish_reader_hints);self.reader_timer.start()
        self.multipv.valueChanged.connect(self.recommendation_preset)
        self.restore()
        for field in (self.seconds, self.depth, self.multipv, self.threads, self.hash_mb):
            field.valueChanged.connect(self.engine_settings_changed)
        self.mode.currentTextChanged.connect(self.engine_settings_changed)
        self.engine_path.editingFinished.connect(self.engine_settings_changed)
        self.refresh_monitors()
        QGuiApplication.instance().screenAdded.connect(self.refresh_monitors)
        QGuiApplication.instance().screenRemoved.connect(self.monitors_changed)
        self.refresh_board()
        self.show_welcome()
        self._ready = True
        self.bind_autosave()
        self.turn.currentIndexChanged.connect(self.turn_changed)
        self.rebuild_local_keys()
        self.status("Ready. Live screen finds and follows visible chessboards automatically.")
        if not os.environ.get("BOARDLENS_TEST_MODE"):
            saved_monitor=self.settings.get("monitor_key")
            self.monitor.setCurrentIndex(max(0,self.monitor.findData(saved_monitor)) if saved_monitor else self.monitor.findData("*"))
            self.source.setCurrentIndex(max(0,min(1,int(self.settings.get("source_index",1)))))
            self.global_keys.setChecked(bool(self.settings.get("global_keys", True)))
            if self.phone_auto.isChecked():
                self.phone_button.setChecked(True);self.toggle_phone(True)

    def bind_autosave(self):
        self.autosave_timer=QTimer(self);self.autosave_timer.setSingleShot(True);self.autosave_timer.setInterval(500)
        self.autosave_timer.timeout.connect(lambda:self.save(quiet=True))
        names=('seconds','depth','multipv','threads','hash_mb','arrow_count','engine_skill','engine_elo','human_elo','phone_port','source','monitor','mode','orientation','turn','engine_kind','playing_style','strength_mode','compare_a','compare_b','compare_c','overlay_enabled','arrow_labels','show_white','show_black','show_reply','rank_best','rank_second','rank_others','only_my_color','early_suggestions','global_keys','stick_to_move','steady_arrows','always_top','phone_auto','browser_reader_button','native_reader_button','dashed_reply','threats_enabled','threat_attacks','threat_mates','lock_target','eval_engine','eval_seconds','eval_depth','eval_human_elo','predict_continuations','prediction_plies','prediction_seconds')
        for name in names:
            field=getattr(self,name)
            signal=field.valueChanged if isinstance(field,(QSpinBox,QDoubleSpinBox)) else field.currentIndexChanged if isinstance(field,QComboBox) else field.toggled
            signal.connect(self.queue_autosave)
        for field in (self.engine_path,self.custom_engine):field.editingFinished.connect(self.queue_autosave)
        for field in self.key_fields.values():field.editingFinished.connect(self.apply_keys)

    def queue_autosave(self,*_):
        if self._ready and not self.closing and not self._applying_preset and hasattr(self,'autosave_timer'):self.autosave_timer.start()

    def moveEvent(self,event):
        super().moveEvent(event);self.queue_autosave()

    def resizeEvent(self,event):
        super().resizeEvent(event);self.queue_autosave()

    def toggle_compact(self, enabled):
        self._compact = enabled
        self.compact_button.setChecked(enabled)
        self.compact_button.setText("Expand" if enabled else "Compact")
        self.fen_panel.setVisible(not enabled and self.practice)
        self.capture_label.hide()
        self.tagline.setVisible(not enabled)
        self.brand.set_compact(enabled)
        self.analysis_panel.setVisible(not enabled)
        self.sidebar_host.setVisible(not enabled and self.workspace_stack.currentIndex() !=2)
        self.settings_button.setVisible(enabled)
        self.setMinimumSize(560 if enabled else 1180,740)
        self.splitter.setOrientation(Qt.Orientation.Vertical if enabled else Qt.Orientation.Horizontal)
        self.board_panel.setMinimumWidth(0 if enabled else 430)
        self.analysis_panel.setMinimumWidth(0 if enabled else 350)
        self.board_area.setMinimumHeight(300 if enabled else 330)
        if enabled:
            self.settings_dialog.layout().insertWidget(0,self.settings_tabs)
        else:
            self.settings_dialog.hide()
            self.sidebar_host.layout().addWidget(self.settings_tabs)
            self.splitter.setSizes([680,420])
        self.settings_tabs.show()
        self.board_area.arrange()

    def window_screen(self):
        rectangle=self.frameGeometry()
        return max(QGuiApplication.screens(),key=lambda screen:
                   screen.availableGeometry().intersected(rectangle).width()*screen.availableGeometry().intersected(rectangle).height())

    def user_toggle_compact(self,enabled):
        # Native windowHandle.screen() can lag a cross-display move. Choose from
        # the actual rectangle and retain the current position when resizing.
        available=self.window_screen().availableGeometry()
        rectangle=QRect(self.geometry())
        if enabled:
            self._expanded_geometry=self.geometry()
            target=self._compact_geometry
            width,height=620,min(900,available.height()-40)
        else:
            self._compact_geometry=self.geometry()
            target=self._expanded_geometry
            width,height=min(1400,available.width()-24),min(900,available.height()-40)
        if target is not None:width,height=target.width(),target.height()
        self.toggle_compact(enabled)
        rectangle.setWidth(min(max(width,self.minimumWidth()),available.width()-20))
        rectangle.setHeight(min(max(height,self.minimumHeight()),available.height()-40))
        rectangle.moveLeft(max(available.left()+4,min(rectangle.left(),available.right()-rectangle.width()-4)))
        rectangle.moveTop(max(available.top()+26,min(rectangle.top(),available.bottom()-rectangle.height()-8)))
        self.setGeometry(rectangle)

    def show_all_boards(self, enabled):
        self.sidebar_host.setVisible(not self._compact)
        self.workspace_stack.setCurrentIndex(1 if enabled and self.multi.count>1 else 0)
        if enabled and self.multi.count>1:
            self.toggle_compact(False)
            screen=self.window_screen()
            g=screen.availableGeometry()
            self.resize(min(1760,g.width()-24),min(960,g.height()-40))
            self.move(max(g.x(),min(self.x(),g.right()-self.width())),max(g.y(),min(self.y(),g.bottom()-self.height())))
            self.multi.layout_cards()

    def engine_settings_changed(self,*_):
        if self._applying_preset:return
        self.mark_custom_preset()
        self.invalidate(release_move=True)
        self.multi.settings_changed()
        self.update_engine_summary()

    def open_settings(self):
        if not self._compact:
            self.settings_tabs.setFocus()
            return
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def start_live(self, compact=False):
        if self.source.currentIndex() != 1:
            return
        self.update_foreground()
        if hasattr(self, 'permissions') and not self.permissions.ensure_capture():
            return
        self._reviewing = False
        self._monitoring = True
        self.update_history_controls()
        self.live_button.setChecked(True)
        self._screen_confirmed = False
        self._stable_key = None
        self._stable_frames = 0
        self.last_requested_fen = None
        if self._last_read is None:self.show_empty_board()
        self.status("Searching "+self.monitor_description()+" for a chessboard…")
        QTimer.singleShot(50, self.request_scan)

    def request_scan(self, force=False):
        if self.closing or self._reviewing or (not self._monitoring and not force):
            return
        self.update_foreground()
        if hasattr(self, 'permissions') and not self.permissions.ensure_capture():
            return
        if self._scan_busy:
            if force:self._scan_again = True
            return
        if self.target_lock.active and not self.target_lock.target.get('source') and not self.target_lock.pixel_visible():
            self.live_finished(self._live_token,None,'Locked board is covered.');return
        self._scan_busy = True
        self._scan_number += 1
        full_scan = self._force_full_scan or self._lost_frames >= 2 or not self.region or time.monotonic()-self._last_discovery_at>=3
        if full_scan:self._last_discovery_at=time.monotonic()
        self._force_full_scan = False
        token = self._live_token
        if self.overlay._native_mac:
            specs=[]
            selected=self.monitor.currentData()
            for screen in QGuiApplication.screens():
                key=screen_key(screen)
                if selected not in (None,'*',key):
                    continue
                if not full_scan and selected=='*' and self.region and self._lost_frames<3 and key not in {r.screen_name for r in self.multi.regions()}:
                    continue
                geometry=screen.geometry()
                masks=[w.frameGeometry().getRect() for w in QApplication.topLevelWidgets()
                       if not getattr(w,'is_board_overlay',False) and w.isVisible() and not w.isMinimized()]
                specs.append({'key':key,'name':screen.name(),'geometry':geometry.getRect(),
                              'width':round(geometry.width()*screen.devicePixelRatio()),
                              'height':round(geometry.height()*screen.devicePixelRatio()),'masks':masks,
                              'owner_pid':os.getpid()})
            if self.region and not full_scan:
                specs=[dict(spec,crop=(region.x,region.y,region.size)) for spec in specs
                       for region in self.multi.regions() if region.screen_name==spec['key']]
            # All panels stay excluded throughout visibility changes.
            excluded={panel.capture_window_id() for panel in self.multi.overlays()}
            from .mac_capture import capture_frames
            hint=(self.region.screen_name,self.region.x,self.region.y,self.region.size) if self.region else None
            if full_scan:
                hint=None
            self.live_worker.submit(token,lambda cancelled:capture_frames(specs,excluded,cancelled),hint)
            return
        self.capture_scan(force,token,full_scan)

    def capture_scan(self, force, token, full_scan=False):
        if self.closing or token != self._live_token:
            return
        frames = []
        selected = self.monitor.currentData()
        try:
            for screen in QGuiApplication.screens():
                key = screen_key(screen)
                if selected not in (None, "*", key):
                    continue
                image = capture(screen)
                geometry = screen.geometry()
                # Ignore our own mirror; otherwise a screen reader can lock onto
                # its own preview instead of the target app.
                for window in QApplication.topLevelWidgets():
                    if getattr(window,"is_board_overlay",False) or not window.isVisible() or window.isMinimized():
                        continue
                    rect = window.frameGeometry().intersected(geometry)
                    if rect.isEmpty():
                        continue
                    x0 = max(0, int((rect.x()-geometry.x())*image.shape[1]/geometry.width()))
                    y0 = max(0, int((rect.y()-geometry.y())*image.shape[0]/geometry.height()))
                    x1 = min(image.shape[1], round((rect.right()+1-geometry.x())*image.shape[1]/geometry.width()))
                    y1 = min(image.shape[0], round((rect.bottom()+1-geometry.y())*image.shape[0]/geometry.height()))
                    image[y0:y1,x0:x1] = (24,30,36)
                regions=[r for r in self.multi.regions() if r.screen_name==key]
                if regions and not full_scan:
                    for region in regions:
                        frames.append((key,screen.name(),region.crop(image),
                                       (region.x,region.y,region.size,image.shape[1],image.shape[0])))
                else:frames.append((key, screen.name(), image))
            if not frames:
                raise ValueError("The selected monitor is unavailable.")
            self._scan_busy = True
            hint = (self.region.screen_name, self.region.x, self.region.y, self.region.size) if self.region else None
            if self._force_full_scan or self._lost_frames:
                hint = None
            self.live_worker.submit(self._live_token, frames, hint)
        except Exception as exc:
            self._scan_busy = False
            self._screen_confirmed = False
            self.status(f"Screen capture: {exc}")
        finally:
            self.update_visuals()

    def live_finished(self, token, answer, error):
        if self.closing or token != self._live_token:
            return
        self._scan_busy = False
        if self._scan_again:
            self._scan_again = False
            self._force_full_scan = True
            self.request_scan(force=True)
            return
        if self._reviewing:
            return
        answers=answer if isinstance(answer,list) else [answer] if answer is not None else []
        answers=self.target_lock.filter(answers)
        answer=self.multi.accept(answers)
        if (error or answer is None) and self.target_lock.active:
            self._screen_confirmed=False;self._lost_frames+=1;self.overlay.hide()
            self.status('Locked board unavailable · keeping its last position. Return to it or unlock.')
            if self._last_read is None:self.show_empty_board('Waiting for the locked board')
            return
        if error or answer is None:
            if not error and self._screen_confirmed:
                self._overlay_grace_until=time.monotonic()+.4
            self._lost_frames+=1
            self._screen_confirmed = False
            self._pending_screen_move=None
            if error or self._lost_frames>2 or time.monotonic()>=self._overlay_grace_until:
                self._overlay_grace_until=0.
                self.overlay.hide()
            if error:
                self.status(f"Screen recognition: {error}")
            else:
                if self._last_read is None or self._lost_frames>=3:self.show_empty_board("No board detected yet")
                self.status("Watching "+self.monitor_description()+" · no complete board detected yet")
            return
        key, name, read, width, height = answer
        self._lost_frames=0
        self._overlay_grace_until=0.
        d = read.detection
        self.region = BoardRegion(key, width, height, d.x, d.y, d.size)
        if self._position_locked and read.symbols != ordered_symbols(chess.Board(),read.white_bottom):
            # Track orientation through pawnless endings and screen flips using
            # legal positions, instead of guessing from the kings' locations.
            matches=[]
            for bottom in (True,False):
                probe=PositionTracker(self.tracker.board)
                state,_=probe.update(read.symbols,bottom)
                if state!='unmatched':matches.append(bottom)
            if len(matches)==1:read.white_bottom=matches[0]
        if self.orientation.currentIndex() != 0:
            read.white_bottom = self.orientation.currentIndex() == 1
        self._white_bottom = read.white_bottom
        self._last_read = read
        self._last_read_at = time.monotonic()
        self.preview(read.image)
        self.region_label.setText("Board found on "+name)
        placement_key = (key, tuple(read.symbols), read.white_bottom,getattr(read,'exact_fen',None))
        if placement_key == self._stable_key:
            self._stable_frames += 1
        else:
            self._stable_key, self._stable_frames = placement_key, 1
            self._screen_confirmed = False
            self._pending_screen_move=None
            self.overlay.hide()
            self.status("Board found. Checking the next frame…")
            return
        if self._stable_frames < 2:
            return
        self._screen_confirmed = True
        self.region_label.setText("Board detected on "+name)
        try:
            if getattr(read,'exact_fen',None) and self.tracker.board.fen()!=read.exact_fen:
                self.tracker=PositionTracker(chess.Board(read.exact_fen));self._turn_known=True;state,move='moved',None
            else:state, move = self.tracker.update(read.symbols, read.white_bottom)
            if state == "unmatched":
                state, move = self.tracker.reconcile(read.symbols, read.white_bottom)
            if state == "unmatched" or (not self._position_locked and self.turn.currentIndex()):
                turn_override = None if self.turn.currentIndex() == 0 else self.turn.currentIndex() == 1
                board, self._turn_known = position_from_read(read, turn_override,
                                                            self.tracker.board if self._position_locked else None)
                self.tracker = PositionTracker(board)
                self.invalidate(preserve_eval=True)
            elif state == "moved":
                self._turn_known = True
                self.pending_until = 0
                self.invalidate(preserve_eval=True)
            elif read.symbols == ordered_symbols(chess.Board(), read.white_bottom):
                self._turn_known = True
            self._position_locked = True
            was_empty=self.board_stack.currentIndex()==1
            self.refresh_board()
            if was_empty and self.result and self.result.get("fen")==self.tracker.board.fen():self.render_result(self.result)
            self.remember_position()
            if self.tracker.board.is_game_over():
                self.status(f"Game over · {self.tracker.board.result()} — still watching for a new board")
                return
            if self.pending_until:
                return
            if self.job is None and self.last_requested_fen != self.tracker.board.fen():
                self.suggest(from_poll=True)
            elif self.job is None:
                self.status("Live · watching for the next move" + (" · turn inferred" if not self._turn_known else ""))
            self.update_visuals()
        except ValueError as exc:
            self._screen_confirmed = False
            self.status(f"Waiting for a complete position… {exc}")

    def turn_changed(self, *_):
        if self._last_read is None or self.source.currentIndex() != 1:
            return
        try:
            turn = None if self.turn.currentIndex() == 0 else self.turn.currentIndex() == 1
            board, known = position_from_read(self._last_read, turn)
            self.tracker = PositionTracker(board)
            self._turn_known = known
            self._position_locked = True
            self.invalidate(preserve_eval=True)
            self.refresh_board()
        except ValueError as exc:
            self.status(str(exc))

    def _button(self, text, handler, parent_layout=None, checkable=False):
        button = QPushButton(text)
        button.setCheckable(checkable)
        button.clicked.connect(handler)
        if isinstance(parent_layout, QFormLayout):
            parent_layout.addRow(button)
        elif parent_layout is not None:
            parent_layout.addWidget(button)
        return button

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16,14,16,12);layout.setSpacing(12)
        top = QHBoxLayout()
        self.brand = BrandBanner()
        top.addWidget(self.brand)
        self.tagline = QLabel("Chess analysis")
        top.addWidget(self.tagline)
        top.addStretch()
        self.always_top = QCheckBox("Stay on top")
        self.always_top.toggled.connect(self.set_always_top)
        self.quick_arrows=self._button("Arrows",lambda enabled:self.overlay_enabled.setChecked(enabled),top,True)
        self.quick_arrows.setChecked(True)
        self.compact_button = self._button("Expand", self.user_toggle_compact, top, True)
        self.settings_button = self._button("Settings", self.open_settings, top)
        help_button=self._button("?", self.help, top);help_button.setToolTip("Help");help_button.setAccessibleName("Help");help_button.setFixedWidth(38)
        layout.addLayout(top)
        from PySide6.QtWidgets import QGridLayout
        actions = QGridLayout()
        self.suggest_button = self._button("Suggest", self.suggest)
        self.suggest_button.setObjectName("primary")
        self.live_button = self._button("Auto suggest", self.toggle_live, checkable=True)
        self.move_button = self._button("Play best", self.play_best)
        stop = self._button("STOP", self.stop)
        self.stop_button = stop
        for i, button in enumerate((self.suggest_button, self.live_button, stop)):
            actions.addWidget(button, i//3, i%3)
        stop.setObjectName("stop")
        layout.addLayout(actions)
        options=QHBoxLayout()
        self.only_my_color = QCheckBox("Only my color")
        self.only_my_color.setToolTip("The color at the bottom is yours. Waits during the opponent's turn.")
        self.only_my_color.toggled.connect(self.my_color_changed)
        options.addWidget(self.only_my_color)
        self.stick_to_move = QCheckBox("Lock move")
        self.stick_to_move.setToolTip("Keep the first displayed move and one arrow for this position. Engine thinking and evaluation continue. Turn off, change the board, or press Scan now to release it.")
        self.stick_to_move.toggled.connect(self.stick_move_changed)
        options.addWidget(self.stick_to_move)
        self.steady_arrows=QCheckBox("Steady arrows");self.steady_arrows.setChecked(True)
        self.steady_arrows.setToolTip("Keep calculating. The first hint is immediate; replacements must stay consistent for 250 ms. Final results appear immediately.")
        self.steady_arrows.toggled.connect(self.steady_changed);options.addWidget(self.steady_arrows)
        options.addStretch()
        self.player_label = QLabel("Your color: White · bottom of board")
        self.quick_scan_button=self._button("Scan now",self.scan_now,options)
        layout.addLayout(options)
        self.player_label.setStyleSheet("color:#aec4b6;")
        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        self.splitter = split
        layout.addWidget(split, 1)
        tabs = QTabWidget()
        self.settings_tabs = tabs
        tabs.setMinimumWidth(280)
        self.settings_dialog = QDialog(self)
        self.settings_dialog.setWindowTitle("BoardLens · Settings")
        self.settings_dialog.resize(580,720)
        settings_layout=QVBoxLayout(self.settings_dialog)
        settings_layout.addWidget(tabs)
        self._button("Done",self.settings_dialog.hide,settings_layout)
        source = QWidget()
        src = QVBoxLayout(source)
        self.source = QComboBox()
        self.source.addItems(["Practice board", "Computer screen", "Screenshot"])
        self.source.currentIndexChanged.connect(self.source_changed)
        src.addWidget(QLabel("Read from"))
        src.addWidget(self.source)
        src.addWidget(self.always_top)
        self.monitor = QComboBox()
        self.monitor.currentIndexChanged.connect(self.monitor_changed)
        self.monitor_label=QLabel("Display to read");src.addWidget(self.monitor_label)
        src.addWidget(self.monitor)
        self.target_board=QComboBox();self.target_board.addItem('Board 1',0);self.target_board.hide();src.addWidget(self.target_board)
        self.lock_target=QCheckBox('Keep this board selected');self.lock_target.setToolTip('Keep following this target when you switch apps. Covered pixel boards pause; direct readers can keep reading in the background.');self.lock_target.toggled.connect(self.target_lock_changed);src.addWidget(self.lock_target)
        self.target_status=QLabel('Automatic board selection');self.target_status.setStyleSheet('font-size:13px;color:#9eb6a8;');self.target_status.setWordWrap(True);src.addWidget(self.target_status)
        self.open_screenshot_button=self._button("Open screenshot…", self.open_image, src)
        self.region_label = QLabel("No screen board selected")
        self.region_label.setWordWrap(True)
        src.addWidget(self.region_label)
        self.orientation = QComboBox()
        self.orientation.addItems(["Detect bottom color", "White at bottom", "Black at bottom"])
        self.orientation.currentIndexChanged.connect(self.orientation_changed)
        src.addWidget(self.orientation)
        self.style_label = QLabel("Built-in AI recognition · no calibration")
        self.style_label.setWordWrap(True)
        self.style_label.hide()
        self.scan_button = self.quick_scan_button
        form = QFormLayout()
        self.turn = QComboBox()
        self.turn.addItems(["Detect turn", "White", "Black"])
        self.turn.setToolTip("Use this if joining a game halfway through and there is no last-move highlight.")
        form.addRow("Side to move", self.turn);self.position_turn_form=form
        self.castling = QLineEdit("-")
        self.castling.setPlaceholderText("KQkq or -")
        self.castling.hide()
        src.addLayout(form)
        self.allow_clicks = QCheckBox("Enable screen clicks for practice")
        self.allow_clicks.setToolTip("Use offline, analysis boards, or games where assistance is allowed.")
        self.allow_clicks.toggled.connect(self.clicks_changed)
        self.allow_clicks.hide()
        self.auto_queen = QCheckBox("Target board auto-promotes to queen")
        self.auto_queen.hide()
        self.reader_options=QWidget();reader_layout=QVBoxLayout(self.reader_options);reader_layout.setContentsMargins(0,4,0,4);reader_layout.setSpacing(12)
        self.readers_toggle=self._button("Optional connections ▸",lambda enabled:self.reader_options.setVisible(enabled),src,True)
        self.readers_toggle.toggled.connect(self.reader_options.setVisible)
        self.readers_toggle.toggled.connect(lambda enabled:self.readers_toggle.setText("Optional connections ▾" if enabled else "Optional connections ▸"))
        self.reader_options.hide()
        browser_group=QGroupBox("Browser connection");browser_layout=QVBoxLayout(browser_group);browser_layout.setSpacing(9)
        self.browser_reader_button=QCheckBox("Connect browser");browser_layout.addWidget(self.browser_reader_button)
        self.browser_connection_details=QWidget();details=QVBoxLayout(self.browser_connection_details);details.setContentsMargins(0,0,0,0);details.setSpacing(8)
        self.browser_reader_status=QLabel("Browser connection off");self.browser_reader_status.setWordWrap(True);self.browser_reader_status.setStyleSheet("color:#a8c7b2;font-size:13px;");details.addWidget(self.browser_reader_status)
        self.browser_reader_key=QLineEdit();self.browser_reader_key.setReadOnly(True);self.browser_reader_key.setEchoMode(QLineEdit.EchoMode.Password);self.browser_reader_key.setPlaceholderText("Pairing key");self.browser_reader_key.setAccessibleName('Private browser pairing key')
        details.addWidget(self.browser_reader_key)
        self._button("Copy pairing key",lambda:self.copy_text(self.browser_reader_key.text()),details)
        self._button("Connection setup…",self.reader_setup,details)
        browser_layout.addWidget(self.browser_connection_details);self.browser_connection_details.hide()
        self.browser_reader_button.toggled.connect(self.browser_connection_details.setVisible);self.browser_reader_button.toggled.connect(self.toggle_browser_reader)
        reader_layout.addWidget(browser_group)
        self.native_connection_group=QGroupBox("Local 3D chess");native_layout=QVBoxLayout(self.native_connection_group)
        self.native_reader_button=QCheckBox("Read local 3D chess");self.native_reader_button.toggled.connect(self.native_access_changed);native_layout.addWidget(self.native_reader_button)
        self.native_connection_status=QLabel('Ready · open your local 3D chess board');self.native_connection_status.setWordWrap(True);self.native_connection_status.setStyleSheet('color:#a8c7b2;font-size:13px;');native_layout.addWidget(self.native_connection_status);self.native_connection_status.hide()
        self.native_reader_button.toggled.connect(self.native_connection_status.setVisible);self.native_connection_group.setVisible(sys.platform=='darwin');reader_layout.addWidget(self.native_connection_group)
        src.addWidget(self.reader_options)
        self.connection_hint=QLabel('Optional. Standard 2D boards use screen scanning.');self.connection_hint.setWordWrap(True);self.connection_hint.setStyleSheet('font-size:13px;color:#9eb6a8;');src.addWidget(self.connection_hint)
        self.screen_setup=QGroupBox('Computer screen');screen_layout=QVBoxLayout(self.screen_setup);screen_layout.setSpacing(9)
        for widget in (self.monitor_label,self.monitor,self.target_board,self.lock_target,self.target_status,self.region_label,self.readers_toggle,self.reader_options,self.connection_hint):
            src.removeWidget(widget);screen_layout.addWidget(widget)
        src.insertWidget(4,self.screen_setup)
        app_settings=QGroupBox('App');app_settings_layout=QVBoxLayout(app_settings)
        from .updater import auto_enabled,set_auto_enabled
        self.auto_updates=QCheckBox('Automatic updates');self.auto_updates.setChecked(auto_enabled());self.auto_updates.setToolTip('Check and download quietly; apply the verified update on next launch.')
        self.auto_updates.toggled.connect(set_auto_enabled);app_settings_layout.addWidget(self.auto_updates)
        self._button('Check for updates',self.open_updates,app_settings_layout)
        if sys.platform == 'darwin':
            self._button('Permissions', lambda: self.permissions.open() if hasattr(self, 'permissions') else None, app_settings_layout)
        src.addWidget(app_settings)
        src.addStretch()
        tabs.addTab(self._scroll(source), "Board")
        engine = QWidget()
        eng = QVBoxLayout(engine)
        self.engine_files=QWidget();files=QVBoxLayout(self.engine_files);files.setContentsMargins(0,0,0,0)
        self.engine_path = QLineEdit(find_engine())
        self.engine_path.setPlaceholderText("Choose a Stockfish / UCI executable")
        self.engine_kind=QComboBox();self.engine_kind.addItems(engine_config.ENGINE_NAMES)
        eng.addWidget(QLabel("Analysis engine"));eng.addWidget(self.engine_kind)
        self.preset_combo=QComboBox();self.preset_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon);self.preset_combo.setMinimumContentsLength(10);self.preset_combo.addItem('Manual',None);self.preset_combo.setToolTip('Manual uses the individual settings below. Quick and Deep are saved Stockfish configurations. Save preset remembers your chosen engine and controls.');self.preset_combo.currentIndexChanged.connect(self.preset_selected);eng.addWidget(self.preset_combo)
        preset_actions=QHBoxLayout();self._button('Save preset…',self.save_named_preset,preset_actions);self._button('Manage…',self.manage_presets,preset_actions);eng.addLayout(preset_actions)
        self._button("Engine library…",self.open_engine_library,eng)
        evaluation_box=QGroupBox('Evaluation bar');evaluation_form=QFormLayout(evaluation_box)
        self.eval_engine=QComboBox()
        for index,item in enumerate(engine_library.ENTRIES):
            if item.kind!='tiny':self.eval_engine.addItem(item.label,index)
        self.eval_seconds=QDoubleSpinBox();self.eval_seconds.setRange(.1,30);self.eval_seconds.setValue(.3);self.eval_seconds.setSingleStep(.1);self.eval_seconds.setSuffix(' s')
        self.eval_depth=QSpinBox();self.eval_depth.setRange(1,40);self.eval_depth.setValue(18)
        self.eval_human_elo=QSpinBox();self.eval_human_elo.setRange(600,2600);self.eval_human_elo.setValue(1500)
        evaluation_form.addRow('Evaluation engine',self.eval_engine);evaluation_form.addRow('Think time',self.eval_seconds);evaluation_form.addRow('Depth cap',self.eval_depth);evaluation_form.addRow('Human rating',self.eval_human_elo)
        for field in (self.eval_engine,self.eval_seconds,self.eval_depth,self.eval_human_elo):
            (field.currentIndexChanged if isinstance(field,QComboBox) else field.valueChanged).connect(self.evaluation_settings_changed)
        eng.addWidget(evaluation_box)

        self.engine_capabilities=QLabel();self.engine_capabilities.setWordWrap(True);eng.addWidget(self.engine_capabilities)
        files.addWidget(QLabel("Stockfish executable"))
        files.addWidget(self.engine_path)
        self._button("Browse engine…", self.browse_engine, files)
        self._button("Install official Stockfish", self.install_engine, files)
        self.custom_engine=QLineEdit();self.custom_engine.setPlaceholderText("Custom UCI executable")
        files.addWidget(QLabel("Custom UCI executable"));files.addWidget(self.custom_engine)
        self._button("Browse custom engine…",self.browse_custom_engine,files)
        strength=QFormLayout();strength.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows);self.engine_strength_form=strength
        self.strength_mode=QComboBox();self.strength_mode.addItems(["Full strength","Skill level","Elo rating"])
        strength.addRow("Stockfish strength",self.strength_mode)
        self.engine_skill=QSpinBox();self.engine_skill.setRange(0,20);self.engine_skill.setValue(20);self.engine_skill.setSuffix(" / 20")
        strength.addRow("Engine skill",self.engine_skill)
        self.engine_elo=QSpinBox();self.engine_elo.setRange(1320,3190);self.engine_elo.setValue(1500)
        strength.addRow("Stockfish Elo",self.engine_elo)
        self.human_elo=QSpinBox();self.human_elo.setRange(600,2600);self.human_elo.setValue(1500)
        strength.addRow("Human target rating",self.human_elo)
        self.playing_style=QComboBox();self.playing_style.addItems(["Balanced","Aggressive","Defensive","Human-like","Maximum strength"])
        self.playing_style.setToolTip("Balanced keeps the engine's native choice. Other supported styles rerank close candidates; these are not guaranteed playing personalities. Tiny bots keep their coded style.")
        strength.addRow("Playing style",self.playing_style);eng.addLayout(strength)
        controls = QFormLayout();controls.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows);self.engine_limit_form=controls
        self.mode = QComboBox()
        self.mode.addItems(["Time", "Depth", "Time + depth", "Adaptive"])
        controls.addRow("Analysis limit", self.mode)
        self.seconds = QDoubleSpinBox()
        self.seconds.setRange(.1, 300)
        self.seconds.setSingleStep(.5)
        self.seconds.setSuffix(" s")
        controls.addRow("Think time", self.seconds)
        self.depth = QSpinBox()
        self.depth.setRange(1, 60)
        controls.addRow("Search depth", self.depth)
        self.multipv = QSpinBox()
        self.multipv.setRange(1, 10)
        candidates=QHBoxLayout();self.preset_buttons=[]
        for count in (1,2,3,5):
            preset=self._button(str(count),lambda checked=False,n=count:self.recommendation_preset(n),candidates);preset.setFixedWidth(50);self.preset_buttons.append((count,preset))
        controls.addRow("Suggested moves", self.multipv)
        self.threads = QSpinBox()
        self.threads.setRange(1, max(1, os.cpu_count() or 2))
        self.threads.setToolTip("Threads per board. Each detected board has an independent Stockfish search.")
        controls.addRow("CPU threads", self.threads)
        self.hash_mb = QSpinBox()
        self.hash_mb.setRange(16, 4096)
        self.hash_mb.setSingleStep(64)
        self.hash_mb.setSuffix(" MB")
        controls.addRow("Hash memory", self.hash_mb)
        self.interval = QSpinBox()
        self.interval.setRange(SCREEN_REFRESH_MS, SCREEN_REFRESH_MS)
        self.interval.setSuffix(" ms")
        self.interval.valueChanged.connect(self.timer.setInterval)
        self.interval.hide()
        eng.addLayout(controls)
        eng.addWidget(QLabel("Show moves"));eng.addLayout(candidates)
        self.limit_label=QLabel()
        self.limit_label.setWordWrap(True)
        eng.addWidget(self.limit_label)
        self.seconds.valueChanged.connect(self.update_limit_label)
        self.depth.valueChanged.connect(self.update_limit_label)
        self.early_suggestions = QCheckBox("Show moves while thinking")
        self.early_suggestions.setChecked(True)
        self.early_suggestions.toggled.connect(self.visual_settings_changed)
        eng.addWidget(self.early_suggestions)
        self.predict_continuations=QCheckBox('Predict opponent and my next move');self.predict_continuations.setChecked(True);self.predict_continuations.toggled.connect(self.prediction_controls_changed);eng.addWidget(self.predict_continuations)
        prediction_form=QFormLayout();prediction_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.prediction_plies=QSpinBox();self.prediction_plies.setRange(1,12);self.prediction_plies.setValue(3);self.prediction_plies.setSuffix(' plies')
        self.prediction_plies.setToolTip('A ply is one move by one side. 3 = your move, opponent reply, your response. This applies to Maia 2, every Maia 3 model, and Tiny bots too.')
        self.prediction_seconds=QDoubleSpinBox();self.prediction_seconds.setRange(.1,60);self.prediction_seconds.setValue(3);self.prediction_seconds.setSingleStep(.5);self.prediction_seconds.setSuffix(' s')
        self.prediction_seconds.setToolTip('Budget for calculating extra replies after the first recommendation. No artificial wait. A Maia pass already running may finish after this budget.')
        prediction_form.addRow('Prediction length',self.prediction_plies);prediction_form.addRow('Reply time budget',self.prediction_seconds);eng.addLayout(prediction_form)
        for field in (self.prediction_plies,self.prediction_seconds):field.valueChanged.connect(self.engine_settings_changed)
        refresh_note=QLabel("Screen refresh: 75 ms target.")
        refresh_note.setWordWrap(True)
        self.engine_refresh_note=refresh_note
        eng.addWidget(refresh_note)
        self.mode.currentTextChanged.connect(self.mode_changed)
        note = QLabel("Search limits explained in Help.")
        note.setWordWrap(True)
        self.engine_search_note=note
        eng.addWidget(note)
        self.engine_summary=QLabel();self.engine_summary.setWordWrap(True)
        self.engine_summary.setStyleSheet("background:#20392c;border-radius:6px;padding:10px;color:#a5dfbd;")
        eng.addWidget(QLabel("Configuration"));eng.addWidget(self.engine_summary)
        self._button("Copy configuration",lambda:self.copy_text(engine_config.configuration(self)),eng)
        self.engine_files_toggle=self._button("Engine files ▸",lambda enabled:self.engine_files.setVisible(enabled),eng,True)
        self.engine_files_toggle.toggled.connect(lambda checked:self.engine_files_toggle.setText("Engine files ▾" if checked else "Engine files ▸"))
        self.engine_files.hide();eng.addWidget(self.engine_files)
        compare=QGroupBox("Engine comparison");compare_form=QFormLayout(compare);compare_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.compare_a=QComboBox();self.compare_a.addItems(engine_config.COMPARE_NAMES)
        self.compare_b=QComboBox();self.compare_b.addItems(engine_config.COMPARE_NAMES);self.compare_b.setCurrentIndex(2)
        self.compare_c=QComboBox();self.compare_c.addItems(["None"]+engine_config.COMPARE_NAMES)
        compare_form.addRow("Engine A",self.compare_a);compare_form.addRow("Engine B",self.compare_b);compare_form.addRow("Engine C",self.compare_c)
        compare_button=QPushButton("Compare engines…");compare_button.clicked.connect(self.open_engine_comparison);compare_form.addRow(compare_button)
        self.compare_toggle=self._button("Compare engines ▸",lambda enabled:compare.setVisible(enabled),eng,True);self.compare_toggle.toggled.connect(lambda enabled:self.compare_toggle.setText("Compare engines ▾" if enabled else "Compare engines ▸"));compare.hide();eng.addWidget(compare)
        self._button("Save now", self.save, eng)
        for field in (self.engine_kind,self.strength_mode,self.playing_style,self.compare_a,self.compare_b,self.compare_c):
            field.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon);field.setMinimumContentsLength(8)
        for field in (self.engine_kind,self.strength_mode,self.playing_style):field.currentIndexChanged.connect(self.engine_configuration_changed)
        for field in (self.engine_skill,self.engine_elo,self.human_elo):field.valueChanged.connect(self.engine_configuration_changed)
        self.custom_engine.editingFinished.connect(self.engine_configuration_changed)
        eng.addStretch()
        tabs.addTab(self._scroll(engine), "Engine")
        keys = QWidget()
        key_layout = QVBoxLayout(keys)
        self.global_keys = QCheckBox("Global shortcuts")
        self.global_keys.toggled.connect(self.enable_hotkeys)
        key_layout.addWidget(self.global_keys)
        self.key_fields = {}
        key_form = QFormLayout()
        names = {"suggest": "Suggest", "move": "Play best", "watch": "Auto suggest", "scan": "Find board", "stop": "Stop", "arrows":"Toggle arrows", "previous":"Previous position", "next":"Next position", "live":"Resume live"}
        for action, default in DEFAULT_KEYS.items():
            field = QLineEdit(default)
            self.key_fields[action] = field
            key_form.addRow(names[action], field)
        key_layout.addLayout(key_form)
        self._button("Apply keybinds", self.apply_keys, key_layout)
        key_note = QLabel("Example: <ctrl>+<alt>+s. Escape stops.")
        key_note.setWordWrap(True)
        key_layout.addWidget(key_note)
        key_layout.addStretch()
        tabs.addTab(self._scroll(keys), "Keys")
        display = QWidget()
        display_layout = QVBoxLayout(display)
        self.overlay_enabled = QCheckBox("Screen arrows")
        self.arrow_labels = QCheckBox("Rank labels")
        self.show_white = QCheckBox("White moves")
        self.show_black = QCheckBox("Black moves")
        self.show_reply = QCheckBox("Opponent reply")
        self.rank_best = QCheckBox("#1 · Best move")
        self.rank_second = QCheckBox("#2 · Alternative")
        self.rank_others = QCheckBox("#3 and more")
        for field in (self.overlay_enabled,self.show_white,self.show_black,self.show_reply,self.rank_best,self.rank_second,self.rank_others):
            field.setChecked(field is not self.rank_others)
            display_layout.addWidget(field)
            field.toggled.connect(self.visual_settings_changed)
        display_layout.addWidget(self.arrow_labels)
        self.arrow_labels.toggled.connect(self.visual_settings_changed)
        visual_form=QFormLayout()
        self.arrow_count=QSpinBox()
        self.arrow_count.setRange(1,10)
        self.arrow_count.setValue(2)
        self.arrow_count.valueChanged.connect(self.visual_settings_changed)
        visual_form.addRow("Moves to draw",self.arrow_count)
        display_layout.addLayout(visual_form)
        note=QLabel("Set move count in Engine. Arrows let clicks through.")
        note.setWordWrap(True)
        display_layout.addWidget(note)
        display_layout.addStretch()
        self.threats_enabled=QCheckBox('Threat highlights');self.threat_attacks=QCheckBox('Show attacked squares');self.threat_mates=QCheckBox('Show mate-in-one targets');self.threat_mates.setChecked(True)
        for field in (self.threats_enabled,self.threat_attacks,self.threat_mates):field.toggled.connect(self.visual_settings_changed);display_layout.insertWidget(0,field)
        self.threat_note=QLabel('Red: material at risk · Purple: mate target');self.threat_note.setWordWrap(True);self.threat_note.setStyleSheet('font-size:13px;color:#9eb6a8;');display_layout.insertWidget(3,self.threat_note)
        self.dashed_reply=QCheckBox("Dashed reply");self.dashed_reply.setChecked(False)
        self.dashed_reply.setToolTip("Cyan shows the opponent reply AFTER your suggested move. Turn this on for a dashed shaft.")
        self.dashed_reply.toggled.connect(self.visual_settings_changed);display_layout.insertWidget(0,self.dashed_reply)
        legend=QLabel("Gold: best · Blue: alternative\nCyan: reply after the best move");legend.setWordWrap(True);display_layout.insertWidget(1,legend)
        move_sections=[('Recommendations',(self.overlay_enabled,self.show_white,self.show_black,self.show_reply,self.rank_best,self.rank_second,self.rank_others,self.arrow_labels,self.dashed_reply)),('Threats',(self.threats_enabled,self.threat_attacks,self.threat_mates))]
        for title,fields in move_sections:
            group=QGroupBox(title);column=QVBoxLayout(group);column.setSpacing(8)
            for field in fields:display_layout.removeWidget(field);column.addWidget(field)
            display_layout.insertWidget(0 if title=='Recommendations' else 1,group)
        self.threats_enabled.toggled.connect(lambda enabled:(self.threat_attacks.setEnabled(enabled),self.threat_mates.setEnabled(enabled)))
        self.threat_attacks.setEnabled(False);self.threat_mates.setEnabled(False)
        tabs.addTab(self._scroll(display),"Arrows")
        phone_page=QWidget();phone_layout=QVBoxLayout(phone_page)
        title=QLabel("Phone companion");title.setStyleSheet("font-size:23px;font-weight:600;color:#a5dfbd;")
        phone_layout.addWidget(title)
        intro=QLabel("View boards and settings on your phone.")
        intro.setWordWrap(True);phone_layout.addWidget(intro)
        self.phone_port=QSpinBox();self.phone_port.setRange(1024,65535);self.phone_port.setValue(8789)
        phone_form=QFormLayout();phone_form.addRow("Connection port",self.phone_port);phone_layout.addLayout(phone_form)
        self.phone_button=self._button("Enable phone companion",self.toggle_phone,phone_layout,True)
        self.phone_address=QLineEdit();self.phone_address.setReadOnly(True);self.phone_address.setPlaceholderText("Enable to show your computer address")
        phone_layout.addWidget(QLabel("Computer address"));phone_layout.addWidget(self.phone_address)
        self._button("Copy address",lambda:self.copy_text(self.phone_address.text()),phone_layout)
        self.phone_code=QLineEdit();self.phone_code.setReadOnly(True);self.phone_code.setPlaceholderText("Pairing code")
        self.phone_code.setStyleSheet("font-size:25px;font-weight:700;color:#a5dfbd;")
        phone_layout.addWidget(QLabel("Pairing code"));phone_layout.addWidget(self.phone_code)
        self.phone_connection_status=QLabel("Companion is off");self.phone_connection_status.setWordWrap(True);phone_layout.addWidget(self.phone_connection_status)
        instructions=QLabel("Same Wi-Fi → open the phone app → enter this address and code. More in Help.")
        instructions.setWordWrap(True);phone_layout.addWidget(instructions)
        self.phone_auto=QCheckBox("Start with BoardLens")
        phone_layout.addWidget(self.phone_auto);phone_layout.addStretch()
        tabs.addTab(self._scroll(phone_page),"Phone")
        for index,tip in enumerate(('Board input and app updates','Analysis engine, limits and presets','Keyboard shortcuts','Arrows and threat highlights','Phone and tablet connection')):tabs.setTabToolTip(index,tip)
        self.local_shortcuts=[]
        QShortcut(QKeySequence("Escape"), self).activated.connect(self.stop)
        middle = QWidget()
        self.board_panel = middle
        mid = QVBoxLayout(middle)
        self.position_label = QLabel("White to move")
        position_header=QHBoxLayout()
        self.position_label.setStyleSheet("font-size:16px;font-weight:600;")
        position_header.addWidget(self.position_label,1)
        self.player_label.setStyleSheet("font-size:13px;color:#aec4b6;")
        position_header.addWidget(self.player_label)
        mid.addLayout(position_header)
        self.board_stack=QStackedWidget()
        self.eval_bar = EvalBar()
        self.board_view = BoardView()
        self.board_view.square_clicked.connect(self.practice_click)
        self.board_area=BoardArea(self.board_view,self.eval_bar)
        self.board_stack.addWidget(self.board_area)
        self.empty_panel=QWidget()
        empty=QVBoxLayout(self.empty_panel);empty.setContentsMargins(28,24,28,24)
        empty.addStretch()
        self.empty_title=QLabel("Looking for a chessboard")
        self.empty_title.setWordWrap(True)
        self.empty_title.setStyleSheet("font-size:24px;font-weight:600;color:#a5dfbd;")
        self.empty_detail=QLabel()
        self.empty_detail.setWordWrap(True)
        self.empty_detail.setStyleSheet("font-size:16px;color:#b3c9bc;")
        empty.addWidget(self.empty_title);empty.addSpacing(12);empty.addWidget(self.empty_detail)
        empty.addSpacing(16)
        self.empty_scan_button=self._button("Scan now",self.scan_now,empty)
        empty.addStretch()
        self.board_stack.addWidget(self.empty_panel)
        mid.addWidget(self.board_stack,1)
        self.simple_label=QLabel("Best move — waiting for analysis")
        self.simple_label.setWordWrap(True)
        self.simple_label.setStyleSheet("font-size:19px;font-weight:600;color:#b6edcb;")
        mid.addWidget(self.simple_label)
        self.reply_label=QLabel("")
        self.reply_label.setWordWrap(True)
        mid.addWidget(self.reply_label)
        history=QHBoxLayout()
        self.previous_button=self._button("Previous", self.history_previous, history)
        self.next_button=self._button("Next", self.history_next, history)
        self.resume_button=self._button("Resume live", self.resume_live, history)
        mid.addLayout(history)
        self.eval_label = QLabel("Evaluation —")
        self.eval_label.setWordWrap(True)
        mid.addWidget(self.eval_label)
        self.fen = QLineEdit(chess.STARTING_FEN)
        self.fen.setPlaceholderText("Paste a full FEN")
        self.fen.setToolTip("FEN records pieces, turn, castling, en passant, and move counters.")
        self.fen_panel = QWidget()
        fen_layout = QVBoxLayout(self.fen_panel)
        fen_layout.setContentsMargins(0,0,0,0)
        fen_layout.addWidget(self.fen)
        pos_buttons = QHBoxLayout()
        self._button("Load FEN", self.load_fen, pos_buttons)
        self._button("Copy FEN", self.copy_fen, pos_buttons)
        self._button("New game", self.new_game, pos_buttons)
        self._button("Undo", self.undo, pos_buttons)
        pos_buttons.addWidget(self.move_button)
        fen_layout.addLayout(pos_buttons)
        mid.addWidget(self.fen_panel)
        split.addWidget(middle)
        right = QWidget()
        self.analysis_panel = right
        right_layout = QVBoxLayout(right)
        analysis_header=QHBoxLayout()
        analysis_title=QLabel("Live chess analysis")
        analysis_title.setStyleSheet("font-size:19px;font-weight:600;")
        analysis_header.addWidget(analysis_title,1)
        self.full_analysis_button=self._button("Full analysis",self.open_full_analysis,analysis_header)
        right_layout.addLayout(analysis_header)
        self.lines = QTextBrowser()
        self.lines.setOpenExternalLinks(True)
        self.lines.setStyleSheet("font-size:16px;")
        self.lines.setMinimumSize(300,300)
        self.lines.document().setDefaultFont(QFont("Arial",12))
        self.lines.document().setDefaultStyleSheet(ANALYSIS_STYLE)
        self.lines.setLineWrapMode(QTextBrowser.LineWrapMode.WidgetWidth)
        self.lines.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        right_layout.addWidget(self.lines, 1)
        self.capture_label = QLabel("",right)
        self.capture_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.capture_label.setFixedHeight(150)
        self.capture_label.hide()
        split.addWidget(right)
        split.setSizes([680,420])
        layout.removeWidget(split)
        self.workspace_stack=QStackedWidget()
        self.workspace_stack.addWidget(split)
        self.workspace_stack.addWidget(self.multi.page)
        self.full_analysis_page=QWidget()
        full_layout=QVBoxLayout(self.full_analysis_page)
        full_header=QHBoxLayout()
        self._button("Back to boards",self.close_full_analysis,full_header)
        full_header.addStretch()
        self._button("Text −",lambda:self.resize_analysis_text(-1),full_header)
        self._button("Text +",lambda:self.resize_analysis_text(1),full_header)
        full_layout.addLayout(full_header)
        self.full_analysis_browser=QTextBrowser()
        self.full_analysis_browser.setStyleSheet("font-size:16px;")
        self.full_analysis_browser.document().setDefaultFont(QFont("Arial",12))
        self.full_analysis_browser.document().setDefaultStyleSheet(ANALYSIS_STYLE)
        self.full_analysis_browser.setLineWrapMode(QTextBrowser.LineWrapMode.WidgetWidth)
        self.full_analysis_browser.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        full_layout.addWidget(self.full_analysis_browser,1)
        self.workspace_stack.addWidget(self.full_analysis_page)
        body=QWidget();body_layout=QHBoxLayout(body);body_layout.setContentsMargins(0,0,0,0)
        nav=QVBoxLayout()
        self.boards_button=self._button("Boards",lambda *_:self.show_all_boards(True),checkable=True)
        self.boards_button.setFixedWidth(60)
        self.boards_button.setToolTip("Show all detected boards together; click to open a larger view.")
        self.boards_button.hide();nav.addWidget(self.boards_button)
        self.focus_button=self._button("Focus",lambda *_:self.show_all_boards(False))
        self.focus_button.setFixedWidth(60);self.focus_button.hide();nav.addWidget(self.focus_button)
        nav.addStretch()
        body_layout.addLayout(nav)
        self.sidebar_host=QWidget();self.sidebar_host.setFixedWidth(320)
        side_layout=QVBoxLayout(self.sidebar_host);side_layout.setContentsMargins(0,0,0,0)
        side_layout.addWidget(tabs)
        body_layout.addWidget(self.sidebar_host)
        body_layout.addWidget(self.workspace_stack,1)
        layout.addWidget(body,1)
        self.board_area.setMinimumHeight(330)
        self.update_history_controls()
        self.status_label = QLabel()
        self.status_label.setObjectName("status")
        self.status_label.setWordWrap(True)
        self.status_label.setMaximumHeight(80)
        layout.addWidget(self.status_label)
        self.copy_notice=QLabel('',self.centralWidget());self.copy_notice.setStyleSheet('background:#a3e3bb;color:#123521;border:1px solid #bbeacf;border-radius:8px;padding:10px 16px;font-weight:600;');self.copy_notice.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents);self.copy_notice.hide()
        self.copy_notice_timer=QTimer(self);self.copy_notice_timer.setSingleShot(True);self.copy_notice_timer.setInterval(2200);self.copy_notice_timer.timeout.connect(self.copy_notice.hide)
        self.toggle_compact(False)

    @staticmethod
    def _scroll(widget):
        return ResponsiveScrollArea(widget)

    @property
    def white_bottom(self):
        return self._white_bottom if self.orientation.currentIndex() == 0 else self.orientation.currentIndex() == 1

    @property
    def practice(self):
        return self.source.currentIndex() == 0

    def status(self, message):
        if not self.closing:
            if getattr(getattr(self, 'permissions', None), 'blocked', False) and not self.practice:
                message = self.permissions.reason + ' permission required · screen reading is paused'
            self.status_label.setText(message)

    def native_access_changed(self,enabled):
        if not enabled or sys.platform!='darwin' or os.environ.get('BOARDLENS_TEST_MODE'):return
        try:
            from .native_chess import accessibility_allowed
            self._native_access_ok=accessibility_allowed()
            if not self._native_access_ok and self._ready:self.status('Local 3D reading needs Accessibility. Open Board → App → Permissions.')
        except Exception as exc:self.status('Could not check local 3D access: '+str(exc))

    def update_foreground(self,kind=None):
        self._native_enabled=self.native_reader_button.isChecked()
        if not self.browser_reader and not self._native_enabled and not self.target_lock.active:return
        route=kind or foreground_kind()
        if route=='self':route=self._last_external_route or self._scan_route or 'browser'
        else:self._last_external_route=route
        if self.target_lock.active:route=self.target_lock.route
        if self._scan_route is not None and route!=self._scan_route:
            self.live_worker.cancel();self._live_token+=1;self._scan_busy=False
            self.region=None;self._last_read=None;self._screen_confirmed=False;self._position_locked=False
            self._stable_key=None;self._stable_frames=0;self._force_full_scan=True;self._lost_frames=0
            self.multi.reset();self.invalidate(release_move=True)
            self.status('App changed · finding its board…')
        self._scan_route=route

    def direct_reads(self):
        if self.target_lock.active and not self.target_lock.target.get('source'):return []
        reads=self.browser_reader.reads() if self.browser_reader and self._scan_route=='browser' else []
        if self._native_enabled and self._scan_route=='native':
            reads+=self.native_reader.reads()
            if not reads and self.native_reader.status.startswith('Enable macOS Accessibility'):raise ValueError(self.native_reader.status)
        if self.target_lock.active:
            reads=self.target_lock.filter(reads)
            if not reads:raise ValueError('Locked board unavailable.')
        return reads[:3]

    def toggle_browser_reader(self,enabled):
        if self.browser_reader:self.browser_reader.close();self.browser_reader=None
        if not enabled:self.browser_reader_key.clear();return
        try:
            from .direct_boards import BrowserReader
            self.browser_reader=BrowserReader();self.browser_reader_key.setText(self.browser_reader.token)
            self.status("Browser reader ready · pair the extension with this key. Scan now follows its visible boards.")
        except OSError as exc:
            self.browser_reader_button.setChecked(False);self.status("Could not start browser reader: "+str(exc))

    def reader_setup(self):
        QMessageBox.information(self,"Connect a browser","This optional connection reads Chess.com and Lichess positions directly, including supported themes and 3D boards. Standard 2D boards can use Computer screen without it.\n\n1. Open chrome://extensions (or edge://extensions), enable Developer mode, click Load unpacked, and select BoardLens 2/BrowserReader.\n2. Copy the pairing key in BoardLens. Open the extension's toolbar popup, paste the key and click Connect.\n3. Reload the chess tab and keep it visible. BoardLens shows the connection status here.\n\nThe connection stays on this computer and never plays moves. The local 3D chess reader uses its separate option.")

    def publish_reader_hints(self):
        self.browser_reader_status.setText(self.browser_reader.connection_status().replace('Reader','Browser connection') if self.browser_reader else 'Browser connection off')
        if self.native_reader_button.isChecked():
            current=getattr(self._last_read,'source_id','') or ''
            native_status='Connected · local 3D chess board found' if current.startswith('native:') and self._screen_confirmed else ('Accessibility permission needed · see Help' if getattr(self,'_native_access_ok',None) is False else 'Ready · switch to your local 3D chess board')
            self.native_connection_status.setText(native_status)
        if not self.browser_reader:return
        hints={}
        sources=[(self._last_read,self.tracker,self.board_view.arrows,self.board_view.marks,self._screen_confirmed)]
        sources += [(state.read,state.tracker,state.card.view.arrows,state.card.view.marks,state.confirmed) for state in self.multi.states]
        if self._monitoring and not self._reviewing and self.overlay_enabled.isChecked():
            for read,tracker,arrows,marks,confirmed in sources:
                if read and tracker and confirmed and getattr(read,'source_id','').startswith('browser:'):
                    hints[read.source_id]={'fen':getattr(read,'visible_fen',None) or getattr(read,'exact_fen',None) or tracker.board.fen(),
                        'arrows':[{'move':a['move'].uci(),'color':a['color']} for a in arrows],
                        'marks':[dict(m,square=chess.square_name(m['square'])) for m in marks]}
        self.browser_reader.publish(hints)

    def toggle_phone(self,enabled):
        if not enabled:
            self.phone.close();self.phone_button.setText("Enable phone companion")
            self.phone_port.setEnabled(True);self.phone_address.clear();self.phone_code.clear()
            self.phone_connection_status.setText("Companion is off")
            return
        try:
            addresses,code=self.phone.start(self.phone_port.value())
            self.phone_address.setText(addresses[0]);self.phone_address.setCursorPosition(0)
            self.phone_code.setText(code);self.phone_port.setEnabled(False)
            self.phone_button.setText("Disable phone companion")
            self.phone_connection_status.setText("Ready to pair · use the same Wi-Fi")
        except OSError as exc:
            self.phone_button.setChecked(False)
            self.phone_connection_status.setText(f"Could not open the connection: {exc}. Try another port.")

    def open_full_analysis(self):
        self.workspace_stack.setCurrentIndex(2)
        self.sidebar_host.hide()

    def close_full_analysis(self):
        self.sidebar_host.setVisible(not self._compact)
        self.workspace_stack.setCurrentIndex(1 if self.multi.count>1 else 0)

    def resize_analysis_text(self,amount):
        font=self.lines.document().defaultFont()
        size=font.pixelSize() if font.pixelSize()>0 else round(font.pointSizeF()*96/72)
        size=max(14,min(30,size+2*amount))
        for view in (self.lines,self.full_analysis_browser):
            view.setStyleSheet(f"font-size:{size}px;")
            changed=view.document().defaultFont();changed.setPixelSize(size)
            view.document().setDefaultFont(changed)

    def monitor_description(self):
        key=self.monitor.currentData()
        if key=='*':return "all monitors"
        return self.monitor.currentText().split(' · ')[0].split(': ',1)[-1] or "the selected monitor"

    def show_empty_board(self,title="Looking for a chessboard"):
        self.board_stack.setCurrentIndex(1)
        self.board_view.hide();self.eval_bar.hide()
        self.empty_title.setText(title)
        self.region_label.setText("No board detected on "+self.monitor_description())
        self.empty_detail.setText(f"Watching {self.monitor_description()}. Open a complete 2D chessboard there, or choose another monitor in Board settings. The board and evaluation will appear after a clear read.")
        self.position_label.setText("Live screen · no confirmed board")
        self.simple_label.clear();self.reply_label.clear()
        for widget in (self.simple_label,self.reply_label,self.eval_label,self.previous_button,self.next_button,self.resume_button):widget.hide()
        self.fen_panel.hide()
        self.eval_label.setText("Evaluation — waiting for a board")
        self.player_label.setText("Watching: "+self.monitor_description())
        self.player_label.hide()
        self.show_welcome()

    def show_board_surface(self):
        self.board_stack.setCurrentIndex(0)
        self.board_view.show();self.eval_bar.show();self.player_label.show()
        for widget in (self.simple_label,self.eval_label,self.previous_button,self.next_button,self.resume_button):widget.show()
        self.reply_label.setVisible(bool(self.reply_label.text()))
        self.fen_panel.setVisible(self.practice and not self._compact)
        self.board_area.arrange()

    def show_welcome(self):
        if self.source.currentIndex()==1 and not self._screen_confirmed and not self._reviewing:
            self.set_analysis_html("<h2>Waiting for a board</h2><p>Live analysis appears here after a position is recognized.</p><p>Use <b>Scan now</b> to refresh. Check <b>Monitor to scan</b> in Board settings if the game is on another display.</p>")
        else:
            self.set_analysis_html("<h2>Ready to analyze</h2><p>Press <b>Suggest</b> for the best move, evaluation and continuations.</p><p>Positive scores favor White; negative scores favor Black. <b>Full analysis</b> gives the text the entire workspace.</p>")

    def set_analysis_html(self,markup,fen=None):
        views=(self.lines,self.full_analysis_browser)
        positions=[v.verticalScrollBar().value() for v in views] if fen and getattr(self,'_analysis_fen',None)==fen else [0,0]
        self._analysis_fen=fen
        for view,position in zip(views,positions):
            view.setHtml(markup)
            view.verticalScrollBar().setValue(position)

    def restore(self):
        for name, default in (("seconds", 1.), ("depth", 18), ("multipv", 3), ("threads", 2), ("hash_mb", 128), ("interval", SCREEN_REFRESH_MS)):
            value = self.settings.get(name, default)
            try:
                getattr(self, name).setValue(float(value) if name == "seconds" else int(value))
            except (TypeError, ValueError, OverflowError):
                getattr(self, name).setValue(default)
        saved_mode = self.settings.get("mode", "Time")
        self.mode.setCurrentText(saved_mode if isinstance(saved_mode, str) else "Time")
        self.mode_changed()
        saved_keys = self.settings.get("keys", {})
        if not isinstance(saved_keys, dict):
            saved_keys = {}
        for name, field in self.key_fields.items():
            field.setText(str(saved_keys.get(name, DEFAULT_KEYS[name])))
        for name in ("overlay_enabled","arrow_labels","show_white","show_black","show_reply","rank_best","rank_second","rank_others","only_my_color","early_suggestions","stick_to_move","steady_arrows"):
            field=getattr(self,name)
            field.setChecked(bool(self.settings.get(name,field.isChecked())))
        self.arrow_count.setValue(int(self.settings.get("arrow_count",2)))
        self.phone_port.setValue(int(self.settings.get("phone_port",8789)))
        self.phone_auto.setChecked(bool(self.settings.get("phone_auto",False)))
        self.browser_reader_button.setChecked(bool(self.settings.get("browser_reader_enabled",False)))
        self.native_reader_button.setChecked(bool(self.settings.get("native_reader_enabled",False)))
        self.custom_engine.setText(str(self.settings.get('custom_engine','')))
        for name,default in (('engine_kind',0),('playing_style',0),('strength_mode',0),('compare_a',0),('compare_b',2),('compare_c',0)):
            getattr(self,name).setCurrentIndex(int(self.settings.get(name,default)))
        for name,default in (('engine_skill',20),('engine_elo',1500),('human_elo',1500)):
            getattr(self,name).setValue(int(self.settings.get(name,default)))
        self.dashed_reply.setChecked(bool(self.settings.get('dashed_reply',False)))
        self.orientation.setCurrentIndex(0 if self.only_my_color.isChecked() else int(self.settings.get('orientation_index',0)))
        self.turn.setCurrentIndex(int(self.settings.get('turn_index',0)))
        self.always_top.setChecked(bool(self.settings.get('always_top',False)))
        for name,default in (('threats_enabled',False),('threat_attacks',False),('threat_mates',True)):getattr(self,name).setChecked(bool(self.settings.get(name,default)))
        saved_target=self.settings.get('target_lock')
        if int(self.settings.get('source_index',1))==1 and self.target_lock.restore(saved_target):
            try:
                region=BoardRegion(**saved_target['region'])
                if region.size>=80:
                    self.target_lock.target=saved_target;self.region=region;self._scan_route=saved_target['route'];self.lock_target.blockSignals(True);self.lock_target.setChecked(True);self.lock_target.blockSignals(False);self.target_status.setText('Locked target · waiting for a read')
            except (TypeError,ValueError):pass
        for name,default in (('eval_seconds',.3),('eval_depth',18),('eval_human_elo',1500),('prediction_plies',3),('prediction_seconds',3.)):getattr(self,name).setValue(self.settings.get(name,default))
        self.eval_engine.setCurrentIndex(max(0,self.eval_engine.findData(self.settings.get('eval_engine_id',0))))
        self.predict_continuations.setChecked(bool(self.settings.get('predict_continuations',True)))
        self.engine_configuration_changed();self.evaluation_settings_changed();self.prediction_controls_changed()
        self.preset_combo.blockSignals(True);self.preset_combo.setCurrentIndex(max(0,self.preset_combo.findData(self.settings.get('active_preset'))));self.preset_combo.blockSignals(False)
        self.source_controls()
        if not os.environ.get('BOARDLENS_TEST_MODE'):
            self.toggle_compact(bool(self.settings.get('compact',False)))
            geometry=self.settings.get('window_geometry')
            if isinstance(geometry,list) and len(geometry)==4 and all(isinstance(v,int) for v in geometry):
                from PySide6.QtCore import QRect
                rectangle=QRect(*geometry)
                if any(screen.availableGeometry().intersects(rectangle) for screen in QGuiApplication.screens()):
                    # Old releases saved expanded mode at the compact width.
                    # Clamp to the actual mode's minimum before restoring it.
                    preferred=1400 if not self._compact and rectangle.width()<1180 else rectangle.width()
                    rectangle.setWidth(max(self.minimumWidth(),preferred))
                    rectangle.setHeight(max(self.minimumHeight(),rectangle.height()))
                    screen=max(QGuiApplication.screens(),key=lambda item:item.availableGeometry().intersected(rectangle).width())
                    g=screen.availableGeometry()
                    rectangle.setWidth(min(rectangle.width(),g.width()-20))
                    rectangle.setHeight(min(rectangle.height(),g.height()-40))
                    rectangle.moveLeft(max(g.left(),min(rectangle.left(),g.right()-rectangle.width())))
                    rectangle.moveTop(max(g.top(),min(rectangle.top(),g.bottom()-rectangle.height())))
                    self.setGeometry(rectangle)

    def save(self, checked=False,quiet=False):
        values = {name: getattr(self, name).value() for name in ("seconds", "depth", "multipv", "threads", "hash_mb", "interval")}
        values.update(source_index=self.source.currentIndex(),orientation_index=self.orientation.currentIndex(),turn_index=self.turn.currentIndex(),always_top=self.always_top.isChecked(),browser_reader_enabled=self.browser_reader_button.isChecked(),native_reader_enabled=self.native_reader_button.isChecked(),phone_port=self.phone_port.value(),phone_auto=self.phone_auto.isChecked(),compact=self._compact,window_geometry=list(self.geometry().getRect()),monitor_key=self.monitor.currentData(),
                      engine=self.engine_path.text().strip(), mode=self.mode.currentText(),
                      keys={name: field.text().strip() for name, field in self.key_fields.items()})
        values.update({name:getattr(self,name).isChecked() for name in
            ("overlay_enabled","arrow_labels","show_white","show_black","show_reply","rank_best","rank_second","rank_others","only_my_color","early_suggestions","global_keys","stick_to_move","steady_arrows")})
        values.update({name:getattr(self,name).currentIndex() for name in ('engine_kind','playing_style','strength_mode','compare_a','compare_b','compare_c')})
        values.update({name:getattr(self,name).value() for name in ('engine_skill','engine_elo','human_elo')})
        values.update(eval_engine_id=self.eval_engine.currentData(),eval_seconds=self.eval_seconds.value(),eval_depth=self.eval_depth.value(),eval_human_elo=self.eval_human_elo.value(),predict_continuations=self.predict_continuations.isChecked(),prediction_plies=self.prediction_plies.value(),prediction_seconds=self.prediction_seconds.value())
        values.update(custom_engine=self.custom_engine.text(),dashed_reply=self.dashed_reply.isChecked())
        values.update(arrow_count=self.arrow_count.value(),threats_enabled=self.threats_enabled.isChecked(),threat_attacks=self.threat_attacks.isChecked(),threat_mates=self.threat_mates.isChecked(),target_lock=self.target_lock.target,active_preset=self.preset_combo.currentData())
        try:
            try:validate_keys(values['keys'])
            except ValueError:values['keys']=self.settings.get('keys',DEFAULT_KEYS)
            save_settings(values);self.settings=values
            if not quiet:self.status("Preferences saved.")
        except OSError as exc:
            self.status(f"Could not save preferences: {exc}")

    def prediction_controls_changed(self,*_):
        for field in (self.prediction_plies,self.prediction_seconds):field.setEnabled(self.predict_continuations.isChecked())
        self.engine_settings_changed()

    def mode_changed(self, *_):
        self.seconds.setEnabled((engine_config.is_tiny(self) or self.mode.currentText() != "Depth") and not engine_config.is_human(self))
        self.depth.setEnabled(self.mode.currentText() != "Time" and not engine_config.is_human(self) and not engine_config.is_tiny(self))
        self.update_limit_label()

    def update_limit_label(self,*_):
        if not hasattr(self,'limit_label'):return
        mode=self.mode.currentText()
        limit=(f"{self.seconds.value():g} seconds" if mode=='Time' else f"depth {self.depth.value()}" if mode=='Depth' else
               f"{self.seconds.value():g} seconds or depth {self.depth.value()}, whichever comes first")
        if mode=="Adaptive":limit=f"adaptive search, up to {self.seconds.value():g}s and depth {self.depth.value()}"
        if engine_config.is_tiny(self):limit=f"{self.seconds.value():g}s bot clock budget (no depth control)"
        self.limit_label.setText("Maia: one pass per position. Use prediction length and reply budget below." if engine_config.is_human(self) else "Active search limit: "+limit)
        self.update_engine_summary()

    def set_always_top(self, enabled):
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, enabled)
        self.show()

    def refresh_monitors(self, *_):
        previous = self.monitor.currentData()
        self.monitor.blockSignals(True)
        self.monitor.clear()
        for index, screen in enumerate(QGuiApplication.screens()):
            g = screen.geometry()
            self.monitor.addItem(f"{index + 1}: {screen.name()} · {g.width()}×{g.height()}", screen_key(screen))
        self.monitor.addItem("All monitors (find boards)", "*")
        if previous:
            self.monitor.setCurrentIndex(max(0, self.monitor.findData(previous)))
        self.monitor.blockSignals(False)

    def monitors_changed(self, *_):
        self.stop()
        self.region = None
        self.multi.reset()
        self.refresh_monitors()
        self.region_label.setText("Monitor changed — finding the board again")
        if self.source.currentIndex() == 1:
            self.start_live()

    def monitor_changed(self, *_):
        if self._ready and self.source.currentIndex() == 1:
            self.stop()
            self.region = None
            self.multi.reset()
            self.start_live()

    def source_changed(self, *_):
        self.stop()
        self._reviewing = False
        self._history.clear()
        self.multi.reset()
        self._history_index = -1
        self.source_controls()
        self.last_observation = None
        self.stable_count = 0
        self.invalidate(release_move=True)
        self._last_read = None
        if self.source.currentIndex()==1:self.show_empty_board()
        else:self.show_board_surface()
        self._position_locked = False
        self._turn_known = False
        if self._ready and self.source.currentIndex() == 1:
            self.start_live(compact=True)
        else:
            self.status("Practice board ready." if self.practice else "Open a board screenshot.")

    def orientation_changed(self, *_):
        self.stop()
        self.last_observation = None
        self.stable_count = 0
        self.invalidate()
        self.refresh_board()
        if self._ready and self.source.currentIndex() == 1:
            self.start_live()

    def clicks_changed(self,enabled):
        if not enabled:self.clicker.cancel()

    def select_board(self, detect=True):
        self.scan_now()

    def scan_now(self, checked=False):
        if self.source.currentIndex()!=1:
            self.source.setCurrentIndex(1)
        if self._reviewing and self._history:
            self.tracker=PositionTracker(self._history[-1]['board'])
        self._reviewing=False
        self._history_index=len(self._history)-1
        # Invalidate both worker generations before starting discovery. A late
        # observation/search from the previous board cannot overwrite refresh.
        self._live_token+=1
        self.live_worker.cancel()
        self._scan_busy=False
        self._scan_again=False
        self.multi.reset()
        self.invalidate(release_move=True)
        self.show_empty_board("Refreshing from screen…")
        self.region=None
        self._last_read=None
        self._last_read_at=0.
        self._screen_confirmed=False
        self._stable_key=None
        self._stable_frames=0
        self._position_locked=False
        self._lost_frames=0
        self._force_full_scan=True
        self._monitoring=True
        self.live_button.setChecked(True)
        self.update_history_controls()
        self.status("Refreshing · finding and reading the visible board again…")
        self.request_scan(force=True)

    def finish_select(self, screens, detect=True):
        self.scan_now()

    def open_image(self):
        self.stop()
        path, _ = QFileDialog.getOpenFileName(self, "Open board screenshot", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if not path:return
        image=cv2.imread(path)
        if image is None:
            self.status("Could not read that image.")
            return
        self.source.setCurrentIndex(2)
        self.status("Finding the chessboard in the screenshot…")
        QApplication.processEvents()
        read=self._recognizer.scan(image)
        if read is None:
            self.status("No complete supported chessboard found. Try a clear image of the whole board.")
            return
        self.snapshot=read.image.copy()
        self._white_bottom=read.white_bottom
        self._last_read=read
        board,_=position_from_read(read)
        self.set_position(board)
        self.preview(self.snapshot)
        self.suggest()

    def screen(self):
        if not self.region:
            raise ValueError("Find or select a board first.")
        for screen in QGuiApplication.screens():
            if screen_key(screen) == self.region.screen_name:
                return screen
        raise ValueError("The selected monitor is disconnected.")

    def board_image(self):
        if self.source.currentIndex() == 2:
            if self.snapshot is None:
                raise ValueError("Open a screenshot first.")
            return self.snapshot.copy()
        if self.practice:
            raise ValueError("The practice board already has an exact position; no recognition is needed.")
        screen = self.screen()
        rect = self.region.desktop_rect(screen.geometry())
        for window in QApplication.topLevelWidgets():
            if not getattr(window,"is_board_overlay",False) and window.isVisible() and not window.isMinimized() and window.frameGeometry().intersects(rect):
                raise ValueError("Move BoardLens away from the target board so it stays fully visible.")
        return self.region.crop(capture(screen))

    def preview(self, image):
        pixmap = bgr_pixmap(image)
        self.capture_label.setPixmap(pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def learn(self):
        try:
            self.stop()
            image = self.board_image()
            templates = Templates.learn(image, chess.Board(), self.white_bottom)
            if not templates.complete:
                raise ValueError("Use the full standard starting position so every piece is learned.")
            templates.save(data_dir() / "templates.npz")
            self.templates = templates
            self.style_label.setText("Board style learned and saved")
            self.set_position(chess.Board())
            self.preview(image)
            self.status("Style learned. Verify the mirrored board, then use Read / sync or Auto suggest.")
        except Exception as exc:
            self.status(str(exc))

    def observe(self):
        image = self.board_image()
        self.preview(image)
        read = self._recognizer.read(image, self.white_bottom)
        if not read.reliable:
            raise ValueError("The visible position is changing or covered. Waiting for the next clear frame.")
        return read.symbols

    def sync(self, stable=False):
        symbols = self.observe()
        if symbols == self.last_observation:
            self.stable_count += 1
        else:
            self.last_observation, self.stable_count = symbols, 1
        if stable and self.stable_count < 2:
            raise ValueError("Waiting for a stable board…")
        state, move = self.tracker.update(symbols, self.white_bottom)
        if state == "unmatched":
            raise ValueError("Position is out of sync. Load its FEN or use Import recognized position with the correct turn and rights.")
        if state == "moved":
            self.pending_until = 0
            self.invalidate()
            self.refresh_board()
        return symbols

    def read_once(self):
        if self.source.currentIndex() == 1:
            self.scan_now()
            return
        try:
            if self.practice:
                self.status("Practice board is already synchronized.")
                return
            self.sync()
            self.status("Position synchronized. Check the mirrored board before suggesting moves.")
        except Exception as exc:
            self.invalidate()
            self.status(str(exc))

    def import_recognized(self):
        try:
            self.stop()
            symbols = self.observe()
            board = board_from_symbols(symbols, self.white_bottom, self.turn.currentIndex() != 2, self.castling.text())
            self.set_position(board)
            self.status("Position imported. For en passant or exact move history, paste the full FEN instead.")
        except Exception as exc:
            self.status(str(exc))

    def invalidate(self, preserve_eval=False, release_move=False):
        if release_move or (self._pinned_result and self._pinned_result['fen']!=self.tracker.board.fen()):
            self._pinned_result=None
        retained=(self.result or self._pinned_result) if self._pinned_result and self.stick_to_move.isChecked() else None
        self.generation += 1
        self.hint_filter.reset()
        if self.job:
            self.job.cancel()
            self.job = None
        self.result = None
        self.last_requested_fen = None
        self._overlay_grace_until=0.
        if retained:
            self.render_result(dict(retained,waiting_for_analysis=True))
            return
        if hasattr(self, "board_view"):
            self.simple_label.setText("Best move — waiting for analysis")
            self.reply_label.clear()
            self.board_view.best_move = None
            self.board_view.arrows = []
            self.overlay.hide()
            self.board_view.update()
            if not preserve_eval:
                self.eval_bar.cp, self.eval_bar.mate = None, None
            self.eval_bar.update()
            self.eval_label.setText("Updating evaluation…" if preserve_eval else "Evaluation — waiting for analysis")
            if not preserve_eval:
                self.show_welcome()

    def set_position(self, board):
        self.invalidate(release_move=True)
        self.tracker = PositionTracker(board)
        self._turn_known = True
        self._position_locked = True
        self.last_sent_fen = None
        self.pending_until = 0
        self.last_observation = None
        self.stable_count = 0
        self.board_view.selected = None
        self.refresh_board()

    def refresh_board(self):
        if self.practice or self.source.currentIndex()==2 or self._reviewing or self._screen_confirmed:self.show_board_surface()
        else:self.show_empty_board()
        board = self.tracker.board
        self.board_view.board = board.copy()
        self.board_view.white_bottom = self.white_bottom
        self.board_view.update()
        self.eval_bar.white_bottom = self.white_bottom
        self.eval_bar.update()
        self.fen.setText(board.fen())
        self.player_label.setText(f"{'White' if self.white_bottom else 'Black'} at bottom")
        side = "White" if board.turn else "Black"
        outcome = board.outcome()
        text = f"Game over · {board.result()}" if outcome else f"{side} to move · move {board.fullmove_number}"
        if outcome:
            self.eval_bar.cp = 100000 if outcome.winner is True else -100000 if outcome.winner is False else 0
            self.eval_bar.mate = None
            self.eval_bar.update()
            self.eval_label.setText(f"Game over · {board.result()}")
        if self.only_my_color.isChecked() and board.turn!=self.white_bottom and not outcome:
            self.simple_label.setText(f"Waiting for your turn · you are {'White' if self.white_bottom else 'Black'}")
            self.reply_label.clear()
        if not outcome and board.is_check():
            text += " · check"
        self.position_label.setText(text)
        if self.source.currentIndex() == 1 and not self._turn_known:
            self.position_label.setText(text + " · turn inferred")

    def load_fen(self):
        try:
            board = chess.Board(self.fen.text().strip())
            if not board.is_valid():
                raise ValueError("The FEN describes an invalid position.")
            self.stop()
            self.set_position(board)
            self.status("FEN loaded. Analysis uses its side to move, castling and en passant rights.")
        except ValueError as exc:
            self.status(f"Could not load FEN: {exc}")

    def threat_marks(self,board,bottom):
        return threat_presentation(board,bottom,self.threats_enabled.isChecked(),self.threat_attacks.isChecked(),self.threat_mates.isChecked())

    def refresh_targets(self):
        if not hasattr(self,'target_board'):return
        selected=self.target_board.currentData();self.target_board.blockSignals(True);self.target_board.clear();self.target_board.addItem('Board 1',0)
        for index,state in enumerate(self.multi.states,2):self.target_board.addItem(f'Board {index}',state.identity)
        self.target_board.setCurrentIndex(max(0,self.target_board.findData(selected)));self.target_board.blockSignals(False);self.target_board.setVisible(self.multi.count>1 and not self.target_lock.active)

    def target_lock_changed(self,enabled):
        if enabled:
            state=next((s for s in self.multi.states if s.identity==self.target_board.currentData()),None)
            read=state.read if state else self._last_read;region=state.region if state else self.region
            if not (state.confirmed if state else self._screen_confirmed):
                self.lock_target.blockSignals(True);self.lock_target.setChecked(False);self.lock_target.blockSignals(False);self.status('Read a board before locking it.');return
            try:self.target_lock.capture(read,region,self._scan_route or 'other')
            except ValueError as exc:self.lock_target.setChecked(False);self.status(str(exc));return
            if state and state.tracker:
                self.tracker=PositionTracker(state.tracker.board);self.region=state.region;self._last_read=state.read;self._white_bottom=state.read.white_bottom;self.invalidate(release_move=True);self.refresh_board()
            self.multi.reset();self.target_status.setText('Locked · follows this board only')
        else:self.target_lock.clear();self.target_status.setText('Automatic board selection');self._force_full_scan=True
        self.refresh_targets();self.queue_autosave();self.update_visuals()

    def mark_custom_preset(self):
        if not self._applying_preset and hasattr(self,'preset_combo') and self.preset_combo.currentData() is not None:
            self.preset_combo.blockSignals(True);self.preset_combo.setCurrentIndex(0);self.preset_combo.blockSignals(False)

    def preset_selected(self,index):
        identity=self.preset_combo.itemData(index)
        if identity:
            try:self.analysis_presets.apply_preset(identity);self.status('Preset loaded. Settings save automatically.')
            except (ValueError,OSError) as exc:self.mark_custom_preset();self.status(str(exc))

    def save_named_preset(self):
        name,ok=QInputDialog.getText(self,'Save analysis preset','Preset name',text='My preset')
        if ok:
            try:self.analysis_presets.save_preset(name);self.status('Analysis preset saved.')
            except (ValueError,OSError) as exc:self.status(str(exc))

    def manage_presets(self):
        items=[p for p in self.analysis_presets.store.list() if not p['builtin']]
        if not items:self.status('Save a custom preset first.');return
        selected,ok=QInputDialog.getItem(self,'Manage presets','Choose preset',[p['name'] for p in items],editable=False)
        if not ok:return
        item=next(p for p in items if p['name']==selected)
        action,ok=QInputDialog.getItem(self,'Manage '+selected,'Action',['Update from current settings','Rename','Remove'],editable=False)
        if not ok:return
        try:
            if action=='Update from current settings':self.analysis_presets.save_preset(item['name'],item['id'])
            elif action=='Remove':self.analysis_presets.store.delete(item['id']);self.analysis_presets.refresh_presets()
            else:
                name,ok=QInputDialog.getText(self,'Rename preset','New name',text=item['name'])
                if ok:self.analysis_presets.store.save(name,item['settings'],item['id']);self.analysis_presets.refresh_presets()
        except (ValueError,OSError) as exc:self.status(str(exc))

    def copy_text(self,value):
        copied=bool(value)
        if copied:QApplication.clipboard().setText(value)
        self.copy_notice.setText('Copied to clipboard.' if copied else 'Nothing to copy yet.');self.copy_notice.adjustSize()
        self.copy_notice.move(max(12,(self.centralWidget().width()-self.copy_notice.width())//2),max(12,self.centralWidget().height()-90));self.copy_notice.show();self.copy_notice.raise_();self.copy_notice_timer.start()
        return copied

    def copy_fen(self):
        self.copy_text(self.tracker.board.fen())

    def new_game(self):
        self.stop()
        self.set_position(chess.Board())
        self.status("Position reset to the standard start. Screen users: reset the target board too.")

    def undo(self):
        if not self.practice:
            self.history_previous()
            return
        if self.tracker.board.move_stack:
            self.stop()
            self.tracker.board.pop()
            self.invalidate()
            self.refresh_board()
            self.status("Practice move undone.")

    def practice_click(self, square):
        if not self.practice:
            return
        board = self.tracker.board
        source = self.board_view.selected
        if source is not None:
            move = chess.Move(source, square)
            piece = board.piece_at(source)
            if piece and piece.piece_type == chess.PAWN and chess.square_rank(square) in (0, 7):
                move.promotion = chess.QUEEN
            if move in board.legal_moves:
                board.push(move)
                self.board_view.selected = None
                self.invalidate()
                self.refresh_board()
                self.status("Practice move played.")
                return
        piece = board.piece_at(square)
        self.board_view.selected = square if piece and piece.color == board.turn else None
        self.board_view.update()

    def search_settings(self):
        return SearchSettings(self.seconds.value(), self.depth.value(), 'Time' if engine_config.is_tiny(self) else self.mode.currentText(),
                              self.multipv.value(),
                              self.threads.value(), self.hash_mb.value(),
                              engine_config.entry(self).identity if engine_config.is_tiny(self) else engine_config.entry(self).kind,
                              self.strength_mode.currentText() if self.engine_kind.currentIndex()==0 else "Full strength",
                              self.engine_skill.value(),self.engine_elo.value(),self.human_elo.value(),
                              self.playing_style.currentText() if self.playing_style.isEnabled() else 'Balanced',engine_config.entry(self).identity,self.predict_continuations.isChecked(),self.prediction_plies.value(),self.prediction_seconds.value())

    def suggest(self, checked=False, from_poll=False):
        try:
            if self._reviewing or self.clicker.active or self.pending_until:
                return
            if self.source.currentIndex() == 1:
                if not self._screen_confirmed or self._last_read is None:
                    self.start_live(compact=True)
                    return
            elif not self.practice:
                self.sync(stable=from_poll)
            board = self.tracker.board.copy()
            if board.is_game_over():
                self.stop()
                self.status(f"Game over: {board.result()}")
                return
            if hasattr(self,'evaluations'):self.evaluations.request(board)
            path = self.analysis_command()
            if self.job and from_poll:
                return
            self.invalidate(preserve_eval=True)
            self.last_requested_fen = board.fen()
            self.job = job = EngineJob()
            job.session = self.engine_session
            generation = self.generation
            job.on_update=lambda result:self.engine_signals.progress.emit(generation,result)
            settings = self.search_settings()
            self.status(f"Thinking for {'White' if board.turn else 'Black'} · {self.limit_label.text()}. STOP cancels.")
            def work():
                try:
                    result, error = job.run(path, board, settings), ""
                except Exception as exc:
                    result, error = None, str(exc)
                if not self.closing:
                    try:
                        self.engine_signals.complete.emit(generation, result, error)
                    except RuntimeError:
                        pass
            threading.Thread(target=work, daemon=True, name="BoardLens-engine").start()
        except Exception as exc:
            self.status(str(exc))

    def engine_progress(self, generation, result):
        if generation!=self.generation or self.closing or self._reviewing or not self.early_suggestions.isChecked():return
        if result['fen']!=self.tracker.board.fen():return
        if self.source.currentIndex()==1 and not self._screen_confirmed:return
        self.result=dict(result,provisional=True)
        self.render_result(self.result)
        label="Move locked" if self.stick_to_move.isChecked() else "Early suggestion"
        self.status(f"{label} · depth {result['lines'][0]['depth']} · still thinking at your chosen limit")

    def engine_finished(self, generation, result, error):
        if generation != self.generation or self.closing:
            return
        self.job = None
        if error:
            self.stop()
            self.status(f"Engine error: {error}")
            return
        if not result or result["fen"] != self.tracker.board.fen():
            return
        if self.source.currentIndex() == 1 and (not self._screen_confirmed or not self._last_read
                or self._last_read.symbols != ordered_symbols(self.tracker.board, self.white_bottom)):
            self.last_requested_fen = None
            return
        self.result = dict(result,provisional=False)
        self.remember_position()
        self.render_result(self.result)
        elapsed=f"{result['elapsed']:.2f}s · " if 'elapsed' in result else ''
        locked="Move locked · " if self.stick_to_move.isChecked() else ""
        detail=f'human rating {self.human_elo.value()}' if result.get('evaluation_kind')=='human-game outcome estimate' else f'depth {result["lines"][0]["depth"]}'
        self.status(f"{locked}{result['engine']} · {elapsed}{detail} · {result['lines'][0]['advantage']} · ready")
    def render_result(self, result):
        if result.get('fen')!=self.tracker.board.fen():
            self.update_visuals()
            return
        lead = result["lines"][0]
        evaluation=self.evaluations.score(self.tracker.board,result)
        self.eval_bar.cp, self.eval_bar.mate = evaluation['cp'],evaluation['mate']
        self.eval_bar.update()
        self.eval_label.setText(f"{evaluation['provider']} · {evaluation['score']} · {evaluation['advantage']}")
        move_result=self.displayed_result(result)
        lead=move_result['lines'][0]
        locked=self.stick_to_move.isChecked()
        side = "White" if self.tracker.board.turn else "Black"
        other = "Black" if self.tracker.board.turn else "White"
        show_current,show_other = self.allowed_colors()
        if locked:show_other=False
        if show_current:
            self.simple_label.setText((lead.get('simple') or simple_move(self.tracker.board,chess.Move.from_uci(lead['move'])))+(' · locked' if locked else ''))
        else:
            self.simple_label.setText(f"Waiting for your turn · you are {'White' if self.white_bottom else 'Black'}" if self.only_my_color.isChecked() else "Suggestions for this side are hidden")
        self.reply_label.setText((lead.get('reply_simple','')+" · after #1") if show_other and self.show_reply.isChecked() and lead.get("reply_simple") else "")
        self.reply_label.setVisible(bool(self.reply_label.text()))
        sections = [f"<h2>{side} to move · {evaluation['score']}</h2><p>Evaluation: {html.escape(evaluation['provider'])} · Moves: {html.escape(result['engine'])}</p>",
                    ""]
        if result.get('evaluation_kind')=='human-game outcome estimate':
            sections[1]="<p><b>Maia human predictions.</b> Ranked by predicted human choice. Scores and W/D/L are human-game outcome estimates, not Stockfish search evaluations. Depth is not used.</p>"
        elif result.get('recommendation_type')=='strength-limited choice':
            sections.insert(1,"<p><b>Strength-limited recommendation.</b> #1 is the engine's chosen move at your selected strength. Alternatives retain engine scores; #1 may have a lower score.</p>")
        for index, line in enumerate(move_result["lines"][:1 if locked else self.multipv.value()], 1):
            if not self.visible_rank(index):
                continue
            if show_current:
                detail='human prediction' if result.get('evaluation_kind')=='human-game outcome estimate' else 'one move · no evaluation' if result.get('evaluation_kind')=='not supplied by this bot' else f'depth {line["depth"]}'
                sections.append(f"<h3>#{index} {side}: {html.escape(line['san'])} &nbsp; {line['score']} <small>· {detail}</small></h3><p>{html.escape(line['description'])}<br>{html.escape(line['insights'])}</p>")
            if show_other and self.show_reply.isChecked() and line["reply"]:
                sections.append(f"<p><b>Opponent’s predicted best reply — {other}, after {html.escape(line['san'])}:</b><br>{html.escape(line['reply'])}</p>")
            if self.predict_continuations.isChecked() and show_current and not locked and line.get('future_simple'):
                sections.append('<p><b>Your predicted response after that reply:</b> '+html.escape(line['future_simple'])+'</p>')
            if not locked and not self.only_my_color.isChecked() and (show_current or (show_other and self.show_reply.isChecked())):
                sections.append(f"<p style='color:#9bdfb2'>{html.escape(line['pv'])}</p>")
        if self.only_my_color.isChecked() and not show_current:
            sections=["<h3>Waiting for your turn</h3><p>Only my color is on. Opponent suggestions are hidden.</p>"]
        
        if 'elapsed' in result and not result.get('provisional') and not result.get('waiting_for_analysis'):
            detail='one human-model prediction' if result.get('evaluation_kind')=='human-game outcome estimate' else f'depth {result["lines"][0]["depth"]}'
            sections.append(f"<p><small>Completed in {result['elapsed']:.2f} seconds · {detail}</small></p>")
        if locked and show_current:
            sections.insert(0,"<p><b>Move locked</b> · Showing the first suggestion for this position. The evaluation follows the engine's latest analysis.</p>")
        if result.get("waiting_for_analysis"):
            sections.insert(0,"<p>Refreshing analysis · keeping the locked move.</p>")
        elif result.get("provisional"):
            sections.insert(0,"<p><b>Early suggestion · still thinking</b></p>")
        self.set_analysis_html("".join(sections),result["fen"])
        self.update_visuals()

    def displayed_result(self, result):
        if not self.stick_to_move.isChecked():return self.hint_filter.select(result,self.steady_arrows.isChecked())
        fen=self.tracker.board.fen()
        if self._pinned_result and self._pinned_result['fen']!=fen:
            self._pinned_result=None
        if self._pinned_result is None and result and result.get('fen')==fen:
            shown=self.hint_filter.displayed
            self._pinned_result=deepcopy(shown if shown and shown['fen']==fen else result)
        if self._pinned_result and result and result.get('fen')==fen:
            from .hints import merge_continuation
            merge_continuation(self._pinned_result,result)
        return self._pinned_result

    def steady_changed(self,enabled):
        self.hint_filter.reset()
        for state in self.multi.states:state.hint_filter.reset()
        self.visual_settings_changed()

    def stick_move_changed(self, enabled):
        if hasattr(self,"multi"):
            if not enabled:
                for state in self.multi.states:state.pinned=None
            self.multi.repaint()
        if not enabled:self._pinned_result=None
        if self.result is not None:
            self.render_result(self.result)
        elif enabled and self._pinned_result:
            self.render_result(dict(self._pinned_result,waiting_for_analysis=True))
        else:
            self.simple_label.setText("Best move — waiting for analysis")
            self.reply_label.clear()
            self.update_visuals()

    def visible_rank(self,index):
        return self.rank_best.isChecked() if index==1 else self.rank_second.isChecked() if index==2 else self.rank_others.isChecked()

    def visual_settings_changed(self,*_):
        if self._applying_preset:return
        self.mark_custom_preset()
        if hasattr(self,"multi"):self.multi.repaint()
        self.quick_arrows.setChecked(self.overlay_enabled.isChecked())
        self.show_white.setEnabled(not self.only_my_color.isChecked())
        self.show_black.setEnabled(not self.only_my_color.isChecked())
        self.show_reply.setEnabled(not self.only_my_color.isChecked())
        if self.result is not None:
            self.render_result(self.result)
        elif self.stick_to_move.isChecked() and self._pinned_result:
            self.render_result(dict(self._pinned_result,waiting_for_analysis=True))
        else:
            self.update_visuals()

    def update_visuals(self):
        if not hasattr(self,"board_view"):
            return
        arrows=[]
        move_result=self.displayed_result(self.result)
        if move_result and move_result.get("fen")==self.tracker.board.fen():
            locked=self.stick_to_move.isChecked()
            color_allowed,other_allowed=self.allowed_colors()
            if locked:other_allowed=False
            side="W" if self.tracker.board.turn else "B"
            colors=["#ffc65c","#61b9ff","#c49bff","#ff90b2","#83e4bb"]
            for index,line in enumerate(move_result["lines"][:1 if locked else min(self.multipv.value(),self.arrow_count.value())],1):
                if color_allowed and self.visible_rank(index):
                    arrows.append({"move":chess.Move.from_uci(line["move"]),"color":colors[(index-1)%len(colors)],"label":f"{side}{index}"})
            lead=move_result["lines"][0]
            if other_allowed and self.show_reply.isChecked() and self.rank_best.isChecked() and lead.get("reply_move"):
                arrows.append({"move":chess.Move.from_uci(lead["reply_move"]),"color":"#53e2e4","label":"B↳" if side=="W" else "W↳","reply":True,"dashed":self.dashed_reply.isChecked()})
        self.board_view.arrows=arrows
        marks,messages=self.threat_marks(self.tracker.board,self.white_bottom)
        self.board_view.marks=marks
        self.board_view.setToolTip('\n'.join(messages) if messages else 'Recognized chess position')
        if not self.arrow_labels.isChecked():
            for arrow in arrows:
                arrow.pop("label",None)
        self.board_view.best_move=None
        self.board_view.update()
        if ((arrows or marks) and self.overlay_enabled.isChecked() and self.target_lock.overlay_visible() and self.source.currentIndex()==1
                and self._monitoring and (self._screen_confirmed or time.monotonic()<self._overlay_grace_until) and not self.clicker.active and not self.pending_until
                and self.region and not self.closing and not self._reviewing):
            try:
                if self._last_read and getattr(self._last_read,'desktop_rect',None):
                    geometry=QRect(*[round(v) for v in self._last_read.desktop_rect]);target=next((s for s in QGuiApplication.screens() if s.geometry().contains(geometry.center())),self.window_screen())
                    projected=[dict(a,points=self._last_read.points) for a in arrows]
                    self.overlay.set_arrows(geometry,self.white_bottom,projected,target,[dict(m,points=self._last_read.points) for m in marks]);self.multi.update_primary();return
                target=self.screen()
                self.overlay.set_arrows(self.region.desktop_rect(target.geometry()),self.white_bottom,arrows,target,marks)
            except ValueError:
                self.overlay.hide()
        else:
            self.overlay.hide()

        self.multi.update_primary()

    def toggle_live(self, enabled):
        if not enabled:
            self.stop()
            return
        if self.source.currentIndex() == 2:
            self.live_button.setChecked(False)
            self.status("Screenshots are static. Use Suggest best move once.")
            return
        if self.source.currentIndex() == 1:
            if self._reviewing:self.resume_live()
            else:self.start_live()
            return
        self.last_requested_fen = None
        self.status("Auto suggest enabled. Screen boards must stay fully visible.")

    def play_best(self, checked=False, _verified_symbols=None):
        if not self.practice:
            self.status("Live mode provides suggestions. Play moves yourself on the target board.")
            return
        if QApplication.activeModalWidget():return
        try:
            board=self.tracker.board
            selected=self.result
            move=can_send_move(board,selected,ordered_symbols(board,self.white_bottom),self.white_bottom,
                               board.turn)
            board.push(move)
            self.invalidate()
            self.refresh_board()
            self.status("Engine move played on the practice board.")
        except Exception as exc:
            self.status(str(exc))

    def input_failed(self, error):
        self.stop()
        self.status(f"Could not click the board: {error}")

    def poll(self):
        if self.browser_reader or self.native_reader_button.isChecked():
            route=foreground_kind()
            if route!='self':self._last_external_route=route
        if self._overlay_grace_until and not self._screen_confirmed and time.monotonic()>=self._overlay_grace_until:
            self._overlay_grace_until=0.
            self.overlay.hide()
        if self.closing or not self.live_button.isChecked() or self.clicker.active or QApplication.activeModalWidget():
            return
        if self.pending_until and time.monotonic() > self.pending_until:
            self.stop()
            self.invalidate()
            self.status("The board did not confirm the move; check the target and sync it.")
            return
        if self.source.currentIndex() == 1:
            self.request_scan()
            return
        try:
            if not self.practice:
                self.sync(stable=True)
            if self.pending_until:
                return
            board = self.tracker.board
            if board.is_game_over():
                self.stop()
                self.status(f"Game over: {board.result()}")
            elif self.job is None and self.last_requested_fen != board.fen():
                self.suggest(from_poll=True)
        except Exception as exc:
            self.invalidate()
            self.status(str(exc))

    def stop(self, checked=False):
        if getattr(getattr(self, 'permissions', None), 'blocked', False):
            self.permissions.resume = False
        self._monitoring = False
        if hasattr(self,'evaluations'):self.evaluations.invalidate()
        if hasattr(self,"comparison"):self.comparison.cancel()
        if hasattr(self,"multi"):self.multi.stop()
        self._scan_again = False
        self._overlay_grace_until=0.
        self._pending_screen_move=None
        self.overlay.hide()
        self.update_history_controls()
        self._live_token += 1
        self._scan_busy = False
        self._screen_confirmed = False
        self.live_worker.cancel()
        self.generation += 1
        self.live_button.setChecked(False)
        self.clicker.cancel()
        if self.job:
            self.job.cancel()
            self.job = None
            self.last_requested_fen = None
        self.pending_until = 0
        self.status("STOPPED · screen monitoring and engine search are off")

    def recommendation_preset(self,count):
        self.multipv.setValue(count);self.arrow_count.setValue(count)
        self.rank_best.setChecked(True);self.rank_second.setChecked(count>=2);self.rank_others.setChecked(count>=3)
        self.visual_settings_changed()

    def open_engine_library(self,checked=False):
        if not hasattr(self,'library_dialog'):
            from .library_dialog import EngineLibraryDialog
            self.library_dialog=EngineLibraryDialog(self)
        self.library_dialog.refresh();self.library_dialog.show();self.library_dialog.raise_()

    def analysis_command(self):
        return engine_config.command(self)

    def update_engine_summary(self):
        if hasattr(self,'engine_summary'):self.engine_summary.setText(engine_config.summary(self))

    def engine_configuration_changed(self,*_):
        if not hasattr(self,'engine_summary'):return
        human=engine_config.is_human(self);tiny=engine_config.is_tiny(self);selected=engine_config.entry(self);stockfish=selected.kind=='stockfish'
        if stockfish and self.playing_style.currentText()=='Maximum strength':
            if self.sender() is self.strength_mode and self.strength_mode.currentText()!='Full strength':self.playing_style.setCurrentText('Balanced')
            else:self.strength_mode.setCurrentText('Full strength')
        self.playing_style.setEnabled(not tiny and not human and selected.kind!='flounder' and (not stockfish or self.strength_mode.currentText()=='Full strength'))
        self.multipv.setMaximum(1 if tiny else 10)
        for count,button in self.preset_buttons:button.setEnabled(not tiny or count==1)
        self.engine_capabilities.setText((f'{selected.difficulty} · ref. {selected.rating} Elo\nOne move · no evaluation' if tiny else 'Stockfish-based · approximate target rating.' if selected.kind=='flounder' else 'Human predictions · approximate target rating.' if human else ''))
        self.strength_mode.setEnabled(stockfish)
        self.engine_strength_form.setRowVisible(self.strength_mode,stockfish)
        self.engine_strength_form.setRowVisible(self.engine_skill,stockfish and self.strength_mode.currentText()=='Skill level')
        self.engine_strength_form.setRowVisible(self.engine_elo,stockfish and self.strength_mode.currentText()=='Elo rating')
        self.engine_strength_form.setRowVisible(self.human_elo,human or selected.kind=='flounder')
        for field in (self.mode,self.seconds,self.depth,self.threads,self.hash_mb):self.engine_limit_form.setRowVisible(field,not human and (not tiny or field==self.seconds))
        
        self.engine_skill.setEnabled(stockfish and self.strength_mode.currentText()=='Skill level')
        self.engine_elo.setEnabled(stockfish and self.strength_mode.currentText()=='Elo rating')
        self.human_elo.setEnabled(human or selected.kind=='flounder')
        self.early_suggestions.setEnabled(True)
        self.early_suggestions.setToolTip("Shows each provider’s first available result, then fills in predicted replies. Non-streaming models must finish their first inference.")
        self.engine_search_note.setVisible(not human)
        self.engine_refresh_note.setText("Screen: 75 ms · one model prediction / position." if human else "Screen refresh: 75 ms target.")
        self.mode.setEnabled(not human and not tiny);self.hash_mb.setEnabled(not human and not tiny);self.threads.setEnabled(not human and not tiny)
        self.mode_changed()
        self.engine_settings_changed()
        if self._ready and self._monitoring:self.last_requested_fen=None

    def browse_custom_engine(self):
        path,_=QFileDialog.getOpenFileName(self,"Choose custom UCI executable")
        if path:self.custom_engine.setText(path);self.engine_configuration_changed()

    def open_engine_comparison(self,checked=False,show=True):
        if not hasattr(self,'comparison'):
            from .comparison import EngineComparison
            self.comparison=EngineComparison(self)
        if show:self.comparison.show();self.comparison.raise_()
        self.comparison.start()

    def browse_engine(self):
        self.stop()
        path, _ = QFileDialog.getOpenFileName(self, "Choose UCI executable")
        if path:
            self.stop()
            self.engine_path.setText(path)
            self.save()

    def install_engine(self):
        if getattr(self, "installing", False):
            return
        self.stop()
        self.status("Downloading verified official Stockfish… This may take a few minutes.")
        self.suggest_button.setEnabled(False)
        # Reuse a separate signal generation; installing never enables screen input.
        def work():
            try:
                from .installer import install_stockfish
                path = install_stockfish(data_dir() / "engine")
                result, error = {"installed_engine": str(path)}, ""
            except Exception as exc:
                result, error = None, str(exc)
            if not self.closing:
                try:
                    self.install_signals.complete.emit(0, result, error)
                except RuntimeError:
                    pass
        self.installing = True
        self.install_signals = EngineSignals(self)
        self.install_signals.complete.connect(self.engine_installed)
        threading.Thread(target=work, daemon=True).start()

    def engine_installed(self, _, result, error):
        self.installing = False
        self.suggest_button.setEnabled(True)
        if error:
            self.status(f"Download failed: {error}. You can browse to a manually installed UCI engine.")
        else:
            self.invalidate()
            self.engine_path.setText(result["installed_engine"])
            self.save()
            self.status("Stockfish installed. Ready to analyze.")

    def enable_hotkeys(self, enabled):
        if not enabled:
            self.hotkeys.stop()
            return
        try:
            self.hotkeys.start({key: field.text() for key, field in self.key_fields.items()})
            self.status("Global keybinds enabled.")
        except Exception as exc:
            self.global_keys.setChecked(False)
            self.status(f"Could not enable global keybinds: {exc}")

    def apply_keys(self):
        try:
            validate_keys({key: field.text() for key, field in self.key_fields.items()})
            if self.global_keys.isChecked():
                self.enable_hotkeys(True)
            self.rebuild_local_keys()
            self.save()
        except ValueError as exc:
            self.status(str(exc))

    def dispatch_local(self, action):
        if not self.global_keys.isChecked():
            self.dispatch(action)

    def dispatch(self, action):
        if self.closing:
            return
        if action == "stop":
            self.stop()
            return
        if QApplication.activeModalWidget():
            return
        if action == "suggest":
            self.suggest()
        elif action == "move":
            self.play_best()
        elif action == "watch":
            self.live_button.setChecked(not self.live_button.isChecked())
            self.toggle_live(self.live_button.isChecked())
        elif action == "scan":
            self.select_board(True)
        elif action == "stop":
            self.stop()
        elif action == "arrows":
            self.overlay_enabled.setChecked(not self.overlay_enabled.isChecked())
        elif action == "previous":self.history_previous()
        elif action == "next":self.history_next()
        elif action == "live":self.resume_live()

    def evaluation_settings_changed(self,*_):
        if not hasattr(self,'evaluations'):return
        kind=engine_library.ENTRIES[self.eval_engine.currentData()].kind
        for field in (self.eval_seconds,self.eval_depth):field.setEnabled(kind not in ('maia3','maia2'))
        self.eval_human_elo.setEnabled(kind in ('maia3','maia2'))
        self.evaluations.invalidate();self.queue_autosave()
        if self._ready:
            self.evaluations.request(self.tracker.board)
            for state in self.multi.states:
                if state.tracker:self.evaluations.request(state.tracker.board)
            self.evaluation_changed(self.tracker.board.fen())

    def evaluation_changed(self,fen):
        if self.closing:return
        if self.tracker.board.fen()==fen:
            if self.result:self.render_result(self.result)
            else:
                score=self.evaluations.score(self.tracker.board)
                self.eval_bar.cp,self.eval_bar.mate=score['cp'],score['mate'];self.eval_bar.update();self.eval_label.setText(score['provider']+' · '+score['score'])
        for state in self.multi.states:
            if state.tracker and state.tracker.board.fen()==fen:self.multi.render(state)

    def open_updates(self):
        from .updater import UpdateDialog
        if not hasattr(self,'update_dialog'):self.update_dialog=UpdateDialog(self)
        self.update_dialog.show();self.update_dialog.raise_();self.update_dialog.start_check()

    def help(self):
        if not hasattr(self,'help_dialog'):
            from .help_dialog import HelpDialog
            self.help_dialog=HelpDialog(self)
        self.help_dialog.show();self.help_dialog.raise_();self.help_dialog.search.setFocus()

    def source_controls(self):
        if self._ready and self.source.currentIndex()!=1 and hasattr(self,'lock_target') and self.lock_target.isChecked():self.lock_target.setChecked(False)
        self.lock_target.setEnabled(self.source.currentIndex()==1)
        self.screen_setup.setVisible(self.source.currentIndex()==1)
        self.monitor.setEnabled(self.source.currentIndex()==1)
        self.open_screenshot_button.setVisible(self.source.currentIndex()==2)
        self.turn.setEnabled(self.source.currentIndex()==1);self.position_turn_form.setRowVisible(self.turn,self.source.currentIndex()==1)
        for field in (self.move_button,):field.setVisible(self.practice)
        self.fen_panel.setVisible(self.practice and not self._compact)
        self.update_history_controls()

    def my_color_changed(self,enabled):
        if enabled:
            self.orientation.setCurrentIndex(0)
        self.orientation.setEnabled(not enabled)
        self.visual_settings_changed()
        self.refresh_board()

    def allowed_colors(self):
        if self.only_my_color.isChecked():
            return self.tracker.board.turn==self.white_bottom,False
        return ((self.show_white.isChecked(),self.show_black.isChecked()) if self.tracker.board.turn else
                (self.show_black.isChecked(),self.show_white.isChecked()))

    def remember_position(self):
        if self.source.currentIndex()!=1 or self._reviewing:return
        snapshot={'board':self.tracker.board.copy(),'white_bottom':self.white_bottom,'result':self.result}
        if self._history and self._history[-1]['board'].fen()==self.tracker.board.fen():
            self._history[-1]=snapshot
        else:
            self._history.append(snapshot)
        self._history_index=len(self._history)-1
        self.update_history_controls()

    def update_history_controls(self):
        if not hasattr(self,'previous_button'):return
        self.previous_button.setEnabled(not self.practice and self._history_index>0)
        self.next_button.setEnabled(self._reviewing and self._history_index<len(self._history)-1)
        self.resume_button.setEnabled(self.source.currentIndex()==1 and (self._reviewing or not self._monitoring))

    def review_position(self,index):
        if not 0<=index<len(self._history):
            self.status("No earlier observed position yet.")
            return
        self.stop()
        self._reviewing=True
        self._history_index=index
        snapshot=self._history[index]
        self.tracker=PositionTracker(snapshot['board'])
        self._white_bottom=snapshot['white_bottom']
        self.invalidate()
        self.refresh_board()
        self.result=snapshot['result']
        if self.result:self.render_result(self.result)
        self.update_history_controls()
        self.status(f"Reviewing position {index+1}/{len(self._history)} · live paused · Resume live to continue")

    def history_previous(self):
        if self.practice:
            self.undo()
            return
        self.review_position(self._history_index-1)

    def history_next(self):
        if self._reviewing:self.review_position(self._history_index+1)

    def resume_live(self):
        if self.source.currentIndex()!=1:return
        if self._history:
            snapshot=self._history[-1]
            self.tracker=PositionTracker(snapshot['board'])
            self._white_bottom=snapshot['white_bottom']
        self._reviewing=False
        self._history_index=len(self._history)-1
        self.invalidate()
        self.refresh_board()
        self.start_live()

    def rebuild_local_keys(self):
        for shortcut in self.local_shortcuts:shortcut.setEnabled(False);shortcut.deleteLater()
        self.local_shortcuts=[]
        for action,field in self.key_fields.items():
            combo=field.text().replace('<','').replace('>','')
            combo=combo.replace('cmd','Meta').replace('ctrl','Ctrl').replace('alt','Alt').replace('shift','Shift')
            shortcut=QShortcut(QKeySequence(combo),self)
            shortcut.activated.connect(lambda action=action:self.dispatch_local(action))
            self.local_shortcuts.append(shortcut)

    def closeEvent(self, event):
        if hasattr(self, 'permissions'): self.permissions.close()
        self.stop()
        self.save()
        self.closing = True
        self.timer.stop()
        if hasattr(self,'autosave_timer'):self.autosave_timer.stop()
        self.settings_dialog.close()
        if hasattr(self,'comparison'):self.comparison.close()
        if hasattr(self,'help_dialog'):self.help_dialog.close()
        if hasattr(self,'update_dialog'):self.update_dialog.close()
        if hasattr(self,'automatic_updates'):self.automatic_updates.close()
        if hasattr(self,'library_dialog'):self.library_dialog.close()
        self.hotkeys.stop()
        self.live_worker.close()
        self.phone.close()
        self.reader_timer.stop()
        if self.browser_reader:self.browser_reader.close()
        self.multi.close()
        self.evaluations.close()
        self.engine_session.close()
        self.overlay.close()
        event.accept()
