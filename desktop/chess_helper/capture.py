"""Qt capture stays on the UI thread. All stored rectangles use screenshot pixels."""
from dataclasses import dataclass

import cv2
import numpy as np
from PySide6.QtCore import QRect
from PySide6.QtGui import QImage, QPixmap


def pixmap_bgr(pixmap):
    if pixmap.isNull():
        raise RuntimeError("Screen capture is unavailable. On Mac, allow Screen Recording for the launcher in System Settings, then restart it.")
    image = pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    values = np.frombuffer(image.bits(), np.uint8).reshape(image.height(), image.bytesPerLine())
    rgba = values[:, :image.width() * 4].reshape(image.height(), image.width(), 4)
    return cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)


def bgr_pixmap(image):
    rgb = cv2.cvtColor(np.ascontiguousarray(image), cv2.COLOR_BGR2RGB)
    return QPixmap.fromImage(QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0],
                                  QImage.Format.Format_RGB888).copy())


def capture(screen):
    return pixmap_bgr(screen.grabWindow(0))


def screen_key(screen):
    geometry = screen.geometry()
    return f"{screen.name()}|{screen.serialNumber()}|{geometry.x()},{geometry.y()}"


@dataclass(frozen=True)
class BoardRegion:
    screen_name: str
    screen_width: int
    screen_height: int
    x: int
    y: int
    size: int

    def crop(self, image):
        if (image.shape[1], image.shape[0]) != (self.screen_width, self.screen_height):
            raise ValueError("Monitor resolution changed. Select the board again.")
        if self.size < 80 or min(self.x, self.y) < 0 or self.x + self.size > self.screen_width or self.y + self.size > self.screen_height:
            raise ValueError("The selected board is outside this screen.")
        return image[self.y:self.y + self.size, self.x:self.x + self.size].copy()

    def desktop_rect(self, geometry):
        return QRect(round(geometry.x() + self.x * geometry.width() / self.screen_width),
                     round(geometry.y() + self.y * geometry.height() / self.screen_height),
                     round(self.size * geometry.width() / self.screen_width),
                     round(self.size * geometry.height() / self.screen_height))

    def square_center(self, square, white_bottom, geometry):
        from .core import square_to_cell
        row, col = square_to_cell(square, white_bottom)
        return (round(geometry.x() + (self.x + (col + .5) * self.size / 8) * geometry.width() / self.screen_width),
                round(geometry.y() + (self.y + (row + .5) * self.size / 8) * geometry.height() / self.screen_height))


def input_point(point, screen):
    # Windows mouse injection uses physical pixels; Qt uses device-independent units.
    # The process uses Per-Monitor-V2 awareness (set before QApplication creation).
    import sys
    if sys.platform != "win32":
        return point
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    class MonitorInfo(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD),
                    ("szDevice", wintypes.WCHAR * 32)]
    matches = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HANDLE, wintypes.HDC,
                                      ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
    user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
    user32.GetMonitorInfoW.restype = wintypes.BOOL
    def visit(monitor, hdc, rect, data):
        info = MonitorInfo()
        info.cbSize = ctypes.sizeof(info)
        if user32.GetMonitorInfoW(monitor, ctypes.byref(info)) and info.szDevice == screen.name():
            matches.append(info.rcMonitor)
        return True
    callback = callback_type(visit)
    user32.EnumDisplayMonitors.argtypes = [wintypes.HDC, ctypes.POINTER(wintypes.RECT), callback_type, wintypes.LPARAM]
    user32.EnumDisplayMonitors.restype = wintypes.BOOL
    user32.EnumDisplayMonitors(None, None, callback, 0)
    if len(matches) != 1:
        raise ValueError("Cannot map this Windows display to mouse coordinates. Select the board again.")
    native = matches[0]
    g = screen.geometry()
    return (round(native.left + (point[0] - g.x()) * (native.right - native.left) / g.width()),
            round(native.top + (point[1] - g.y()) * (native.bottom - native.top) / g.height()))
