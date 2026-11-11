"""Legal-capture threat estimates, separate from engine move recommendations."""
from functools import lru_cache
import chess
VALUES={chess.PAWN:100,chess.KNIGHT:320,chess.BISHOP:330,chess.ROOK:500,chess.QUEEN:900,chess.KING:20000}


def exchange_gain(board,square,depth=6,_budget=None):
    if _budget is None:_budget=[256]
    _budget[0]-=1
    if depth<=0 or _budget[0]<0:return 0
    best=0
    for move in board.generate_legal_captures():
        if move.to_square!=square:continue
        target=board.piece_at(square)
        if target is None or target.piece_type==chess.KING:continue
        gain=VALUES[target.piece_type]+(VALUES[move.promotion]-100 if move.promotion else 0)
        probe=board.copy(stack=False);probe.push(move)
        best=max(best,gain-exchange_gain(probe,square,depth-1,_budget))
    return best


@lru_cache(maxsize=48)
def analyze(fen):
    board=chess.Board(fen);hanging=[];mates=[]
    if not board.is_valid():return {'hanging':[],'mates':[],'attacks':{True:[],False:[]}}
    for square,piece in board.piece_map().items():
        if piece.piece_type==chess.KING or not board.is_attacked_by(not piece.color,square):continue
        probe=board.copy(stack=False)
        if probe.turn==piece.color:probe.turn=not piece.color;probe.ep_square=None
        gain=exchange_gain(probe,square)
        if gain>0:hanging.append({'square':square,'color':piece.color,'piece':chess.piece_name(piece.piece_type),'loss':gain,
            'text':f"{'White' if piece.color else 'Black'} {chess.piece_name(piece.piece_type)} on {chess.square_name(square)} can lose material in a capture sequence."})
    if not board.is_game_over():
        for move in board.legal_moves:
            probe=board.copy(stack=False);probe.push(move)
            if probe.is_checkmate():mates.append({'move':move.uci(),'square':move.to_square,'color':board.turn,'text':f"{'White' if board.turn else 'Black'} has mate in one: {board.san(move)}."})
    return {'hanging':sorted(hanging,key=lambda p:p['loss'],reverse=True),'mates':mates,
            'attacks':{color:sorted(set().union(*(set(board.attacks(s)) for s,p in board.piece_map().items() if p.color==color))) for color in (True,False)}}


def presentation(board,bottom,enabled=False,attacked=False,mates=True):
    if not enabled or not board.is_valid():return [],[]
    report=analyze(board.fen());marks=[];messages=[]
    if attacked:marks.extend({'square':s,'color':'#ff8c73','kind':'attack'} for s in report['attacks'][not bottom])
    for item in report['hanging']:
        marks.append({'square':item['square'],'color':'#ff7185','kind':'hanging'});messages.append(item['text'])
    if mates:
        for item in report['mates']:
            marks.append({'square':item['square'],'color':'#c89bff','kind':'mate'});messages.append(item['text'])
    return marks,messages
