import chess
import cv2
import numpy as np
import pytest

from chess_helper.capture import BoardRegion, pixmap_bgr
from chess_helper.core import ordered_symbols
from chess_helper.vision import Templates, checker_score, detect_boards


def render(qt, board, white_bottom=True, size=560):
    from chess_helper.widgets import BoardView
    view = BoardView()
    view.resize(size + 32, size + 32)
    view.board = board
    view.white_bottom = white_bottom
    image = pixmap_bgr(view.grab())
    return image[16:16 + size, 16:16 + size].copy()


def test_retina_and_negative_monitor_coordinates(qt):
    from PySide6.QtCore import QRect
    region = BoardRegion("left", 2560, 1600, 320, 160, 800)
    geometry = QRect(-1280, 0, 1280, 800)
    assert region.square_center(chess.A8, True, geometry) == (-1095, 105)
    assert region.square_center(chess.H1, False, geometry) == (-1095, 105)
    assert region.desktop_rect(geometry) == QRect(-1120, 80, 400, 400)
    with pytest.raises(ValueError):
        region.crop(np.zeros((800, 1280, 3), np.uint8))


@pytest.mark.parametrize("white_bottom", [True, False])
def test_learn_and_read_moves_on_both_colors(qt, white_bottom, tmp_path):
    board = chess.Board()
    start = render(qt, board, white_bottom)
    templates = Templates.learn(start, board, white_bottom)
    templates.save(tmp_path / "style.npz")
    templates = Templates.load(tmp_path / "style.npz")
    assert templates.complete
    for uci in ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6", "b5c6", "d7c6"]:
        board.push_uci(uci)
        symbols, reliable, confidence = templates.read(render(qt, board, white_bottom))
        assert symbols == ordered_symbols(board, white_bottom), (uci, confidence)
        assert reliable, (uci, confidence)


def test_board_detection_and_uncertainty(qt):
    board = render(qt, chess.Board(), size=512)
    canvas = np.full((850, 1200, 3), (31, 42, 39), dtype=np.uint8)
    canvas[120:632, 240:752] = board
    candidates = detect_boards(canvas)
    assert any(abs(d.x - 240) < 5 and abs(d.y - 120) < 5 and abs(d.size - 512) < 5 for d in candidates)
    assert checker_score(board) > .9
    templates = Templates.learn(board, chess.Board(), True)
    corrupt = board.copy()
    cv2.rectangle(corrupt, (80, 75), (165, 170), (10, 10, 240), -1)
    assert not templates.read(corrupt)[1]
    with pytest.raises(ValueError):
        Templates.learn(np.zeros_like(board), chess.Board(), True)
