"""Independent positions, searches and passive overlays for additional boards."""
from __future__ import annotations
from copy import deepcopy
import threading
import time
import chess
from PySide6.QtCore import QObject,Signal,Qt,QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QGridLayout,QComboBox
from .capture import BoardRegion,screen_key
from .core import PositionTracker,ordered_symbols
from .engine import EngineJob,EngineSession
from .hints import LiveHintFilter
from .overlay import BoardOverlay
from .recognition import position_from_read
from .widgets import BoardView,EvalBar,BoardArea


def near(a,b):
    if a.screen_name!=b.screen_name:return False
    dx=(a.x+a.size/2)-(b.x+b.size/2);dy=(a.y+a.size/2)-(b.y+b.size/2)
    return dx*dx+dy*dy < (max(a.size,b.size)*.55)**2


def region_of(answer):
    key,_,read,width,height=answer;d=read.detection
    return BoardRegion(key,width,height,d.x,d.y,d.size)


class BoardPage(QWidget):
    resized=Signal()
    def resizeEvent(self,event):
        super().resizeEvent(event)
        QTimer.singleShot(0,self.resized.emit)


class BoardCard(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setObjectName('boardCard')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground,True)
        layout=QVBoxLayout(self);layout.setContentsMargins(12,10,12,10);layout.setSpacing(5)
        self.title=QLabel();self.title.setStyleSheet('font-size:15px;font-weight:600;color:#a3e6c0;')
        self.state=QLabel('Reading board…');self.state.setWordWrap(True)
        layout.addWidget(self.title);layout.addWidget(self.state)
        self.bar=EvalBar();self.bar.setFixedWidth(54)
        self.bar.score_label.setStyleSheet("background:#344a48;color:white;border-radius:5px;font-size:12px;font-weight:700;padding:0;")
        self.view=BoardView();self.view.setStyleSheet('background:transparent;')
        self.view.setToolTip('Recognized live position. Play moves on the original board.')
        self.board_holder=BoardArea(self.view,self.bar)
        self.board_holder.setMinimumSize(180,160)
        layout.addWidget(self.board_holder)
        self.move=QLabel('Waiting for analysis');self.move.setWordWrap(True)
        self.score=QLabel('Evaluation —');self.score.setWordWrap(True)
        layout.addWidget(self.move);layout.addWidget(self.score)
        self.turn=QComboBox();self.turn.addItems(['Auto turn','White to move','Black to move'])
        self.turn.setToolTip('Use if joining a static position without a turn clue. Each board tracks its own moves.')
        layout.addWidget(self.turn)
        layout.addStretch(1)
        self.setStyleSheet('QWidget#boardCard {background:#1b3028;border:1px solid #355444;border-radius:10px;} QWidget#boardCard QLabel {background:transparent;border:none;}')

    def resizeEvent(self,event):
        super().resizeEvent(event)
        height=max(160,min(self.width()-24,self.height()-180))
        self.board_holder.setFixedHeight(height)


class BoardState:
    def __init__(self,identity,answer):
        self.identity=identity;self.region=region_of(answer);self.name=answer[1]
        self.read=answer[2];self.tracker=None;self.known=False
        self.key=None;self.stable=0;self.confirmed=False;self.misses=0
        self.result=None;self.pinned=None;self.hint_filter=LiveHintFilter();self.job=None;self.generation=0
        self.session=EngineSession();self.last_requested=None;self.closed=False
        self.overlay=BoardOverlay();self.card=BoardCard();self.turn_override=None

    def cancel(self,close=False):
        self.generation+=1
        if self.job:self.job.cancel();self.job=None
        self.overlay.hide();self.last_requested=None
        if close:
            self.closed=True;self.session.close();self.overlay.close();self.card.deleteLater()


