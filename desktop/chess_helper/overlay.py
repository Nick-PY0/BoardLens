"""Click-through, per-monitor arrows. Never receives board clicks or focus."""
from __future__ import annotations

import math
import os
import sys

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from .core import square_to_cell


def paint_arrows(painter, rect, white_bottom, arrows):
    cell = rect.width()/8
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    for arrow in arrows:
        move = arrow["move"]
        def point(square):
            if arrow.get('points') and square in arrow['points']:
                x,y=arrow['points'][square];return QPointF(rect.x()+x*rect.width(),rect.y()+y*rect.height())
            row,col=square_to_cell(square,white_bottom)
            return QPointF(rect.x()+(col+.5)*cell,rect.y()+(row+.5)*cell)
        start,end=point(move.from_square),point(move.to_square)
        color=QColor(arrow["color"])
        color.setAlpha(215)
        pen=QPen(color,max(3,cell*.095),Qt.PenStyle.DashLine if arrow.get("dashed",False) else Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        dx,dy=abs(end.x()-start.x())/cell,abs(end.y()-start.y())/cell
        tail=start
        if not arrow.get('points') and (round(dx),round(dy)) in ((1,2),(2,1)):
            tail=QPointF(end.x(),start.y()) if dx>dy else QPointF(start.x(),end.y())
            painter.drawLine(start,tail)
        painter.drawLine(tail,end)
        angle=math.atan2(end.y()-tail.y(),end.x()-tail.x())
        length=cell*.29
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawPolygon(QPolygonF([end,
            QPointF(end.x()-length*math.cos(angle-.52),end.y()-length*math.sin(angle-.52)),
            QPointF(end.x()-length*math.cos(angle+.52),end.y()-length*math.sin(angle+.52))]))
        if arrow.get("label"):
            center=start*.28+end*.72
            radius=max(9,cell*.16)
            painter.setBrush(QColor("#152630"))
            painter.drawEllipse(center,radius,radius)
            painter.setPen(color.lighter(130))
            painter.setFont(QFont("Arial",max(8,round(radius*.8)),QFont.Weight.Bold))
            painter.drawText(QRectF(center.x()-radius,center.y()-radius,2*radius,2*radius),
                             Qt.AlignmentFlag.AlignCenter,arrow["label"])


def paint_marks(painter, rect, white_bottom, marks):
    """Small translucent targets; projected boards use their square centers."""
    cell=rect.width()/8
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    for mark in marks:
        row,col=square_to_cell(mark['square'],white_bottom)
        center=QPointF(rect.x()+(col+.5)*cell,rect.y()+(row+.5)*cell)
        points=mark.get('points') or {}
        if mark['square'] in points:
            x,y=points[mark['square']];center=QPointF(rect.x()+x*rect.width(),rect.y()+y*rect.height())
        color=QColor(mark['color']);color.setAlpha(65 if mark['kind']=='attack' else 105)
        painter.setBrush(color);painter.setPen(Qt.PenStyle.NoPen)
        radius=cell*(.12 if mark['kind']=='attack' else .36)
        painter.drawEllipse(center,radius,radius)
        if mark['kind']!='attack':
            color.setAlpha(225);painter.setPen(QPen(color,max(2,cell*.035)));painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center,radius,radius)
    painter.restore()


class BoardOverlay(QWidget):
    is_board_overlay = True

    def __init__(self):
        flags=(Qt.WindowType.Tool|Qt.WindowType.FramelessWindowHint|
               Qt.WindowType.WindowStaysOnTopHint|Qt.WindowType.WindowTransparentForInput|
               Qt.WindowType.WindowDoesNotAcceptFocus|Qt.WindowType.NoDropShadowWindowHint)
        super().__init__(None,flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAutoFillBackground(False)
        self.setStyleSheet("background: transparent; border: none;")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.arrows=[]
        self.marks=[]
        self.white_bottom=True
        self._native_panel=None
        self._native_mac=(sys.platform=='darwin' and not os.environ.get('BOARDLENS_TEST_MODE')
                          and os.environ.get('QT_QPA_PLATFORM')!='offscreen')
        self._windows_configured=False
        self.capture_excluded=False

    def _mac_panel(self):
        if self._native_panel is None:
            from .mac_overlay import PassivePanel
            self._native_panel=PassivePanel()
        return self._native_panel

    def capture_window_id(self):
        if self._native_mac:
            return int(self._mac_panel().panel.windowNumber())
        return 0

    def isVisible(self):
        if self._native_mac:
            return bool(self._native_panel and self._native_panel.panel.isVisible())
        return super().isVisible()

    def hide(self):
        if self._native_panel:
            self._native_panel.hide()
        super().hide()

    def close(self):
        if self._native_panel:
            self._native_panel.close()
            self._native_panel=None
        return super().close()

    def _configure_windows(self):
        if sys.platform!='win32' or self._windows_configured:
            return
        import ctypes
        from ctypes import wintypes
        api=ctypes.windll.user32
        api.GetWindowLongPtrW.argtypes=[wintypes.HWND,ctypes.c_int]
        api.GetWindowLongPtrW.restype=ctypes.c_ssize_t
        api.SetWindowLongPtrW.argtypes=[wintypes.HWND,ctypes.c_int,ctypes.c_ssize_t]
        api.SetWindowLongPtrW.restype=ctypes.c_ssize_t
        hwnd=int(self.winId())
        style=api.GetWindowLongPtrW(hwnd,-20)
        # Native layered-window hit testing and no activation, across processes.
        api.SetWindowLongPtrW(hwnd,-20,style|0x20|0x80000|0x08000000|0x80)
        api.SetWindowDisplayAffinity.argtypes=[wintypes.HWND,wintypes.DWORD]
        self.capture_excluded=bool(api.SetWindowDisplayAffinity(hwnd,0x11))
        self._windows_configured=True

    def set_arrows(self, geometry, white_bottom, arrows, screen=None, marks=None):
        self.white_bottom=white_bottom
        self.arrows=arrows
        self.marks=marks or []
        if self._native_mac:
            self.setGeometry(geometry)
            if arrows or self.marks:
                from PySide6.QtGui import QGuiApplication
                primary=QGuiApplication.primaryScreen()
                self._mac_panel().update(geometry,screen.devicePixelRatio() if screen else 1,
                                         white_bottom,arrows,primary.geometry().height(),self.marks)
            else:
                self.hide()
            return
        self._configure_windows()
        if screen is not None:
            self.winId()
            if self.windowHandle().screen() != screen:
                self.windowHandle().setScreen(screen)
        self.setGeometry(geometry)
        self.update()
        if arrows or self.marks:
            if not super().isVisible():
                self.show()
        else:
            self.hide()

    def paintEvent(self,event):
        painter=QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(),Qt.GlobalColor.transparent)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        paint_marks(painter,QRectF(self.rect()),self.white_bottom,self.marks)
        paint_arrows(painter,QRectF(self.rect()),self.white_bottom,self.arrows)
