from __future__ import annotations

import json
import os
import platform
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import chess


def data_dir() -> Path:
    if os.environ.get("BOARDLENS_DATA_DIR"):
        target = Path(os.environ["BOARDLENS_DATA_DIR"]).expanduser()
        target.mkdir(parents=True, exist_ok=True)
        return target
    if platform.system() == "Windows":
        root = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif platform.system() == "Darwin":
        root = Path.home() / "Library/Application Support"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
    target = root / "BoardLens"
    target.mkdir(parents=True, exist_ok=True)
    return target


DEFAULT_KEYS = {
    "suggest": "<ctrl>+<alt>+s",
    "move": "<ctrl>+<alt>+m",
    "watch": "<ctrl>+<alt>+a",
    "scan": "<ctrl>+<alt>+b",
    "stop": "<ctrl>+<alt>+x",
    "arrows": "<ctrl>+<alt>+h",
    "previous": "<ctrl>+<alt>+<left>",
    "next": "<ctrl>+<alt>+<right>",
    "live": "<ctrl>+<alt>+l",
}


def load_settings():
    try:
        value = json.loads((data_dir() / "settings.json").read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(value):
    path = data_dir() / "settings.json"
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2))
    temp.replace(path)


def find_engine():
    settings = load_settings()
    candidates = [settings.get("engine", ""), os.environ.get("STOCKFISH_EXECUTABLE", ""),
                  shutil.which("stockfish"), "/opt/homebrew/bin/stockfish", "/usr/local/bin/stockfish"]
    roots = [Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / "engine",
             data_dir() / "engine"]
    candidates.extend(str(p) for root in roots for p in sorted(root.glob("**/*"))
                      if p.is_file() and p.name.lower().startswith("stockfish")
                      and ((p.suffix.lower() == ".exe") if os.name == "nt" else (p.suffix == "" or p.name == "stockfish-macos-universal"))
                      and p.suffix.lower() not in {".txt", ".md", ".cpp", ".h", ".nnue", ".gz", ".zip"})
    for path in candidates:
        if isinstance(path, (str, os.PathLike)) and path and Path(path).is_file() and (os.name == "nt" or os.access(path, os.X_OK)):
            return str(path)
    return ""


def square_to_cell(square: int, white_bottom: bool):
    file, rank = chess.square_file(square), chess.square_rank(square)
    return (7 - rank, file) if white_bottom else (rank, 7 - file)


def cell_to_square(row: int, col: int, white_bottom: bool):
    return chess.square(col, 7 - row) if white_bottom else chess.square(7 - col, row)


def ordered_symbols(board: chess.Board, white_bottom=True):
    return [board.piece_at(cell_to_square(r, c, white_bottom)).symbol()
            if board.piece_at(cell_to_square(r, c, white_bottom)) else "."
            for r in range(8) for c in range(8)]


