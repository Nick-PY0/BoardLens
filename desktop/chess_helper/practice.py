"""Bounded evaluation loss for practice; analysis remains full strength."""
import random

import chess


def choose_practice_line(board, lines, chance=.30, max_loss_cp=40, random_value=None):
    if not lines:
        raise ValueError("Analyze a position before playing it.")
    best=lines[0]
    if best.get("mate") is not None:
        return best
    if (random.random() if random_value is None else random_value) >= chance:
        return best
    direction=1 if board.turn else -1
    candidates=[]
    for line in lines[1:]:
        if line.get("mate") is not None:
            continue
        loss=direction*(best["cp"]-line["cp"])
        if not 2 <= loss <= max_loss_cp:
            continue
        move=chess.Move.from_uci(line["move"])
        if move not in board.legal_moves:
            continue
        after=board.copy()
        after.push(move)
        queen_squares=after.pieces(chess.QUEEN,board.turn)
        # Do not select an alternative that leaves a queen immediately available
        # to a cheaper attacker, even if a shallow search mis-evaluated it.
        hanging=False
        for reply in after.legal_moves:
            attacker=after.piece_at(reply.from_square)
            if reply.to_square in queen_squares and attacker and attacker.piece_type != chess.QUEEN:
                hanging=True
                break
        if not hanging:
            candidates.append(line)
    return random.choice(candidates) if candidates else best
