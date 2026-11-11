import json
from pathlib import Path
import threading
import time

import chess
import cv2
import pytest

from chess_helper.app import MainWindow
from chess_helper.core import PositionTracker, ordered_symbols
from chess_helper.recognition import Recognizer, position_from_read


FIXTURES = Path(__file__).parent / "fixtures"
MANIFEST = json.loads((FIXTURES / "testset-manifest.json").read_text())


@pytest.fixture(scope="module")
def recognizer():
    return Recognizer()


@pytest.mark.parametrize("name", list(MANIFEST))
def test_external_screenshot_corpus(recognizer, name):
    expected = MANIFEST[name]
    result = recognizer.scan(cv2.imread(str(FIXTURES/name)))
    if expected["expect"] == "low-confidence-reject":
        assert result is None
    else:
        assert result is not None, name
        board, known = position_from_read(result)
        assert board.board_fen() == expected["fen"]
        assert result.white_bottom == (expected["orientation"] == "white")


def test_board_free_screen_not_recognized(recognizer):
    assert recognizer.scan(cv2.imread(str(FIXTURES/"reddit-chrome-no-board.png"))) is None


def test_missed_pair_of_moves_keeps_history():
    tracker = PositionTracker()
    board = chess.Board()
    board.push_uci("e2e4")
    board.push_uci("c7c5")
    assert tracker.reconcile(ordered_symbols(board))[0] == "moved"
    assert tracker.board.fen() == board.fen()
    assert len(tracker.board.move_stack) == 2


def test_stop_is_responsive_during_detection_and_discards_late_results(qt, monkeypatch):
    from PySide6.QtTest import QTest
    from PySide6.QtCore import Qt
    entered = threading.Event()
    def slow(*args, **kwargs):
        entered.set()
        time.sleep(.8)
        return None
    monkeypatch.setattr(Recognizer, "scan", slow)
    window = MainWindow()
    window.show()
    window.source.setCurrentIndex(1)
    deadline = time.monotonic()+3
    while not entered.is_set() and time.monotonic() < deadline:
        qt.processEvents()
        time.sleep(.01)
    assert entered.is_set()
    started = time.monotonic()
    QTest.mouseClick(window.stop_button, Qt.MouseButton.LeftButton)
    qt.processEvents()
    assert time.monotonic()-started < .2
    assert not window._monitoring and not window._scan_busy
    assert not window.live_button.isChecked()
    message = window.status_label.text()
    QTest.qWait(1000)
    assert window.status_label.text() == message
    assert window._last_read is None
    window.close()


def test_stop_ignores_an_engine_that_returns_after_cancellation(qt, monkeypatch):
    import chess.engine
    from chess_helper.engine import EngineJob, summarize
    def late(job, path, board, settings):
        time.sleep(.25)
        return summarize(board,[{"pv":[chess.Move.from_uci("e2e4")],
                                 "score":chess.engine.PovScore(chess.engine.Cp(20),chess.WHITE)}],"late engine")
    monkeypatch.setattr(EngineJob,"run",late)
    window = MainWindow()
    if not window.engine_path.text():
        window.close()
        pytest.skip("Install Stockfish to exercise the engine path")
    window.suggest()
    window.stop_button.click()
    from PySide6.QtTest import QTest
    QTest.qWait(500)
    assert window.result is None and window.eval_bar.cp is None
    assert window.status_label.text().startswith("STOPPED")
    window.close()