class PositionTracker:
    """Accept only complete, legal, unambiguous observations; never invent move history."""
    def __init__(self, board=None):
        self.board = board.copy() if board is not None else chess.Board()

    def update(self, symbols, white_bottom=True):
        if symbols == ordered_symbols(self.board, white_bottom):
            return "same", None
        matches = []
        for move in self.board.legal_moves:
            candidate = self.board.copy()
            candidate.push(move)
            if symbols == ordered_symbols(candidate, white_bottom):
                matches.append((move, candidate))
        if len(matches) == 1:
            move, self.board = matches[0]
            return "moved", move
        return "unmatched", None

    def reconcile(self, symbols, white_bottom=True):
        """Catch a missed pair of plies without losing turn or castling history."""
        before = ordered_symbols(self.board, white_bottom)
        changed = {cell_to_square(i//8,i%8,white_bottom) for i,(a,b) in enumerate(zip(before,symbols)) if a != b}
        matches = []
        for first in self.board.legal_moves:
            if first.from_square not in changed:
                continue
            candidate = self.board.copy()
            candidate.push(first)
            for second in list(candidate.legal_moves):
                if second.from_square not in changed:
                    continue
                candidate.push(second)
                if symbols == ordered_symbols(candidate, white_bottom):
                    matches.append(candidate.copy())
                candidate.pop()
        if len(matches) == 1:
            self.board = matches[0]
            return "moved", self.board.peek()
        return "unmatched", None


def board_from_symbols(symbols, white_bottom, turn, castling="-"):
    if len(symbols) != 64 or any(s not in ".PNBRQKpnbrqk" for s in symbols):
        raise ValueError("A board must contain exactly 64 recognized squares.")
    board = chess.Board(None)
    for i, symbol in enumerate(symbols):
        if symbol != ".":
            board.set_piece_at(cell_to_square(i // 8, i % 8, white_bottom), chess.Piece.from_symbol(symbol))
    board.turn = turn
    board.set_castling_fen(castling.strip() or "-")
    if not board.is_valid():
        raise ValueError("The recognized position is not legal. Check the crop, orientation, turn and castling rights, or enter its FEN.")
    return board


def describe_move(board, move):
    piece = board.piece_at(move.from_square)
    if not piece:
        return ""
    side = "White" if board.turn else "Black"
    if board.is_castling(move):
        text = f"{side} castles {'kingside' if chess.square_file(move.to_square) > 4 else 'queenside'}"
    else:
        verb = "captures on" if board.is_capture(move) else "moves to"
        text = f"{side}'s {chess.piece_name(piece.piece_type)} on {chess.square_name(move.from_square)} {verb} {chess.square_name(move.to_square)}"
        if board.is_en_passant(move):
            text += " (en passant)"
        if move.promotion:
            text += f", promoting to a {chess.piece_name(move.promotion)}"
    after = board.copy()
    after.push(move)
    if after.is_checkmate():
        text += "; checkmate"
    elif after.is_check():
        text += "; check"
    return text + "."


def simple_move(board,move):
    side='White' if board.turn else 'Black'
    if board.is_castling(move):
        return f"{side}: castle {'kingside' if chess.square_file(move.to_square)>4 else 'queenside'}"
    piece=board.piece_at(move.from_square)
    text=f"{side}: {chess.piece_name(piece.piece_type).capitalize()} {'takes on' if board.is_capture(move) else 'to'} {chess.square_name(move.to_square)}"
    if move.promotion:text+=f" — promote to {chess.piece_name(move.promotion)}"
    return text


def advantage(cp, mate=None):
    if mate is not None:
        return f"{'White' if mate > 0 else 'Black'} has a forced mate in {abs(mate)}"
    if abs(cp) < 25:
        return "Roughly equal"
    side = "White" if cp > 0 else "Black"
    lead = abs(cp)
    return f"{side} {'has a small edge' if lead < 100 else 'is better' if lead < 250 else 'has a clear advantage' if lead < 500 else 'is winning'}"


def move_insights(board, move):
    """Facts visible on this move; avoids inventing the engine's strategic reasoning."""
    facts = []
    piece = board.piece_at(move.from_square)
    if board.is_capture(move):
        captured = board.piece_at(move.to_square)
        name = chess.piece_name(captured.piece_type) if captured else "pawn"
        facts.append(f"Captures a {name}.")
    if piece and piece.piece_type in (chess.KNIGHT, chess.BISHOP):
        if chess.square_rank(move.from_square) == (0 if board.turn else 7):
            facts.append("Develops a minor piece from the back rank.")
    if move.to_square in (chess.D4, chess.E4, chess.D5, chess.E5):
        facts.append("Occupies a central square.")
    after = board.copy()
    after.push(move)
    if after.is_check():
        facts.append("The opponent must answer the check.")
    if not facts:
        facts.append("Compare the continuation below to see the engine's predicted play.")
    return " ".join(facts)


def validate_keys(keys):
    normalized = [str(value).strip().lower() for value in keys.values()]
    if any(not value for value in normalized) or len(set(normalized)) != len(normalized):
        raise ValueError("Each action needs a different, nonempty key combination.")
    return dict(zip(keys, normalized))


def can_send_move(board, result, symbols, white_bottom, allowed_side):
    """Final guard for an explicitly requested practice move."""
    if not result or result.get("fen") != board.fen():
        raise ValueError("Analyze the current position before sending a move.")
    if board.turn != allowed_side:
        raise ValueError("It is not the selected side’s turn.")
    if symbols != ordered_symbols(board, white_bottom):
        raise ValueError("The screen position changed. Scan and analyze again.")
    move = chess.Move.from_uci(result["lines"][0]["move"])
    if move not in board.legal_moves:
        raise ValueError("The suggested move is no longer legal.")
    return move


@dataclass(frozen=True)
class SearchSettings:
    seconds: float = 1.0
    depth: int = 18
    mode: str = "Time"
    multipv: int = 3
    threads: int = 2
    hash_mb: int = 128
    engine_kind: str = "stockfish"
    strength: str = "Full strength"
    skill: int = 20
    elo: int = 1500
    human_elo: int = 1500
    style: str = "Balanced"
    engine_id: str = "stockfish"
    predict_continuations: bool = True
    prediction_plies: int = 3
    prediction_seconds: float = 3.0
