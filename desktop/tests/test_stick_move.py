import time
import chess
import chess.engine
import pytest
from chess_helper.app import MainWindow
from chess_helper.engine import summarize


def result(board,move,cp=20):
    probe=board.copy();first=chess.Move.from_uci(move);probe.push(first)
    pv=[first]+([] if probe.is_game_over() else [next(iter(probe.legal_moves))])
    return summarize(board,[{'pv':pv,'score':chess.engine.PovScore(chess.engine.Cp(cp),chess.WHITE),'depth':12}], 'test engine')


def test_first_move_stays_locked_through_progress_and_final_but_eval_updates(qt):
    w=MainWindow();w.stick_to_move.setChecked(True)
    board=w.tracker.board
    a=result(board,'e2e4');b=result(board,'d2d4',-80)
    w.engine_progress(w.generation,a)
    assert [x['move'].uci() for x in w.board_view.arrows]==['e2e4']
    w.engine_progress(w.generation,b)
    w.engine_finished(w.generation,b,'')
    assert w.result['lines'][0]['move']=='d2d4'
    assert [x['move'].uci() for x in w.board_view.arrows]==['e2e4']
    assert 'e4' in w.simple_label.text() and 'locked' in w.simple_label.text()
    assert not w.reply_label.text() and w.eval_bar.cp==-80
    w.stick_to_move.setChecked(False)
    assert w.board_view.arrows[0]['move'].uci()=='d2d4'
    assert 'd4' in w.simple_label.text()
    w.close()


def test_lock_preserves_same_position_reanalysis_and_releases_for_new_board(qt):
    w=MainWindow();w.result=result(w.tracker.board,'e2e4')
    w.stick_to_move.setChecked(True)
    w.invalidate(preserve_eval=True)
    assert w.result is None
    assert [x['move'].uci() for x in w.board_view.arrows]==['e2e4']
    w.engine_progress(w.generation,result(w.tracker.board,'d2d4'))
    assert w.board_view.arrows[0]['move'].uci()=='e2e4'
    w.tracker.board.push_uci('e2e4');w.invalidate();w.refresh_board()
    w.engine_progress(w.generation,result(w.tracker.board,'e7e5'))
    assert [x['move'].uci() for x in w.board_view.arrows]==['e7e5']
    w.close()


def test_scan_now_releases_pin_and_setting_persists(qt,monkeypatch):
    w=MainWindow();w.result=result(w.tracker.board,'e2e4')
    w.stick_to_move.setChecked(True);w.save()
    monkeypatch.setattr(w,'request_scan',lambda **kw:None)
    w.scan_now()
    assert w._pinned_result is None and not w.board_view.arrows
    assert w.stick_to_move.isChecked()
    w.close()
    again=MainWindow()
    assert again.stick_to_move.isChecked() and again._pinned_result is None
    again.close()
