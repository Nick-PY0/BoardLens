"""A passive AppKit panel, independent of Qt's application activation logic."""
from __future__ import annotations

import AppKit
from Foundation import NSData
from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtCore import Qt


class BoardLensPassivePanel(AppKit.NSPanel):
    def canBecomeKeyWindow(self):
        return False

    def canBecomeMainWindow(self):
        return False


class PassivePanel:
    def __init__(self):
        self.panel = BoardLensPassivePanel.alloc().initWithContentRect_styleMask_backing_defer_(
            AppKit.NSMakeRect(0, 0, 1, 1),
            AppKit.NSWindowStyleMaskBorderless | AppKit.NSWindowStyleMaskNonactivatingPanel,
            AppKit.NSBackingStoreBuffered, False)
        self.panel.setReleasedWhenClosed_(False)
        self.panel.setOpaque_(False)
        self.panel.setBackgroundColor_(AppKit.NSColor.clearColor())
        self.panel.setHasShadow_(False)
        self.panel.setIgnoresMouseEvents_(True)
        self.panel.setAcceptsMouseMovedEvents_(False)
        self.panel.setBecomesKeyOnlyIfNeeded_(True)
        self.panel.setHidesOnDeactivate_(False)
        self.panel.setFloatingPanel_(True)
        self.panel.setLevel_(AppKit.NSFloatingWindowLevel)
        self.panel.setCollectionBehavior_(AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces |
            AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary |
            AppKit.NSWindowCollectionBehaviorStationary |
            AppKit.NSWindowCollectionBehaviorIgnoresCycle)
        self.view = AppKit.NSImageView.alloc().initWithFrame_(AppKit.NSMakeRect(0, 0, 1, 1))
        self.view.setImageScaling_(AppKit.NSImageScaleAxesIndependently)
        self.panel.setContentView_(self.view)
        self.signature = None

    def update(self, geometry, scale, white_bottom, arrows, primary_height, marks=None):
        marks=marks or []
        signature = (geometry.getRect(), scale, white_bottom,
                     tuple((a['move'].uci(), a['color'], a.get('label'), a.get('reply'),a.get('dashed'),tuple(sorted((a.get('points') or {}).items()))) for a in arrows),
                     tuple((m['square'],m['color'],m['kind'],tuple(sorted((m.get('points') or {}).items()))) for m in marks))
        if signature != self.signature:
            from .overlay import paint_arrows,paint_marks
            width, height = geometry.width(), geometry.height()
            image = QImage(round(width*scale), round(height*scale), QImage.Format.Format_ARGB32_Premultiplied)
            image.setDevicePixelRatio(scale)
            image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(image)
            paint_marks(painter,QRectF(0,0,width,height),white_bottom,marks)
            paint_arrows(painter, QRectF(0, 0, width, height), white_bottom, arrows)
            painter.end()
            data = QByteArray()
            buffer = QBuffer(data)
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            image.save(buffer, 'PNG')
            raw = bytes(data)
            native_image = AppKit.NSImage.alloc().initWithData_(NSData.dataWithBytes_length_(raw, len(raw)))
            native_image.setSize_(AppKit.NSMakeSize(width, height))
            self.panel.setFrame_display_(AppKit.NSMakeRect(geometry.x(), primary_height-geometry.y()-height,
                                                          width, height), False)
            self.view.setFrame_(AppKit.NSMakeRect(0, 0, width, height))
            self.view.setImage_(native_image)
            self.signature = signature
        if not self.panel.isVisible():
            # Orders only this non-activating panel. It never activates the app
            # or changes the key/main window behind it.
            self.panel.orderFrontRegardless()

    def hide(self):
        if self.panel.isVisible():
            self.panel.orderOut_(None)

    def close(self):
        self.panel.orderOut_(None)
        self.panel.close()

    def diagnostics(self):
        return {'ignores_mouse': bool(self.panel.ignoresMouseEvents()),
                'can_become_key': bool(self.panel.canBecomeKeyWindow()),
                'can_become_main': bool(self.panel.canBecomeMainWindow()),
                'nonactivating': bool(self.panel.styleMask() & AppKit.NSWindowStyleMaskNonactivatingPanel)}
