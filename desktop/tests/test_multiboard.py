import time
import chess
import chess.engine
import numpy as np
from PySide6.QtGui import QGuiApplication
from chess_helper.app import MainWindow
from chess_helper.capture import screen_key
from chess_helper.recognition import Recognizer
from chess_helper.vision import Detection
from chess_helper.core import ordered_symbols
from chess_helper.engine import summarize


def test_three_boards_found_in_one_screenshot_including_duplicate_positions(render_board):
    board=chess.Board();second=board.copy();second.push_uci('e2e4')
    image=np.full((760,1800,3),28,np.uint8)
    for x,b in zip((25,590,1155),(board,second,board)):
        image[100:612,x:x+512]=render_board(b)
    reads=Recognizer().scan_all(image)
    assert len(reads)==3
    assert [r.symbols for r in reads]==[ordered_symbols(board),ordered_symbols(second),ordered_symbols(board)]


def answers(render_board,boards):
    recognizer=Recognizer();key=screen_key(QGuiApplication.primaryScreen())
    result=[]
    for index,board in enumerate(boards):
        read=recognizer.read(render_board(board));read.detection=Detection(30+index*560,100,512,1.)
        result.append((key,'test display',read,1800,800))
    return result


def prepare(qt,monkeypatch):
    w=MainWindow();w.show();qt.processEvents()
    w.source.blockSignals(True);w.source.setCurrentIndex(1);w.source.blockSignals(False)
    w._monitoring=True
    monkeypatch.setattr(w,'suggest',lambda **kw:None)
    monkeypatch.setattr(w.multi,'search',lambda state:None)
    return w


def test_three_independent_boards_track_and_collapse_to_one(qt,monkeypatch,render_board):
    w=prepare(qt,monkeypatch);board=chess.Board()
    initial=answers(render_board,[board,board,board])
    for _ in range(2):w.live_finished(w._live_token,initial,'')
    assert len(w.multi.states)==2 and w.multi.count==3
    assert w.multi.grid.count()==3 and not w.boards_button.isHidden()
    assert w.workspace_stack.currentIndex()==1
    moved=board.copy();moved.push_uci('e2e4')
    updated=answers(render_board,[board,moved,board])
    for _ in range(2):w.live_finished(w._live_token,updated,'')
    assert w.tracker.board.fen()==chess.STARTING_FEN
    assert w.multi.states[0].tracker.board.fen()==moved.fen()
    assert w.multi.states[1].tracker.board.fen()==chess.STARTING_FEN
    for _ in range(3):w.live_finished(w._live_token,updated[0],'')
    assert not w.multi.states and w.multi.count==1
    assert w.multi.grid.count()==1 and w.boards_button.isHidden()
    assert w.workspace_stack.currentIndex()==0
    w.close()


def test_each_secondary_board_keeps_its_own_locked_move(qt,monkeypatch,render_board):
    w=prepare(qt,monkeypatch);batch=answers(render_board,[chess.Board()]*3)
    for _ in range(2):w.live_finished(w._live_token,batch,'')
    w.stick_to_move.setChecked(True)
    for state,move in zip(w.multi.states,('e2e4','g1f3')):
        result=summarize(state.tracker.board,[{'pv':[chess.Move.from_uci(move)],'score':chess.engine.PovScore(chess.engine.Cp(20),chess.WHITE)}],'test')
        w.multi.finished(state,state.generation,result,'',True)
    before=[s.card.move.text() for s in w.multi.states]
    for state in w.multi.states:
        newer=summarize(state.tracker.board,[{'pv':[chess.Move.from_uci('d2d4')],'score':chess.engine.PovScore(chess.engine.Cp(-30),chess.WHITE)}],'test')
        w.multi.finished(state,state.generation,newer,'',False)
    assert [s.card.move.text() for s in w.multi.states]==before
    assert [s.card.view.arrows[0]['move'].uci() for s in w.multi.states]==['e2e4','g1f3']
    assert all(s.card.bar.cp==-30 for s in w.multi.states)
    w.stick_to_move.setChecked(False)
    assert [s.card.view.arrows[0]['move'].uci() for s in w.multi.states]==['d2d4','d2d4']
    w.close()


def test_reordered_detections_keep_identity_without_array_comparison(qt,monkeypatch,render_board):
    w=prepare(qt,monkeypatch);batch=answers(render_board,[chess.Board()]*3)
    for _ in range(2):w.live_finished(w._live_token,batch,'')
    original_region=w.region
    for _ in range(2):w.live_finished(w._live_token,list(reversed(batch)),'')
    assert w.region==original_region
    assert len(w.multi.states)==2 and w.multi.count==3
    w.close()


def test_expand_button_shows_inline_settings_and_compact_button_returns(qt):
    w=MainWindow();w.show();qt.processEvents()
    w.toggle_compact(True)
    assert w.compact_button.text()=='Expand'
    w.compact_button.click();qt.processEvents()
    assert not w._compact and w.sidebar_host.isVisible()
    assert w.settings_tabs.parentWidget()==w.sidebar_host
    assert w.compact_button.text()=='Compact'
    w.compact_button.click();qt.processEvents()
    assert w._compact and not w.sidebar_host.isVisible()
    w.settings_button.click();qt.processEvents()
    assert w.settings_dialog.isVisible()
    w.close()
