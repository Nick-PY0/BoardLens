"""Live macOS permission checks and a recoverable screen-reading setup page."""
from dataclasses import dataclass
import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


@dataclass(frozen=True)
class Access:
    screen: bool
    accessibility: bool
    error: str = ''


def current_access():
    if sys.platform != 'darwin':
        return Access(True, True)
    try:
        import Quartz
        import ApplicationServices
        return Access(bool(Quartz.CGPreflightScreenCaptureAccess()),
                      bool(ApplicationServices.AXIsProcessTrusted()))
    except Exception as error:
        return Access(False, False, str(error))


class Permissions(QObject):
    def __init__(self, window, reader=current_access):
        super().__init__(window)
        self.window = window
        self.reader = reader
        self.access = reader()
        self.blocked = False
        self.resume = False
        self.reason = ''
        self.manual_open = False
        self.dismissed = False
        self.page = QWidget()
        layout = QVBoxLayout(self.page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.addStretch()
        self.title = QLabel('Set up screen access')
        self.title.setStyleSheet('font-size:26px;font-weight:650;color:#a5dfbd;')
        self.title.setWordWrap(True)
        layout.addWidget(self.title)
        self.detail = QLabel()
        self.detail.setWordWrap(True)
        self.detail.setStyleSheet('font-size:16px;color:#bad0c2;')
        layout.addWidget(self.detail)
        layout.addSpacing(20)
        self.screen_status = QLabel()
        self.screen_status.setWordWrap(True)
        layout.addWidget(self.screen_status)
        actions = QHBoxLayout()
        self.allow = QPushButton('Allow screen access')
        self.allow.setObjectName('primary')
        self.allow.clicked.connect(self.request_screen)
        actions.addWidget(self.allow)
        self.settings = QPushButton('Open macOS Settings')
        self.settings.clicked.connect(lambda: self.open_settings('Privacy_ScreenCapture'))
        actions.addWidget(self.settings)
        layout.addLayout(actions)
        layout.addSpacing(18)
        self.ax_status = QLabel()
        self.ax_status.setWordWrap(True)
        layout.addWidget(self.ax_status)
        self.ax_button = QPushButton('Accessibility settings')
        self.ax_button.clicked.connect(self.request_accessibility)
        layout.addWidget(self.ax_button)
        layout.addSpacing(18)
        bottom = QHBoxLayout()
        self.check = QPushButton('Check again')
        self.check.clicked.connect(self.refresh)
        bottom.addWidget(self.check)
        self.restart = QPushButton('Restart BoardLens')
        self.restart.clicked.connect(self.restart_app)
        bottom.addWidget(self.restart)
        self.back = QPushButton('Use app without scanning')
        self.back.clicked.connect(self.leave)
        bottom.addWidget(self.back)
        layout.addLayout(bottom)
        self.practice = QPushButton('Use Practice board')
        self.practice.clicked.connect(lambda: window.source.setCurrentIndex(0))
        layout.addWidget(self.practice)
        layout.addStretch()
        window.workspace_stack.addWidget(self.page)
        window.source.currentIndexChanged.connect(self.refresh)
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        self.render()

    @staticmethod
    def open_settings(section):
        QDesktopServices.openUrl(QUrl('x-apple.systempreferences:com.apple.preference.security?' + section))

    def request_screen(self):
        # The OS owns the actual approval. This button never changes TCC data.
        try:
            import Quartz
            Quartz.CGRequestScreenCaptureAccess()
        except Exception as error:
            self.window.status('Could not request screen access: ' + str(error))
        self.refresh()

    def request_accessibility(self):
        # Only an explicit button press can ask macOS. Startup and polling are read-only.
        from .native_chess import request_access
        if not request_access():self.open_settings('Privacy_Accessibility')
        self.refresh()

    def direct_available(self):
        w = self.window
        if w._scan_route == 'browser' and w.browser_reader:
            return bool(w.browser_reader.reads())
        return bool(w._scan_route == 'native' and w.native_reader_button.isChecked()
                    and self.access.accessibility)

    def missing(self):
        w = self.window
        if w.practice or self.direct_available():
            return ''
        if w._scan_route == 'native' and w.native_reader_button.isChecked() and not self.access.accessibility:
            return 'Accessibility'
        return '' if self.access.screen else 'Screen Recording'

    def ensure_capture(self, resume=True):
        self.access = self.reader()
        if not self.missing():
            if self.blocked:
                self.refresh()
            return True
        self.dismissed = False
        self.resume = self.resume or resume
        self.pause()
        return False

    def pause(self):
        w = self.window
        self.reason = self.missing()
        if not self.blocked or w._monitoring or w._scan_busy or w.job is not None:
            wanted = self.resume or w._monitoring
            w.stop()
            self.resume = wanted
            # A stopped scan cannot publish an old board or old arrows afterward.
            w.multi.reset()
            w.region = None
            w._last_read = None
        self.blocked = True
        self.render()
        if not self.dismissed:
            w.workspace_stack.setCurrentWidget(self.page)
        w.status_label.setText(self.reason + ' permission required · screen reading is paused')

    def refresh(self, *_):
        if self.window.closing:
            return
        self.access = self.reader()
        self.window._native_access_ok=self.access.accessibility
        if not self.window.practice:
            self.window.update_foreground()
        self.render()
        if self.missing():
            self.pause()
            return
        was_blocked = self.blocked
        self.blocked = False
        if self.window.workspace_stack.currentWidget() is self.page and (was_blocked or not self.manual_open or self.window.practice):
            self.manual_open = False
            self.window.workspace_stack.setCurrentIndex(0)
        if was_blocked and self.resume and not self.window.practice:
            self.resume = False
            self.window.scan_now()
        elif self.window.practice:
            self.resume = False

    def render(self):
        required = self.missing()
        self.title.setText((required + ' access needed') if required else 'Permissions')
        self.detail.setText(
            'BoardLens cannot read the screen until macOS allows it. Enable BoardLens in '
            'Privacy & Security, then check again. If macOS asks for a restart, use Restart BoardLens.'
            if required == 'Screen Recording' else
            'Allow Accessibility for the local 3D reader. Ordinary 2D screen scanning uses Screen Recording.'
            if required else 'Screen access is ready. These permissions are checked while BoardLens runs.')
        if self.access.error:
            self.detail.setText('Could not check permissions: ' + self.access.error)
        self.screen_status.setText('Screen Recording: ' + ('Allowed' if self.access.screen else 'Required for screen scanning'))
        self.ax_status.setText('Accessibility: ' + ('Allowed' if self.access.accessibility else
                              'Not enabled for this BoardLens copy · only needed for the local 3D reader'))
        if not self.access.accessibility and os.environ.get('BOARDLENS_NATIVE_LAUNCHER'):
            self.ax_status.setText(self.ax_status.text()+'\nUse Applications → BoardLens.app. If it is already on, remove the old BoardLens entry with −, add this app with +, and enable it again. Then restart BoardLens. Updates from an older temporary signature may need this once.')
        self.allow.setVisible(not self.access.screen)
        self.ax_button.setVisible(not self.access.accessibility)
        self.back.setEnabled(True)

    def leave(self):
        self.manual_open = False
        self.dismissed = True
        self.window.workspace_stack.setCurrentIndex(0)

    def open(self):
        self.manual_open = True
        self.dismissed = False
        self.access = self.reader()
        self.render()
        self.window.workspace_stack.setCurrentWidget(self.page)

    def restart_app(self):
        from .restart_app import restart_command
        command = restart_command(os.getpid(), Path(__file__).resolve().parent.parent)
        subprocess.Popen(command, start_new_session=True)
        self.window.close()

    def close(self):
        self.timer.stop()
