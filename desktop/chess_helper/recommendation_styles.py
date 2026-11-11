"""Explicit recommendation ranking; these are GUI styles, not native personas."""
import hashlib,math,random
import chess

# Adapted from Blundermind src/40-engines.js (GPL-3.0), by bhale22.
# Calibration used its Stockfish build; BoardLens uses the selected local build.
LADDER=[(600,.1196),(732,.1133),(884,.1065),(1118,.1001),(1289,.0941),(1559,.0885),(1696,.0832),(1959,.0782),(2204,.0735),(2387,.0691)]

def flounder_index(board,infos,elo,rng=None):
    rng=rng or random.Random()
    e=max(600,min(2400,elo));a,b=LADDER[0],LADDER[1]
    for left,right in zip(LADDER,LADDER[1:]):
        if left[0]<=e:a,b=left,right
    scale=math.exp(math.log(a[1])+(e-a[0])/(b[0]-a[0])*(math.log(b[1])-math.log(a[1])))
    shape=max(.28,min(.55,.436+(e-1600)*.00007))
    scores=[info['score'].pov(board.turn).score(mate_score=100000) for info in infos]
    perceived=lambda value:math.copysign(math.log1p(abs(value)/100),value)
    best=perceived(max(scores));cost=[best-perceived(value) for value in scores]
    target=scale*(-math.log(max(1e-12,1-rng.random())))**(1/shape)
    eligible=[i for i,value in enumerate(cost) if value<=target+.5]
    return min(eligible,key=lambda i:abs(cost[i]-target))

def style_index(board,infos,style):
    if style in ('Balanced','Maximum strength') or len(infos)<2:return 0
    if any('score' not in info for info in infos):return 0
    scores=[info['score'].pov(board.turn).score(mate_score=100000) for info in infos]
    best=max(scores);eligible=[i for i,value in enumerate(scores) if best-value<=50]
    if style=='Human-like':
        seed=int.from_bytes(hashlib.sha256((board.fen()+style).encode()).digest()[:8],'big')
        return random.Random(seed).choices(eligible,weights=[math.exp((scores[i]-best)/35) for i in eligible])[0]
    values={1:100,2:320,3:330,4:500,5:900,6:0}
    def bonus(index):
        move=infos[index]['pv'][0];after=board.copy();after.push(move)
        if style=='Aggressive':
            capture=board.piece_at(move.to_square)
            return (25 if after.is_check() else 0)+(min(20,values[capture.piece_type]/30) if capture else 0)+len(after.attackers(board.turn,after.king(not board.turn)))*4
        if style=='Defensive':
            piece=board.piece_at(move.from_square)
            escape=board.is_attacked_by(not board.turn,move.from_square) and not after.is_attacked_by(not board.turn,move.to_square)
            return (25 if escape and piece and piece.piece_type!=chess.PAWN else 0)+(20 if board.is_castling(move) else 0)
        return 0
    return max(eligible,key=lambda i:scores[i]+bonus(i))