class MultiBoards(QObject):
    updated=Signal(object,int,object,str,bool)

    def __init__(self,window):
        super().__init__(window)
        self.window=window;self.states=[];self.serial=0;self.primary_misses=0
        self.updated.connect(self.finished)
        self.primary_card=BoardCard();self.primary_card.turn.hide()
        self.page=BoardPage();self.page.resized.connect(self.layout_cards);self.grid=QGridLayout(self.page);self.grid.setContentsMargins(0,0,0,0);self.grid.setSpacing(10)
        self.count=0;self._columns=0

    def regions(self):
        return ([self.window.region] if self.window.region else [])+[s.region for s in self.states]

    def overlays(self):return [self.window.overlay]+[s.overlay for s in self.states]

    def accept(self,answers):
        w=self.window;remaining=list(answers)
        primary=None
        if w.region:
            matches=[a for a in remaining if near(w.region,region_of(a))]
            if matches:primary=min(matches,key=lambda a:abs(region_of(a).x-w.region.x)+abs(region_of(a).y-w.region.y))
        elif remaining:primary=remaining[0]
        if primary:
            self.primary_misses=0;remaining=[a for a in remaining if a is not primary]
        else:self.primary_misses+=1
        if primary is None and remaining and self.primary_misses>=3:
            primary=remaining.pop(0);self.primary_misses=0
            w._stable_key=None;w._stable_frames=0;w._position_locked=False
            w.invalidate(release_move=True)
        used=set()
        for answer in remaining:
            region=region_of(answer)
            state=next((s for s in self.states if s.identity not in used and near(s.region,region)),None)
            if state is None:
                if len(self.states)>=2:continue
                self.serial+=1;state=BoardState(self.serial,answer);self.states.append(state)
                state.card.turn.currentIndexChanged.connect(lambda index,state=state:self.turn_changed(state,index))
            used.add(state.identity);self.observe(state,answer)
        for state in list(self.states):
            if primary and near(state.region,region_of(primary)):
                state.cancel(close=True);self.states.remove(state);continue
            if state.identity not in used:
                state.misses+=1;state.confirmed=False
                if state.misses>=3:
                    state.cancel(close=True);self.states.remove(state)
                elif state.misses>1:state.overlay.hide()
        self.count=(1 if primary or (w.region and self.primary_misses<3) else 0)+len(self.states)
        self.layout_cards()
        w.refresh_targets()
        return primary

    def observe(self,state,answer):
        state.region=region_of(answer);state.name=answer[1];read=answer[2];state.misses=0
        key=(tuple(read.symbols),read.white_bottom,getattr(read,'exact_fen',None))
        if key!=state.key:
            state.key=key;state.stable=1;state.confirmed=False;state.read=read
            state.overlay.hide();self.render(state);return
        state.stable+=1;state.confirmed=True;state.read=read
        try:
            if state.tracker is None or (getattr(read,'exact_fen',None) and state.tracker.board.fen()!=read.exact_fen):
                board,state.known=position_from_read(read,state.turn_override);state.tracker=PositionTracker(board)
            else:
                matches=[]
                for bottom in (True,False):
                    probe=PositionTracker(state.tracker.board)
                    status,_=probe.update(read.symbols,bottom)
                    if status!='unmatched':matches.append(bottom)
                if len(matches)==1:read.white_bottom=matches[0]
                status,_=state.tracker.update(read.symbols,read.white_bottom)
                if status=='unmatched':status,_=state.tracker.reconcile(read.symbols,read.white_bottom)
                if status=='unmatched':
                    board,state.known=position_from_read(read,state.turn_override,state.tracker.board)
                    state.tracker=PositionTracker(board)
                elif status=='moved':state.known=True
            fen=state.tracker.board.fen()
            if (state.last_requested and state.last_requested!=fen) or (state.result and state.result['fen']!=fen):
                state.cancel();state.result=None;state.pinned=None;state.hint_filter.reset()
            if state.pinned and state.pinned['fen']!=fen:state.pinned=None
            if state.last_requested!=fen and state.job is None and not state.tracker.board.is_game_over():self.search(state)
        except ValueError:state.confirmed=False
        self.render(state)

    def search(self,state):
        w=self.window
        if not w._monitoring or w._reviewing or state.closed:return
        try:path=w.analysis_command()
        except ValueError as exc:state.card.state.setText(str(exc));return
        board=state.tracker.board.copy();settings=w.search_settings();w.evaluations.request(board)
        state.generation+=1;generation=state.generation
        state.last_requested=board.fen();job=state.job=EngineJob();job.session=state.session
        if w.early_suggestions.isChecked():
            job.on_update=lambda result:self.updated.emit(state,generation,result,'',True)
        def work():
            try:result,error=job.run(path,board,settings),''
            except Exception as exc:result,error=None,str(exc)
            if not w.closing:self.updated.emit(state,generation,result,error,False)
        threading.Thread(target=work,daemon=True,name=f'BoardLens-board-{state.identity}').start()

    def finished(self,state,generation,result,error,provisional):
        if state.closed or self.window.closing or generation!=state.generation:return
        if not provisional:state.job=None
        if error:state.card.state.setText('Engine: '+error);return
        if not result or state.tracker is None or result['fen']!=state.tracker.board.fen():return
        state.result=dict(result,provisional=provisional)
        self.render(state)

    def render(self,state):
        w=self.window;card=state.card
        index=self.states.index(state)+2 if state in self.states else 2
        card.title.setText(f'Board {index}')
        if state.tracker is None:
            card.state.setText('Confirming position…');card.view.hide();card.bar.hide();return
        card.view.show();card.bar.show()
        board=state.tracker.board;bottom=state.read.white_bottom
        card.view.board=board.copy();card.view.white_bottom=bottom
        card.bar.white_bottom=bottom
        text=f"{'White' if board.turn else 'Black'} to move · {'White' if bottom else 'Black'} bottom"
        if not state.known:text+=' · turn inferred'
        if not state.confirmed:text+=' · checking board'
        card.state.setText(text)
        raw=state.result
        if not w.stick_to_move.isChecked():state.pinned=None
        elif state.pinned is None and raw:
            previous=state.hint_filter.displayed
            state.pinned=deepcopy(previous if previous and previous['fen']==board.fen() else raw)
        shown=state.pinned if w.stick_to_move.isChecked() else state.hint_filter.select(raw,w.steady_arrows.isChecked())
        if state.pinned and raw:
            from .hints import merge_continuation
            merge_continuation(state.pinned,raw)
        arrows=[]
        current=(board.turn==bottom) if w.only_my_color.isChecked() else (w.show_white.isChecked() if board.turn else w.show_black.isChecked())
        other=not w.only_my_color.isChecked() and (w.show_black.isChecked() if board.turn else w.show_white.isChecked())
        if shown and shown['fen']==board.fen():
            lead=shown['lines'][0];locked=w.stick_to_move.isChecked()
            card.move.setText(lead['simple']+(' · locked' if locked else '') if current else 'Waiting for your turn' if w.only_my_color.isChecked() else 'Suggestions hidden')
            for rank,line in enumerate(shown['lines'][:1 if locked else min(w.arrow_count.value(),w.multipv.value())],1):
                if current and w.visible_rank(rank):arrows.append({'move':chess.Move.from_uci(line['move']),'color':['#ffc65c','#61b9ff','#c49bff'][(rank-1)%3]})
            if other and not locked and w.show_reply.isChecked() and w.rank_best.isChecked() and lead.get('reply_move'):
                arrows.append({'move':chess.Move.from_uci(lead['reply_move']),'color':'#53e2e4','reply':True,'dashed':w.dashed_reply.isChecked()})
        else:card.move.setText('Thinking…' if state.job else 'Waiting for analysis')
        if raw:
            lead=w.evaluations.score(board,raw);card.bar.cp,card.bar.mate=lead['cp'],lead['mate']
            card.score.setText(f"{lead['score']} · {lead['advantage']}"+(' · thinking' if raw.get('provisional') else ''))
        marks,messages=w.threat_marks(board,bottom);card.view.marks=marks;card.view.setToolTip("\n".join(messages));card.view.arrows=arrows;card.view.update();card.bar.update()
        if (arrows or marks) and w.overlay_enabled.isChecked() and w._monitoring and state.confirmed and not w._reviewing:
            if getattr(state.read,'desktop_rect',None):
                from PySide6.QtCore import QRect
                rect=QRect(*[round(v) for v in state.read.desktop_rect]);target=next((s for s in QGuiApplication.screens() if s.geometry().contains(rect.center())),w.window_screen());state.overlay.set_arrows(rect,bottom,[dict(a,points=state.read.points) for a in arrows],target,[dict(m,points=state.read.points) for m in marks]);return
            target=next((s for s in QGuiApplication.screens() if screen_key(s)==state.region.screen_name),None)
            if target:state.overlay.set_arrows(state.region.desktop_rect(target.geometry()),bottom,arrows,target,marks)
        else:state.overlay.hide()

    def update_primary(self):
        w=self.window;card=self.primary_card;card.title.setText('Board 1')
        card.state.setText(w.position_label.text());card.view.board=w.tracker.board.copy();card.view.white_bottom=w.white_bottom
        card.view.arrows=list(w.board_view.arrows);card.view.marks=list(w.board_view.marks);card.view.update()
        card.bar.cp,card.bar.mate=w.eval_bar.cp,w.eval_bar.mate;card.bar.white_bottom=w.white_bottom;card.bar.update()
        card.move.setText(w.simple_label.text());card.score.setText(w.eval_label.text())

    def layout_cards(self):
        w=self.window
        if not hasattr(w,'boards_button'):return
        cards=([self.primary_card] if self.count>len(self.states) else [])+[s.card for s in self.states]
        columns=len(cards) if self.page.width()>=len(cards)*250 else min(2,len(cards))
        columns=max(1,columns)
        existing=[self.grid.itemAt(i).widget() for i in range(self.grid.count())]
        if existing!=cards or columns!=self._columns:
            while self.grid.count():self.grid.takeAt(0)
            for index,card in enumerate(cards):self.grid.addWidget(card,index//columns,index%columns)
            self._columns=columns
        self.update_primary()
        previous=w.boards_button.isVisible()
        w.boards_button.setVisible(self.count>1)
        w.focus_button.setVisible(self.count>1)
        w.boards_button.setText(f'Boards\n{self.count}')
        if self.count<=1:
            w.boards_button.blockSignals(True);w.boards_button.setChecked(False);w.boards_button.blockSignals(False)
            if w.workspace_stack.currentIndex() !=2:w.workspace_stack.setCurrentIndex(0)
        elif not previous:
            w.boards_button.blockSignals(True);w.boards_button.setChecked(True);w.boards_button.blockSignals(False)
            if w.workspace_stack.currentIndex() !=2:w.workspace_stack.setCurrentIndex(1)

    def repaint(self):
        for state in self.states:self.render(state)
        self.update_primary()

    def turn_changed(self,state,index):
        state.turn_override=None if index==0 else index==1
        if state.read:
            board,state.known=position_from_read(state.read,state.turn_override)
            state.cancel();state.tracker=PositionTracker(board);state.result=None;state.pinned=None
            if state.confirmed:self.search(state)
        self.render(state)

    def settings_changed(self):
        for state in self.states:
            state.cancel();state.result=None;state.pinned=None;state.hint_filter.reset()
            if state.confirmed:self.search(state)
            self.render(state)

    def stop(self):
        for state in self.states:state.cancel()

    def reset(self):
        for state in self.states:state.cancel(close=True)
        self.states.clear();self.primary_misses=0;self.count=0;self.layout_cards()

    def close(self):self.reset()
