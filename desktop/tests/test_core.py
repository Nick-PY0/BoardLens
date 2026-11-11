import chess
import chess.engine
import pytest

from chess_helper.core import (PositionTracker, SearchSettings, advantage, board_from_symbols,
    can_send_move, cell_to_square, describe_move, load_settings, ordered_symbols,
    save_settings, square_to_cell, validate_keys)
from chess_helper.engine import search_limit, summarize


@pytest.mark.parametrize("white_bottom", [True, False])
def test_orientation(white_bottom):
    for square in chess.SQUARES:
        assert cell_to_square(*square_to_cell(square, white_bottom), white_bottom) == square
    assert square_to_cell(chess.A1, white_bottom) == ((7, 0) if white_bottom else (0, 7))


@pytest.mark.parametrize("fen,uci", [
    (chess.STARTING_FEN, "e2e4"),
    ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "e1g1"),
    ("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", "e5d6"),
    ("4k3/P7/8/8/8/8/8/4K3 w - - 0 1", "a7a8n"),
])
def test_tracks_special_moves_and_history(fen, uci):
    before = chess.Board(fen)
    after = before.copy()
    after.push_uci(uci)
    tracker = PositionTracker(before)
    for white_bottom in (True, False):
        tracker = PositionTracker(before)
        state, move = tracker.update(ordered_symbols(after, white_bottom), white_bottom)
        assert state == "moved" and move.uci() == uci
        assert tracker.board.fen() == after.fen()
        assert tracker.board.move_stack


def test_unmatched_observation_never_overwrites_position():
    tracker = PositionTracker()
    symbols = ordered_symbols(tracker.board)
    symbols[0] = "."
    assert tracker.update(symbols) == ("unmatched", None)
    assert tracker.board.fen() == chess.STARTING_FEN


def test_import_requires_explicit_rights_and_valid_kings():
    symbols = ordered_symbols(chess.Board())
    board = board_from_symbols(symbols, True, chess.WHITE, "KQkq")
    assert board.fen() == chess.STARTING_FEN
    assert not board_from_symbols(symbols, True, chess.WHITE).has_castling_rights(chess.WHITE)
    with pytest.raises(ValueError):
        board_from_symbols(["."] * 64, True, chess.WHITE)
    with pytest.raises(ValueError):
        board_from_symbols(["."] * 63, True, chess.WHITE)


def test_time_and_depth_have_distinct_limits():
    assert search_limit(SearchSettings(mode="Time")).depth is None
    assert search_limit(SearchSettings(mode="Depth")).time is None
    both = search_limit(SearchSettings(mode="Time + depth", seconds=2, depth=12))
    assert both.time == 2 and both.depth == 12


def test_scores_and_reply_use_correct_color_perspective():
    board = chess.Board()
    board.push_uci("e2e4")
    info = {"pv": [chess.Move.from_uci("e7e5"), chess.Move.from_uci("g1f3")],
            "score": chess.engine.PovScore(chess.engine.Cp(-150), chess.BLACK), "depth": 10}
    result = summarize(board, [info], "Test")
    lead = result["lines"][0]
    assert lead["score"] == "+1.50" and lead["advantage"] == "White is better"
    assert "Black's pawn" in lead["description"] and "White's knight" in lead["reply"]
    assert lead["pv"].startswith("1...e5")


def test_stale_and_wrong_side_results_cannot_click():
    board = chess.Board()
    result = {"fen": board.fen(), "lines": [{"move": "e2e4"}]}
    symbols = ordered_symbols(board)
    assert can_send_move(board, result, symbols, True, chess.WHITE).uci() == "e2e4"
    with pytest.raises(ValueError):
        can_send_move(board, result, symbols, True, chess.BLACK)
    symbols[0] = "."
    with pytest.raises(ValueError):
        can_send_move(board, result, symbols, True, chess.WHITE)
    board.push_uci("e2e4")
    with pytest.raises(ValueError):
        can_send_move(board, result, ordered_symbols(board), True, chess.BLACK)


def test_settings_and_key_collisions():
    save_settings({"seconds": 2, "keys": {"stop": "<ctrl>+x"}})
    assert load_settings()["seconds"] == 2
    with pytest.raises(ValueError):
        validate_keys({"a": "<ctrl>+x", "b": "<CTRL>+X"})


def test_mate_sign_and_explanations():
    assert "Black" in advantage(-100000, -2)
    board = chess.Board("7k/8/5KQ1/8/8/8/8/8 w - - 0 1")
    assert "checkmate" in describe_move(board, chess.Move.from_uci("g6g7"))
