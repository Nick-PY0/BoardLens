import time
import chess,chess.engine,pytest
from PySide6.QtTest import QTest
from chess_helper.app import MainWindow
from chess_helper import engine_config
from chess_helper.engine import EngineJob,summarize


def test_phone_positions_do_not_change_desktop_game_or_settings(qt,monkeypatch):
    calls=[]
    monkeypatch.setattr(engine_config,'command',lambda w,index=None:'fake')
    def run(job,path,board,settings):
        calls.append(settings);move=next(iter(board.legal_moves));return summarize(board,[{'pv':[move],'score':chess.engine.PovScore(chess.engine.Cp(13),True)}],'provider')
    monkeypatch.setattr(EngineJob,'run',run)
    w=MainWindow()
    try:
        before=(w.tracker.board.fen(),w.engine_kind.currentIndex(),w.seconds.value(),w.eval_engine.currentIndex())
        board=chess.Board();board.push_san('e4')
        response=w.phone.execute({'command':'analyze_phone','data':{'request_id':'phone-1','fen':board.fen(),'engine':'tiny17','evaluator':'stockfish','seconds':.2,'moves':3,'predict':True}})
        for _ in range(50):
            QTest.qWait(10)
            if w.phone.analysis.state.get('status')=='ready':break
        assert response['accepted'] and w.phone.analysis.state['status']=='ready'
        assert (w.tracker.board.fen(),w.engine_kind.currentIndex(),w.seconds.value(),w.eval_engine.currentIndex())==before
        recommendation=next(s for s in calls if s.engine_id=='tiny17');evaluation=next(s for s in calls if s.engine_id=='stockfish')
        assert recommendation.multipv==1 and recommendation.predict_continuations
        assert evaluation.strength=='Full strength' and not evaluation.predict_continuations
        assert evaluation.seconds==.3
        generation=w.phone.analysis.generation
        w.phone.execute({'command':'cancel_phone','data':{'request_id':'different-device'}})
        assert w.phone.analysis.generation==generation
    finally:w.close()


def test_bad_phone_requests_rejected_before_starting_jobs(qt,monkeypatch):
    monkeypatch.setattr(engine_config,'command',lambda w,index=None:'fake');w=MainWindow()
    try:
        base={'request_id':'phone','fen':chess.Board().fen()}
        for bad in ({'engine':'unknown'},{'evaluator':'tiny17'},{'seconds':-1},{'moves':99},{'seconds':float('nan')},{'predict':'yes'}):
            with pytest.raises(ValueError):w.phone.analysis.request(dict(base,**bad))
        assert not w.phone.analysis.jobs
    finally:w.close()


def test_phone_position_poll_is_authenticated_and_omits_board_images():
    import json,urllib.request,urllib.error
    from chess_helper.phone_server import PhoneServer
    server=PhoneServer(lambda data:None,port=0,host='127.0.0.1')
    try:
        server.publish({'boards':[{'svg':'large board image'}],'phone_analysis':{'request_id':'one','status':'thinking'}})
        url=f'http://127.0.0.1:{server.port}/api/phone-position'
        with pytest.raises(urllib.error.HTTPError) as denied:urllib.request.urlopen(url)
        assert denied.value.code==401
        request=urllib.request.Request(url,headers={'Authorization':'Bearer '+server.token})
        with urllib.request.urlopen(request) as response:value=json.load(response)
        assert value=={'phone_analysis':{'request_id':'one','status':'thinking'}}
    finally:server.close()
