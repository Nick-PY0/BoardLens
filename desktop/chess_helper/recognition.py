"""Local, calibration-free chess tile inference using the MIT Fenshot CNN."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import chess
import cv2
import numpy as np

from .core import board_from_symbols, ordered_symbols
from .detection import grid_candidates,refine_grid
from .vision import Detection, checker_score, complete_grid

LABELS = ".KQRBNPkqrbnp"


@dataclass
class Read:
    symbols: list[str]
    confidence: np.ndarray
    probabilities: np.ndarray
    white_bottom: bool
    turn_hint: bool | None
    image: np.ndarray
    detection: Detection | None = None

    @property
    def reliable(self):
        return bool(self.confidence.min() >= .70 and self.confidence.mean() >= .90
                    and self.symbols.count("K") == 1 and self.symbols.count("k") == 1)


def orientation(symbols):
    white = [i // 8 for i, symbol in enumerate(symbols) if symbol == "P"]
    black = [i // 8 for i, symbol in enumerate(symbols) if symbol == "p"]
    if white and black and abs(np.mean(white) - np.mean(black)) > .5:
        return bool(np.mean(white) > np.mean(black))
    wk, bk = symbols.index("K") if "K" in symbols else 60, symbols.index("k") if "k" in symbols else 4
    return wk > bk


def last_move_turn(image, symbols):
    """Last-move squares normally share a highlight distinct from both tile colors."""
    h, w = image.shape[:2]
    colors = []
    for row in range(8):
        for col in range(8):
            samples = [image[int((row+dy)*h/8), int((col+dx)*w/8)].astype(float)
                       for dy, dx in ((.08,.08),(.08,.92),(.92,.08),(.92,.92))]
            colors.append(np.median(samples, axis=0))
    colors = np.array(colors)
    parity = np.indices((8,8)).sum(0).ravel() % 2
    means = [np.median(colors[parity == p], axis=0) for p in (0,1)]
    errors = np.linalg.norm(colors - np.array(means)[parity], axis=1)
    highlighted = np.flatnonzero(errors > 45)
    if len(highlighted) != 2:
        return None
    occupied = [symbols[i] for i in highlighted if symbols[i] != "."]
    if len(occupied) == 1:
        return not occupied[0].isupper()
    return None


class Recognizer:
    def __init__(self):
        self.session = None

    def load(self):
        if self.session is None:
            import onnxruntime as ort
            options = ort.SessionOptions()
            options.intra_op_num_threads = 2
            options.inter_op_num_threads = 1
            model = Path(__file__).parent / "assets/models/chess-tiles-v2.onnx"
            self.session = ort.InferenceSession(str(model), sess_options=options,
                                               providers=["CPUExecutionProvider"])

    def read(self, image, white_bottom=None):
        self.load()
        # Match upstream luma and bilinear sampling; batch order is A1..H8.
        gray = image[...,2].astype(np.float32)*.299 + image[...,1].astype(np.float32)*.587 + image[...,0].astype(np.float32)*.114
        board = cv2.resize(gray, (256,256), interpolation=cv2.INTER_LINEAR) / 255
        tiles = board.reshape(8,32,8,32).transpose(0,2,1,3)[::-1].reshape(64,1024).copy()
        output = self.session.run(["probs"], {"tiles": tiles})[0]
        probabilities = output.reshape(8,8,13)[::-1].reshape(64,13).copy()
        symbols = [LABELS[index] for index in probabilities.argmax(1)]
        return Read(symbols, probabilities.max(1), probabilities,
                    orientation(symbols) if white_bottom is None else white_bottom,
                    last_move_turn(image, symbols), image)

    def read_candidate(self,image,detection):
        d=detection
        crop=image[d.y:d.y+d.size,d.x:d.x+d.size]
        if crop.shape[:2]!=(d.size,d.size) or not complete_grid(crop):return None
        result=self.read(crop)
        result.detection=d
        if not result.reliable:
            refined=refine_grid(image,d)
            if refined!=d:
                crop=image[refined.y:refined.y+refined.size,refined.x:refined.x+refined.size]
                if complete_grid(crop):
                    alternative=self.read(crop)
                    alternative.detection=refined
                    if alternative.reliable or alternative.confidence.mean()>result.confidence.mean():result=alternative
        return result

    def scan(self, image, hint=None, cancelled=None):
        self._scan_candidates=[]
        # A screenshot containing exactly the board has no outside border for
        # the grid finder to vote on. Validate and read its complete 8x8 grid.
        if image.shape[0] == image.shape[1] and complete_grid(image):
            result = self.read(image)
            if result.reliable:
                try:
                    position_from_read(result)
                    result.detection = Detection(0,0,image.shape[0],1.)
                    return result
                except ValueError:
                    pass
        if hint:
            x,y,size = hint
            if min(x,y) >= 0 and x+size <= image.shape[1] and y+size <= image.shape[0]:
                crop = image[y:y+size,x:x+size]
                if complete_grid(crop):
                    result = self.read(crop)
                    if result.reliable:
                        result.detection = Detection(x,y,size,1.)
                        return result
        search = image.copy()
        for _ in range(3):
            best, quality = None, -1
            candidates = grid_candidates(search, cancelled=cancelled,limit=32 if getattr(self,"_collect_multiple",False) else 8)
            self._scan_candidates=candidates
            for detection in candidates:
                if cancelled and cancelled.is_set():
                    return None
                x,y,size = detection.x,detection.y,detection.size
                crop = image[y:y+size,x:x+size]
                if crop.shape[:2] != (size,size):
                    continue
                if not complete_grid(crop):
                    continue
                result = self.read_candidate(image,detection)
                if result is None:continue
                # Missing a border file often yields many confident empty
                # squares. Grid coverage must outweigh that artificial gain.
                score = float(result.confidence.mean()) + .30*detection.score + .00001*size
                if result.reliable and score > quality:
                    try:
                        position_from_read(result)
                    except ValueError:
                        continue
                    best, quality = result, score
            if best:
                return best
            if not candidates:
                break
            # Empty decorative boards and this app's mirror must not hide a
            # smaller populated board elsewhere in the same screenshot.
            for d in candidates:
                search[d.y:d.y+d.size,d.x:d.x+d.size] = (24,30,36)
        return None

    def scan_all(self,image,cancelled=None,limit=3):
        self._collect_multiple=True
        try:
            first=self.scan(image,cancelled=cancelled)
        finally:
            self._collect_multiple=False
        if first is None:return []
        reads=[first]
        candidates=getattr(self,'_scan_candidates',[])
        # Most candidates are shifted versions of the same grid. Accept only
        # separate complete boards, regardless of whether their FENs match.
        for d in candidates:
            if len(reads)>=limit or (cancelled and cancelled.is_set()):break
            if any(board_overlap(d,r.detection)>.35 for r in reads):continue
            read=self.read_candidate(image,d)
            if read is None:continue
            if not read.reliable:continue
            try:position_from_read(read)
            except ValueError:continue
            reads.append(read)
        return sorted(reads,key=lambda r:(r.detection.y//max(1,r.detection.size//2),r.detection.x))


def board_overlap(a,b):
    intersection=max(0,min(a.x+a.size,b.x+b.size)-max(a.x,b.x))*max(0,min(a.y+a.size,b.y+b.size)-max(a.y,b.y))
    return intersection/max(1,min(a.size,b.size)**2)


def position_from_read(read, turn_override=None, previous=None):
    """Recover the visible position. Turn/history metadata is kept when tracked."""
    if getattr(read,'exact_fen',None):
        board=chess.Board(read.exact_fen)
        if turn_override is not None:board.turn=turn_override
        return board,True
    turn = turn_override if turn_override is not None else read.turn_hint
    if read.symbols == ordered_symbols(chess.Board(), read.white_bottom):
        return chess.Board(), True
    rights = "-"
    selected_turn = turn if turn is not None else chess.WHITE
    try:
        board = board_from_symbols(read.symbols, read.white_bottom, selected_turn)
    except ValueError:
        board = board_from_symbols(read.symbols, read.white_bottom, not selected_turn)
        turn = not selected_turn
    # A checked king must belong to the side to move. Never let an invalid turn
    # suppress an otherwise recognized board.
    eligible = []
    for king, rook, flag in ((chess.E1,chess.H1,"K"),(chess.E1,chess.A1,"Q"),
                              (chess.E8,chess.H8,"k"),(chess.E8,chess.A8,"q")):
        color = flag.isupper()
        if board.piece_at(king) == chess.Piece(chess.KING,color) and board.piece_at(rook) == chess.Piece(chess.ROOK,color):
            eligible.append(flag)
    board.set_castling_fen("".join(eligible) or "-")
    if previous is not None:
        board.castling_rights &= previous.castling_rights
    return board, turn is not None
