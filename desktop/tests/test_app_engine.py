import threading
import time

import chess
import pytest

from chess_helper.app import MainWindow
from chess_helper.core import SearchSettings, find_engine
from chess_helper.engine import EngineJob


def wait(qt, condition, seconds=10):
    end = time.monotonic() + seconds
    while not condition() and time.monotonic() < end:
        qt.processEvents()
        time.sleep(.01)
    assert condition()


def test_real_stockfish_analysis_and_cancel():
    path = find_engine()
    if not path:
        pytest.skip("Install Stockfish for integration tests")
    result = EngineJob().run(path, chess.Board(), SearchSettings(seconds=.2, multipv=2))
    assert len(result["lines"]) == 2
    assert chess.Move.from_uci(result["lines"][0]["move"]) in chess.Board().legal_moves
    job = EngineJob()
    output = []
    thread = threading.Thread(target=lambda: output.append(job.run(path, chess.Board(), SearchSettings(mode="Depth", depth=60))))
    thread.start()
    time.sleep(.15)
    job.cancel()
    thread.join(6)
    assert not thread.is_alive() and output == [None]


def test_practice_gui_plays_one_suggestion_only_when_clicked(qt):
    window=MainWindow();window.show();qt.processEvents()
    if not window.engine_path.text():window.close();pytest.skip("Stockfish missing")
    try:
        window.seconds.setValue(.1);window.multipv.setValue(2);window.suggest_button.click()
        wait(qt,lambda:window.result is not None and not window.result.get('provisional'))
        assert "Opponent" in window.lines.toPlainText() and window.eval_bar.cp is not None
        assert not window.tracker.board.move_stack and not hasattr(window,'auto_button')
        window.move_button.click();assert not window.tracker.board.turn
        window.stop();window.undo();assert not window.tracker.board.move_stack
    finally:window.close()


def test_screen_clicks_and_unconfirmed_move_guard(qt):
    window=MainWindow()
    try:
        window.source.setCurrentIndex(1);assert not hasattr(window,'auto_button')
        window.pending_until=time.monotonic()-1;window.live_button.setChecked(True);window.poll()
        assert not window.live_button.isChecked() and "did not confirm" in window.status_label.text()
    finally:window.close()


def test_live_mode_is_suggestions_only_and_keeps_following(qt, monkeypatch, render_board):
    import numpy as np
    window=MainWindow()
    images=[render_board(chess.Board())]
    def frame(screen):
        image=np.full((800,800,3),24,np.uint8)
        image[:512,:512]=images[0]
        return image
    monkeypatch.setattr("chess_helper.app.capture",frame)
    clicks=[]
    monkeypatch.setattr(window.clicker,"start",lambda *args:clicks.append(args))
    window.seconds.setValue(.1)
    window.multipv.setValue(1)
    window.source.setCurrentIndex(1)
    wait(qt,lambda:window.result is not None)
    window.play_best()
    assert not clicks and not hasattr(window,'auto_button')
    assert window.move_button.isHidden()
    assert window.allow_clicks.isHidden()
    board=chess.Board();board.push_uci("e2e4")
    images[0]=render_board(board)
    wait(qt,lambda:window.tracker.board.fen()==board.fen())
    assert not clicks and window._monitoring
    window.close()
