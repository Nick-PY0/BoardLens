"""Shared brand artwork and a compact banner that keeps its proportions."""
from pathlib import Path
import sys

from PySide6.QtCore import QRectF
from PySide6.QtGui import QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QWidget

ASSETS = Path(__file__).parent / 'assets/ui'


def app_icon():
    mac = ASSETS / 'boardlens-icon-mac.png'
    return QIcon(str(mac if sys.platform == 'darwin' and mac.exists() else ASSETS / 'boardlens-icon-rounded.png'))


class BrandBanner(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.artwork = QPixmap(str(ASSETS / 'boardlens-banner.png'))
        self.setAccessibleName('BoardLens')
        self.set_compact(False)

    def set_compact(self, compact):
        self.setFixedSize(160 if compact else 220, 36 if compact else 44)

    def paintEvent(self, event):
        if self.artwork.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()), 7, 7)
        painter.setClipPath(clip)
        # The approved banner has white presentation margins. Fit it by
        # trimming only those margins while keeping the mark undistorted.
        width = self.artwork.width()
        height = width * self.height() / self.width()
        source = QRectF(0, (self.artwork.height() - height) / 2, width, height)
        painter.drawPixmap(QRectF(self.rect()), self.artwork, source)
