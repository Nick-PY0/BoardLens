import json,threading,time,urllib.request,urllib.error
from concurrent.futures import ThreadPoolExecutor
import chess
import chess.engine
import pytest
from chess_helper.app import MainWindow
from chess_helper.phone_server import PhoneServer


def request(server,path,body=None,token=None):
    headers={}
    if token:headers['Authorization']='Bearer '+token
    if body is not None:headers['Content-Type']='application/json'
    req=urllib.request.Request(f'http://127.0.0.1:{server.port}'+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=6) as response:return response.status,json.loads(response.read())
    except urllib.error.HTTPError as error:return error.code,json.loads(error.read())


def test_pairing_authentication_state_and_commands():
    calls=[];server=PhoneServer(lambda data:calls.append(data) or 'done',port=0,host='127.0.0.1')
    try:
        server.publish({'boards':[{'id':'primary'}]})
        assert request(server,'/api/health')[1]['app']=='BoardLens'
        assert request(server,'/api/state')[0]==401
        assert request(server,'/api/pair',{'code':'wrong'})[0]==403
        status,paired=request(server,'/api/pair',{'code':server.code})
        assert status==200 and len(paired['token'])>30
        token=paired['token']
        assert request(server,'/api/state',token=token)[1]['boards']==[{'id':'primary'}]
        assert request(server,'/api/command',{'command':'stop'},token)[0]==200
        assert calls==[{'command':'stop'}]
        assert request(server,'/api/command',{'command':'stop'},'bad-token')[0]==401
        assert len(calls)==1
    finally:server.close()


def test_pairing_rate_limit_and_static_path_whitelist():
    server=PhoneServer(lambda data:None,port=0,host='127.0.0.1')
    try:
        for _ in range(8):assert request(server,'/api/pair',{'code':'wrong'})[0]==403
        assert request(server,'/api/pair',{'code':server.code})[0]==429
        assert request(server,'/../../core.py')[0]==404
        with urllib.request.urlopen(f'http://127.0.0.1:{server.port}/') as response:
            assert b'BoardLens Companion' in response.read()
    finally:server.close()


def through_qt(qt,callback):
    with ThreadPoolExecutor(1) as pool:
        future=pool.submit(callback);deadline=time.monotonic()+6
        while not future.done() and time.monotonic()<deadline:qt.processEvents();time.sleep(.005)
        return future.result(timeout=1)


def test_real_http_commands_update_qt_settings_and_stop(qt):
    w=MainWindow();w.phone.start(0,host='127.0.0.1');server=w.phone.server
    try:
        token=request(server,'/api/pair',{'code':server.code})[1]['token']
        status,response=through_qt(qt,lambda:request(server,'/api/command',{'command':'settings','data':{'seconds':1.5,'multipv':2,'stick_to_move':True}},token))
        assert status==200 and w.seconds.value()==1.5 and w.multipv.value()==2 and w.stick_to_move.isChecked()
        old=w.seconds.value()
        status,_=through_qt(qt,lambda:request(server,'/api/command',{'command':'settings','data':{'seconds':2.5,'threads':999999}},token))
        assert status==400 and w.seconds.value()==old
        w._monitoring=True;w.live_button.setChecked(True)
        status,_=through_qt(qt,lambda:request(server,'/api/command',{'command':'stop'},token))
        assert status==200 and not w._monitoring and not w.live_button.isChecked()
        state=request(server,'/api/state',token=token)[1]
        assert state['settings']['seconds']==1.5 and 'svg' in state['boards'][0]
    finally:w.close()


def test_phone_practice_moves_are_legal_and_stale_actions_are_rejected(qt):
    w=MainWindow();phone=w.phone
    phone.execute({'command':'practice_move','data':{'fen':chess.STARTING_FEN,'move':'e2e4'}})
    assert not w.tracker.board.turn
    with pytest.raises(ValueError):phone.execute({'command':'practice_move','data':{'fen':chess.STARTING_FEN,'move':'d2d4'}})
    w.source.blockSignals(True);w.source.setCurrentIndex(1);w.source.blockSignals(False)
    with pytest.raises(ValueError):phone.execute({'command':'auto_move','data':{'enabled':True}})
    w.close()


def test_phone_shares_three_independent_boards_and_visible_candidate_ranks(qt,monkeypatch,render_board):
    from PySide6.QtGui import QGuiApplication
    from chess_helper.capture import screen_key
    from chess_helper.engine import summarize
    from chess_helper.recognition import Recognizer
    from chess_helper.vision import Detection
    w=MainWindow();w.source.blockSignals(True);w.source.setCurrentIndex(1);w.source.blockSignals(False)
    w._monitoring=True;monkeypatch.setattr(w,'suggest',lambda **kw:None);monkeypatch.setattr(w.multi,'search',lambda state:None)
    batch=[]
    for index in range(3):
        read=Recognizer().read(render_board(chess.Board()));read.detection=Detection(30+index*560,100,512,1.)
        batch.append((screen_key(QGuiApplication.primaryScreen()),'QA display',read,1800,800))
    try:
        for _ in range(2):w.live_finished(w._live_token,batch,'')
        result=summarize(w.tracker.board,[{'pv':[chess.Move.from_uci(move)],'score':chess.engine.PovScore(chess.engine.Cp(30),chess.WHITE)} for move in ('e2e4','d2d4')],'QA')
        w.result=result;w.render_result(result)
        for state in w.multi.states:w.multi.finished(state,state.generation,result,'',False)
        w.rank_best.setChecked(False)
        snapshot=w.phone.snapshot()
        assert len(snapshot['boards'])==3 and len({b['id'] for b in snapshot['boards']})==3
        assert all(b['lines'][0]['rank']==2 and b['lines'][0]['move']=='d2d4' for b in snapshot['boards'])
        assert all(b['turn_override']==0 and '<svg' in b['svg'] for b in snapshot['boards'])
        for _ in range(3):w.live_finished(w._live_token,batch[:1],'')
        assert len(w.phone.snapshot()['boards'])==1
    finally:w.close()


def test_phone_screenshot_import_and_settings_validation(qt,monkeypatch):
    import base64
    from pathlib import Path
    w=MainWindow();monkeypatch.setattr(w,'suggest',lambda **kw:None)
    try:
        image=(Path(__file__).parent/'fixtures/chesscom-starting-layout-nov10.png').read_bytes()
        w.phone.execute({'command':'screenshot','data':{'image':base64.b64encode(image).decode()}})
        assert w.source.currentIndex()==2 and w.tracker.board.fen()==chess.STARTING_FEN
        assert len(w.phone.snapshot()['boards'])==1
        with pytest.raises(ValueError):w.phone.apply_settings({'threads':1.5})
        with pytest.raises(ValueError):w.phone.apply_settings({'seconds':float('nan')})
        with pytest.raises(ValueError):w.phone.apply_settings({'only_my_color':True,'orientation':1})
    finally:w.close()


def test_move_preset_updates_arrow_count_and_visibility(qt):
    w=MainWindow()
    try:
        for count in (1,2,3,5):
            w.recommendation_preset(count)
            assert w.multipv.value()==count and w.arrow_count.value()==count
            assert w.rank_best.isChecked() and w.rank_second.isChecked()==(count>=2)
            assert w.rank_others.isChecked()==(count>=3)
        values,schema=w.phone.schema()
        assert not {'move_delay','inaccuracy_chance','inaccuracy_loss','practice_strength','side'}&set(values)
    finally:w.close()
