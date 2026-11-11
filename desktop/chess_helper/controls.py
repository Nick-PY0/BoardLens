from __future__ import annotations

import os
import sys

from PySide6.QtCore import QObject, QTimer, Signal

from .core import validate_keys


class Hotkeys(QObject):
    action = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.listener = None
        self.native = None

    def start(self, bindings):
        bindings = validate_keys(bindings)
        if sys.platform == 'darwin' and not os.environ.get('BOARDLENS_TEST_MODE'):
            from .mac_hotkeys import NativeHotkeys
            self.native = self.native or NativeHotkeys(self.action.emit)
            self.native.start(bindings)
            return
        from pynput import keyboard
        for combo in bindings.values():
            keyboard.HotKey.parse(combo)
        self.stop()
        if not getattr(keyboard.Listener, "IS_TRUSTED", True):
            raise RuntimeError("Global keys need Accessibility / Input Monitoring permission for your launcher. App buttons still work.")
        self.listener = keyboard.GlobalHotKeys({combo: (lambda action=action: self.action.emit(action))
                                               for action, combo in bindings.items()})
        self.listener.start()

    def stop(self):
        if self.native:
            self.native.stop()
        if self.listener:
            self.listener.stop()
            self.listener = None


class ClickMove(QObject):
    done = Signal()
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._finish)
        self.active = False
        self.controller = None
        self.destination = None
        self.original = None

    def start(self, source, destination):
        if self.active:
            raise ValueError("A move is already being sent.")
        from pynput.mouse import Button, Controller
        self.controller = self.controller or Controller()
        self.original = self.controller.position
        self.destination = destination
        self.active = True
        try:
            self.controller.position = source
            self.controller.click(Button.left)
            self.timer.start(180)
        except Exception:
            self.cancel()
            raise

    def _finish(self):
        if not self.active:
            return
        try:
            from pynput.mouse import Button
            self.controller.position = self.destination
            self.controller.click(Button.left)
            self.controller.position = self.original
            self.active = False
            self.done.emit()
        except Exception as exc:
            self.active = False
            self.failed.emit(str(exc))

    def cancel(self):
        self.timer.stop()
        if self.active and self.controller and self.original:
            try:
                self.controller.position = self.original
            except Exception:
                pass
        self.active = False
