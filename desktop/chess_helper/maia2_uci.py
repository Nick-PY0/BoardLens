"""Small UCI adapter for the official optional Maia-2 package."""
from __future__ import annotations
import argparse,contextlib,math,sys

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--model-dir',required=True);parser.add_argument('--cache',action='store_true');args=parser.parse_args()
    import chess
    import torch
    torch.set_num_threads(1)
    from maia2 import model,inference
    loaded=None;prepared=None;board=chess.Board();elo=1500;count=3
    def load():
        nonlocal loaded,prepared
        if loaded is None:
            with contextlib.redirect_stdout(sys.stderr):loaded=model.from_pretrained(type='rapid',device='cpu',save_root=args.model_dir);prepared=inference.prepare()
    if args.cache:load();return
    for line in sys.stdin:
        words=line.strip().split()
        if not words:continue
        if words[0]=='uci':
            print('id name Maia-2 Rapid / BoardLens adapter\noption name Elo type spin default 1500 min 600 max 2600\noption name Temperature type spin default 0 min 0 max 0\noption name MultiPV type spin default 3 min 1 max 10\nuciok',flush=True)
        elif words[0]=='isready':load();print('readyok',flush=True)
        elif words[0]=='ucinewgame':board=chess.Board()
        elif words[0]=='setoption':
            name=' '.join(words[2:words.index('value')]).lower();value=words[words.index('value')+1]
            if name=='elo':elo=int(value)
            elif name=='multipv':count=int(value)
        elif words[0]=='position':
            at=2 if words[1]=='startpos' else 8
            board=chess.Board() if words[1]=='startpos' else chess.Board(' '.join(words[2:8]))
            if at<len(words) and words[at]=='moves':
                for move in words[at+1:]:board.push_uci(move)
        elif words[0]=='go':
            load()
            with contextlib.redirect_stdout(sys.stderr):probabilities,expected=inference.inference_each(loaded,prepared,board.fen(),elo,elo)
            ranked=[move for move in probabilities if chess.Move.from_uci(move) in board.legal_moves]
            expected=max(.0001,min(.9999,float(expected)));cp=round(400*math.log(expected/(1-expected)))
            if not board.turn:cp=-cp
            for rank,move in enumerate(ranked[:count],1):print(f'info depth 1 multipv {rank} score cp {cp} pv {move}',flush=True)
            print('info string White expected score '+str(expected),flush=True)
            print('bestmove '+(ranked[0] if ranked else '0000'),flush=True)
        elif words[0] in ('stop','quit'):return

if __name__=='__main__':main()
