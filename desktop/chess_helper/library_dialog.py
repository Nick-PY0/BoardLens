"""Per-engine installation, with large models excluded from lightweight batches."""
import threading
from PySide6.QtCore import Qt,Signal,QTimer
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QTableWidget,QTableWidgetItem,QPushButton,QHeaderView
from .toggle import ToggleButton as QCheckBox
from . import engine_library

class EngineLibraryDialog(QDialog):
    progress=Signal(str,str)
    batch_finished=Signal()
    def __init__(self,window):
        super().__init__(window);self.window=window;self.busy=False
        self.setWindowTitle('BoardLens · Optional engine library');self.resize(1050,720)
        layout=QVBoxLayout(self)
        text=QLabel('Download only the engines you choose. Tiny bots share one .NET runtime. Large neural models are optional. Reference Elo values come from their original publications; your analysis settings can change their strength.');text.setWordWrap(True);layout.addWidget(text)
        self.table=QTableWidget(len(engine_library.ENTRIES),5);self.table.setHorizontalHeaderLabels(['Choose','Engine','Reference','Download / requirements','Status'])
        self.table.verticalHeader().hide();self.table.verticalHeader().setDefaultSectionSize(42);self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch);self.table.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0,65);self.table.setColumnWidth(2,100);self.table.setColumnWidth(4,130)
        layout.addWidget(self.table,1)
        for row,entry in enumerate(engine_library.ENTRIES):
            checked=QCheckBox();checked.setEnabled(entry.kind!='custom');self.table.setCellWidget(row,0,checked)
            for column,value in ((1,entry.label),(2,str(entry.rating) if entry.rating else '—'),(3,entry.size),(4,'')):
                item=QTableWidgetItem(value);item.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable);self.table.setItem(row,column,item)
        buttons=QHBoxLayout();self.selected_button=QPushButton('Download selected');self.light_button=QPushButton('Download all lightweight');self.all_button=QPushButton('Download all · includes large models')
        self.selected_button.clicked.connect(self.download_selected);self.light_button.clicked.connect(lambda:self.download([e.identity for e in engine_library.ENTRIES if not e.heavy and e.kind!='custom']));self.all_button.clicked.connect(lambda:self.download([e.identity for e in engine_library.ENTRIES if e.kind!='custom']))
        for button in (self.selected_button,self.light_button,self.all_button):buttons.addWidget(button)
        layout.addLayout(buttons);self.status=QLabel('Nothing downloads automatically.');self.status.setWordWrap(True);layout.addWidget(self.status)
        self.progress.connect(self.updated);self.batch_finished.connect(self.finished_downloads);self.refresh()
    def refresh(self):
        for row,entry in enumerate(engine_library.ENTRIES):self.table.item(row,4).setText('Choose path' if entry.kind=='custom' else 'Installed / ready' if engine_library.available(entry) else 'Not installed')
    def download_selected(self):
        self.download([entry.identity for row,entry in enumerate(engine_library.ENTRIES) if self.table.cellWidget(row,0).isChecked() and entry.kind!='custom'])
    def download(self,identities):
        if self.busy:return
        if not identities:self.status.setText('Check one or more engines first.');return
        self.busy=True
        for button in (self.selected_button,self.light_button,self.all_button):button.setEnabled(False)
        self.status.setText('Installing selected engines… Large runtimes can take a few minutes. Closing this window keeps the current download running.')
        def work():
            for identity in identities:
                self.progress.emit(identity,'Downloading…')
                try:
                    entry=engine_library.BY_ID[identity]
                    if not engine_library.available(entry):engine_library.install(identity)
                    self.progress.emit(identity,'Installed / ready')
                except Exception as exc:self.progress.emit(identity,'Failed: '+str(exc))
            self.batch_finished.emit()
        threading.Thread(target=work,daemon=True,name='BoardLens-library').start()
    def updated(self,identity,status):
        row=next(i for i,entry in enumerate(engine_library.ENTRIES) if entry.identity==identity)
        self.table.item(row,4).setText(status);self.status.setText(engine_library.BY_ID[identity].label+' · '+status)
    def finished_downloads(self):
        self.busy=False
        for button in (self.selected_button,self.light_button,self.all_button):button.setEnabled(True)
        self.window.engine_configuration_changed();self.status.setText('Download batch finished. Select an installed engine manually; failed rows show the reason.')
