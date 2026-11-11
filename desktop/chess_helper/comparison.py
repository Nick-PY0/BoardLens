"""Independent, explicitly selected engine comparisons for one observed board."""
from __future__ import annotations
import html,json,threading
from dataclasses import asdict
from PySide6.QtCore import QTimer,Signal
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPushButton,QTextBrowser,QWidget
from .toggle import ToggleButton as QCheckBox
from .engine import EngineJob,EngineSession
from . import engine_config

class EngineComparison(QDialog):
    completed=Signal(int,int,object,str)
    def __init__(self,window):
        super().__init__(window);self.window=window;self.generation=0;self.jobs={};self.sessions=[EngineSession() for _ in range(3)];self.results=[];self.signature=None;self.following=False
        self.setWindowTitle('BoardLens · Engine comparison');self.resize(1250,780);self.setMinimumSize(760,550)
        layout=QVBoxLayout(self);header=QHBoxLayout();header.addWidget(QLabel('Compare the same position'))
        self.board_choice=QComboBox();header.addWidget(self.board_choice)
        self.auto_refresh=QCheckBox('Follow board changes');self.auto_refresh.setChecked(True);header.addWidget(self.auto_refresh)
        run=QPushButton('Compare now');run.clicked.connect(self.start);header.addWidget(run)
        cancel=QPushButton('Stop');cancel.clicked.connect(self.cancel);header.addWidget(cancel);layout.addLayout(header)
        self.position=QLabel();self.position.setWordWrap(True);layout.addWidget(self.position)
        note=QLabel('Engines A / B / C are chosen manually in the Engine tab. Each uses your selected search limits. Maia predicts human moves; its outcome estimates use a different scale.');note.setWordWrap(True);layout.addWidget(note)
        row=QHBoxLayout();self.columns=[];self.titles=[]
        for index in range(3):
            box=QWidget();column=QVBoxLayout(box);title=QLabel();title.setWordWrap(True);title.setStyleSheet('font-size:18px;font-weight:600;color:#a5dfbd;');column.addWidget(title)
            view=QTextBrowser();view.setStyleSheet('font-size:16px;');column.addWidget(view,1);row.addWidget(box,1);self.columns.append((box,view));self.titles.append(title)
        layout.addLayout(row,1);self.completed.connect(self.analysis_finished)
        self.timer=QTimer(self);self.timer.timeout.connect(self.poll);self.timer.start(300)
        self.boards()

    def boards(self):
        w=self.window;items=[]
        valid=w.practice or w._reviewing or (w.source.currentIndex()==2 and w.snapshot is not None) or (w._last_read is not None and w._lost_frames<3)
        if valid:items.append(('primary','Board 1',w.tracker.board))
        items.extend((str(s.identity),f'Board {i}',s.tracker.board) for i,s in enumerate(w.multi.states,2) if s.tracker and s.misses<3)
        ids=[self.board_choice.itemData(i) for i in range(self.board_choice.count())]
        if ids!=[i[0] for i in items]:
            old=self.board_choice.currentData();self.board_choice.clear()
            for identity,title,board in items:self.board_choice.addItem(title,identity)
            self.board_choice.setCurrentIndex(max(0,self.board_choice.findData(old)))
        return items

    def current(self):
        return next((board.copy() for identity,title,board in self.boards() if identity==self.board_choice.currentData()),None)

    def key(self,board):
        w=self.window
        return (board.fen(),self.board_choice.currentData(),w.compare_a.currentIndex(),w.compare_b.currentIndex(),w.compare_c.currentIndex(),json.dumps(asdict(w.search_settings()),sort_keys=True),w.engine_path.text(),w.custom_engine.text())

    def poll(self):
        board=self.current()
        if not board:
            if self.signature:self.cancel();self.signature=None;self.results=[]
            for box,view in self.columns:view.clear()
            self.position.setText('No confirmed board. Use Scan now in the main window.');return
        if self.signature and self.key(board)!=self.signature:
            if self.isVisible() and self.auto_refresh.isChecked() and self.following:self.start()
            else:
                self.cancel();self.signature=None;self.results=[]
                for box,view in self.columns:view.setText('Position or settings changed. Press Compare now.')

    def start(self,checked=False):
        self.cancel();board=self.current()
        if board is None:self.position.setText('No confirmed board to compare.');return
        if board.is_game_over():self.position.setText('Game over · '+board.result());return
        self.following=True;self.signature=self.key(board);generation=self.generation;self.results=[]
        self.position.setText(('White' if board.turn else 'Black')+' to move · '+board.fen())
        w=self.window;selected=[w.compare_a.currentIndex(),w.compare_b.currentIndex()]
        if w.compare_c.currentIndex()>0:selected.append(w.compare_c.currentIndex()-1)
        for index,(box,view) in enumerate(self.columns):box.setVisible(index<len(selected));view.clear()
        for index,profile in enumerate(selected):
            title=engine_config.COMPARE_NAMES[profile];self.titles[index].setText(title)
            self.results.append({'profile':title,'status':'Thinking…','result':None,'error':''})
            try:path,settings=engine_config.profile(w,profile)
            except ValueError as exc:self.analysis_finished(index,generation,None,str(exc));continue
            job=EngineJob();job.session=self.sessions[index];self.jobs[index]=job;self.columns[index][1].setText('Thinking…')
            def work(index=index,job=job,path=path,settings=settings):
                try:result,error=job.run(path,board,settings),''
                except Exception as exc:result,error=None,str(exc)
                if not w.closing:self.completed.emit(index,generation,result,error)
            threading.Thread(target=work,daemon=True,name=f'BoardLens-comparison-{index}').start()

    def analysis_finished(self,index,generation,result,error):
        if generation!=self.generation:return
        board=self.current()
        if board is None or not self.signature or self.key(board)!=self.signature or (result and result['fen']!=board.fen()):return
        self.jobs.pop(index,None)
        item=self.results[index];item.update(status='Error' if error else 'Ready',result=result,error=error)
        view=self.columns[index][1]
        if error:view.setText(error);return
        if not result:view.setText('Canceled');return
        kind=result.get('evaluation_kind','engine search evaluation')
        parts=[f'<p><b>{html.escape(kind)}</b></p>']
        if result.get('recommendation_type')=='strength-limited choice':parts.append('<p>#1 is the strength-limited choice. Its score may be below an alternative.</p>')
        for rank,line in enumerate(result['lines'],1):
            parts.append(f'<h3>#{rank} {html.escape(line["simple"])} · {line["score"]}</h3><p>{html.escape(line["description"])}</p><p>{html.escape(line["wdl"])}</p>')
            if line['reply_simple']:parts.append('<p>Reply: '+html.escape(line['reply_simple'])+'</p>')
            if line['pv']:parts.append('<p>'+html.escape(line['pv'])+'</p>')
        detail='one human-model prediction' if kind=='human-game outcome estimate' else f'depth {result["lines"][0]["depth"]}'
        parts.append(f'<p>{result.get("elapsed",0):.2f}s · {detail}</p>')
        view.setHtml(''.join(parts))

    def cancel(self,checked=False):
        self.generation+=1;self.following=False
        for index,job in list(self.jobs.items()):
            job.cancel();self.columns[index][1].setText('Canceled')
            if index<len(self.results):self.results[index]['status']='Canceled'
        self.jobs.clear()

    def snapshot(self):
        board=self.current()
        if not board or not self.signature or self.key(board)!=self.signature:return None
        return {'fen':board.fen(),'board_id':self.board_choice.currentData(),'engines':self.results}

    def closeEvent(self,event):
        self.cancel()
        for session in self.sessions:session.close()
        event.accept()
