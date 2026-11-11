from copy import deepcopy
import chess,chess.engine
from chess_helper.app import MainWindow
from chess_helper.core import SearchSettings
from chess_helper.engine import EngineJob,summarize


def test_one_move_providers_publish_then_append_two_legal_predictions(monkeypatch):
    job=EngineJob();calls=[];updates=[];job.on_update=lambda value:updates.append(deepcopy(value))
    def one(engine,board,settings):
        calls.append(board.fen());move=next(iter(board.legal_moves))
        result=summarize(board,[{'pv':[move],'score':chess.engine.PovScore(chess.engine.Cp(17),board.turn)}],'single move provider')
        result['elapsed']=.01
        return result
    monkeypatch.setattr(job,'_search_once',one)
    board=chess.Board();result=job._search(None,board,SearchSettings())
    assert len(calls)==3 and len(updates[0]['lines'][0]['pv_moves'])==1
    assert len(result['lines'][0]['pv_moves'])==3
    assert all(u['lines'][0]['move']==result['lines'][0]['move'] for u in updates)
    probe=board.copy()
    for uci in result['lines'][0]['pv_moves']:
        move=chess.Move.from_uci(uci);assert move in probe.legal_moves;probe.push(move)
    assert result['lines'][0]['future_simple'] and result['lines'][0]['reply_simple']


def test_continuation_cancellation_does_not_search_future_positions(monkeypatch):
    job=EngineJob();calls=[]
    def one(engine,board,settings):
        calls.append(1);r=summarize(board,[{'pv':[chess.Move.from_uci('e2e4')],'score':chess.engine.PovScore(chess.engine.Cp(1),True)}],'test');r['elapsed']=0;return r
    monkeypatch.setattr(job,'_search_once',one);job.on_update=lambda _:job.cancel()
    assert job._search(None,chess.Board(),SearchSettings()) is None and calls==[1]


def test_bar_uses_its_own_provider_and_limits(qt):
    w=MainWindow()
    try:
        w.engine_kind.setCurrentIndex(1) # Maia recommendations, Stockfish evaluator
        w.eval_seconds.setValue(.4);w.eval_depth.setValue(14)
        index,entry,settings=w.evaluations.profile()
        assert entry.identity=='stockfish' and settings.seconds==.4 and settings.depth==14
        assert settings.strength=='Full strength' and not settings.predict_continuations
        board=chess.Board();recommendation={'fen':board.fen(),'engine':'Maia','lines':[{'cp':900,'mate':None,'score':'+9.00'}]}
        assert w.evaluations.score(board,recommendation)['cp'] is None
        w.evaluations.cache[board.fen()]={'fen':board.fen(),'engine':'Stockfish','lines':[{'cp':24,'mate':None,'score':'+0.24'}]}
        assert w.evaluations.score(board,recommendation)['cp']==24
        w.stop();assert not w.evaluations.cache
    finally:w.close()
