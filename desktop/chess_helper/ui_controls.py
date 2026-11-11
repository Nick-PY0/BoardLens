"""Controls whose content fits native font metrics and narrow panels."""
from PySide6.QtCore import QEvent,Qt,QTimer
from PySide6.QtWidgets import (QScrollArea,QLayout,QSizePolicy,QFormLayout,QLabel,QComboBox,QLineEdit)


class ResponsiveScrollArea(QScrollArea):
    """Fit the actual viewport, including its vertical scrollbar, on every layout."""
    def __init__(self,widget,parent=None):
        super().__init__(parent);self._fitting=False;self._queued=False
        self.setWidgetResizable(True);self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        widget.setMinimumWidth(0);widget.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        if widget.layout():widget.layout().setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        for form in widget.findChildren(QFormLayout):
            form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows);form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        for label in widget.findChildren(QLabel):label.setWordWrap(True);label.setMinimumWidth(0)
        for field in [*widget.findChildren(QComboBox),*widget.findChildren(QLineEdit)]:
            field.setMinimumWidth(0);field.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
            if isinstance(field,QComboBox):field.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon);field.setMinimumContentsLength(6)
        self.setWidget(widget);self.viewport().installEventFilter(self);widget.installEventFilter(self)
        self.horizontalScrollBar().valueChanged.connect(lambda value:self.horizontalScrollBar().setValue(0) if value else None)
        self.queue_fit()
    def queue_fit(self):
        if not self._queued:self._queued=True;QTimer.singleShot(0,self.fit)
    def eventFilter(self,obj,event):
        if event.type() in (QEvent.Type.Resize,QEvent.Type.Show,QEvent.Type.LayoutRequest):self.queue_fit()
        return super().eventFilter(obj,event)
    def resizeEvent(self,event):super().resizeEvent(event);self.queue_fit()
    def fit(self):
        self._queued=False
        if self._fitting or not self.widget():return
        self._fitting=True
        try:
            widget=self.widget();width=max(1,self.viewport().width())
            if widget.minimumWidth()!=width or widget.maximumWidth()!=width:widget.setFixedWidth(width)
            if widget.layout():widget.layout().activate()
            self.horizontalScrollBar().setRange(0,0)
            if widget.x()!=0:widget.move(0,widget.y())
        finally:self._fitting=False
