"""Searchable feature guides and offline answers to common questions."""
import html
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QTextOption
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QComboBox,QListWidget,QListWidgetItem,QSplitter,QTextBrowser,QPushButton,QWidget
from .help_index import HelpIndex

class HelpDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent);self.index=HelpIndex();self.results=[];self._updating=False
        self.setWindowTitle('BoardLens · Help');self.resize(1030,760);self.setMinimumSize(700,560)
        layout=QVBoxLayout(self);layout.setContentsMargins(18,16,18,16);layout.setSpacing(12)
        title=QLabel('Help & feature guides');title.setStyleSheet('font-size:24px;font-weight:700;color:#a5dfbd;');layout.addWidget(title)
        self.search=QLineEdit();self.search.setClearButtonEnabled(True);self.search.setPlaceholderText('Ask a question, e.g. “Why do my arrows keep changing?”');self.search.setAccessibleName('Ask about a BoardLens feature');layout.addWidget(self.search)
        self.category=QComboBox();self.category.addItems(['All sections',*dict.fromkeys(t['category'] for t in self.index.items)]);layout.addWidget(self.category)
        self.status=QLabel('Browse a section or ask a question. Answers work offline.');self.status.setWordWrap(True);layout.addWidget(self.status)
        split=QSplitter();split.setChildrenCollapsible(False);layout.addWidget(split,1)
        self.list=QListWidget();self.list.setMinimumWidth(150);self.list.setMaximumWidth(340);self.list.setWordWrap(True);self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);split.addWidget(self.list)
        self.browser=QTextBrowser();self.browser.setMinimumWidth(260);self.browser.setOpenLinks(False);self.browser.setLineWrapMode(QTextBrowser.LineWrapMode.WidgetWidth);self.browser.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere);self.browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);self.browser.anchorClicked.connect(lambda url:self.open_topic(url.toString().removeprefix('guide:')));split.addWidget(self.browser);split.setSizes([280,700])
        footer=QHBoxLayout();self.all_button=QPushButton('Browse all guides');self.all_button.clicked.connect(self.clear_filters);footer.addWidget(self.all_button);footer.addStretch();close=QPushButton('Close');close.clicked.connect(self.hide);footer.addWidget(close);layout.addLayout(footer)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(160);self.timer.timeout.connect(self.refresh)
        self.search.textChanged.connect(lambda _:self.timer.start());self.search.returnPressed.connect(self.refresh);self.category.currentIndexChanged.connect(self.refresh);self.list.currentRowChanged.connect(self.selected);self.refresh()
    def clear_filters(self):self.category.setCurrentIndex(0);self.search.clear();self.refresh()
    def refresh(self,*_):
        self.timer.stop();self._updating=True
        self.results=self.index.search(self.search.text(),self.category.currentText());self.list.clear()
        for item in self.results:
            entry=QListWidgetItem(item['title']);entry.setToolTip(item['summary']);self.list.addItem(entry)
        self._updating=False
        if self.results:
            self.status.setText(f'{len(self.results)} matching guides · choose a topic for steps and an explanation.' if self.search.text().strip() else f'{len(self.results)} guides · browse by section or ask a question.')
            self.list.setCurrentRow(0);self.selected(0)
        else:
            self.status.setText('No matching guide in this section. Try All sections or browse the guides.')
            self.browser.setHtml('<h2>Try another question</h2><p>For example: Why do arrows change? How do I connect my phone? Where are the puzzles?</p><p>Browse all guides to see every documented feature. This is an offline guide search, so it does not invent answers to unrelated questions.</p>')
    def selected(self,row):
        if not self._updating and 0<=row<len(self.results):self.render(self.results[row])
    def open_topic(self,identity):
        item=next((t for t in self.index.items if t['id']==identity),None)
        if item:self.render(item)
    def render(self,item):
        esc=html.escape;steps=''.join('<li>'+esc(step)+'</li>' for step in item['steps'])
        questions=''.join('<li>'+esc(q)+'</li>' for q in item.get('questions',[]))
        self.browser.setHtml(f"<style>h1{{font-size:25px;}}h2{{font-size:19px;}}p,li{{font-size:16px;line-height:1.5;}}li{{margin-bottom:9px;}}small{{color:#a8c0af;}}</style><small>{esc(item['category'])}</small><h1>{esc(item['title'])}</h1><p>{esc(item['summary'])}</p><h2>How to use it</h2><ol>{steps}</ol><h2>What to expect</h2><p>{esc(item['details'])}</p><h2>Questions this guide answers</h2><ul>{questions}</ul>")
        self.browser.verticalScrollBar().setValue(0)
