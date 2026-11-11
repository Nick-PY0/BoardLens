"""Checkable buttons with a wrapped label and a separate On/Off state."""
from PySide6.QtCore import QRect,QSize,Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QPushButton,QSizePolicy,QStyleOptionButton,QStylePainter,QStyle

class ToggleButton(QPushButton):
    def __init__(self,text='',parent=None):
        super().__init__(text,parent);self.setCheckable(True);self.setProperty('toggle',True)
        policy=QSizePolicy(QSizePolicy.Policy.Preferred,QSizePolicy.Policy.Preferred);policy.setHeightForWidth(True);self.setSizePolicy(policy)
        self.toggled.connect(self.update)
    def minimumSizeHint(self):return QSize(80 if self.text() else 38,36)
    def sizeHint(self):return QSize(min(280,self.fontMetrics().horizontalAdvance(self.text())+58) if self.text() else 42,38)
    def hasHeightForWidth(self):return bool(self.text())
    def heightForWidth(self,width):
        if not self.text():return 36
        rect=self.fontMetrics().boundingRect(QRect(0,0,max(25,width-58),1000),Qt.TextFlag.TextWordWrap,self.text())
        return max(38,rect.height()+16)
    def paintEvent(self,event):
        painter=QStylePainter(self);option=QStyleOptionButton();self.initStyleOption(option);option.text='';painter.drawControl(QStyle.ControlElement.CE_PushButton,option)
        color='#173e26' if self.isChecked() else '#d4e1d8'
        painter.setPen(QColor(color if self.isEnabled() else '#6d8377'))
        if self.text():painter.drawText(QRect(10,4,max(1,self.width()-58),self.height()-8),Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignLeft|Qt.TextFlag.TextWordWrap,self.text())
        font=painter.font();font.setPixelSize(10);font.setBold(True);painter.setFont(font)
        rect=QRect(self.width()-39,0,34,self.height()) if self.text() else self.rect()
        painter.drawText(rect,Qt.AlignmentFlag.AlignCenter,'ON' if self.isChecked() else 'OFF')
