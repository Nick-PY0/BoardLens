from copy import deepcopy
import chess,chess.engine,pytest
from chess_helper.core import SearchSettings
from chess_helper.engine import EngineJob,summarize
from chess_helper.app import MainWindow

@pytest.mark.parametrize('kind',['maia2','maia3','tiny17'])
def test_prediction_length_changes_real_number_of_provider_calls(monkeypatch,kind):
    job=EngineJob();calls=[]
    def one(engine,board,settings):
        calls.append(board.fen());move=next(iter(board.legal_moves));r=summarize(board,[{'pv':[move]}],'provider',allow_unscored=True);r['elapsed']=0;return r
    monkeypatch.setattr(job,'_search_once',one)
    result=job._search(None,chess.Board(),SearchSettings(engine_kind=kind,prediction_plies=5,prediction_seconds=3))
    assert len(calls)==5 and len(result['lines'][0]['pv_moves'])==5
    assert result['prediction']['completed_plies']==5
    calls.clear();job._search(None,chess.Board(),SearchSettings(engine_kind=kind,prediction_plies=1))
    assert len(calls)==1

def test_reply_budget_stops_new_passes_without_hiding_primary_move(monkeypatch):
    import chess_helper.engine as module
    clock=[0.];calls=[];job=EngineJob();updates=[]
    monkeypatch.setattr(module.time,'monotonic',lambda:clock[0]);job.on_update=lambda r:updates.append(deepcopy(r))
    def one(engine,board,settings):
        calls.append(settings);clock[0]+=.3;r=summarize(board,[{'pv':[next(iter(board.legal_moves))]}],'Maia',allow_unscored=True);r['elapsed']=.3;return r
    monkeypatch.setattr(job,'_search_once',one)
    r=job._search(None,chess.Board(),SearchSettings(engine_kind='maia3',prediction_plies=8,prediction_seconds=.1))
    assert len(calls)==2 and r['prediction']['budget_exhausted']
    assert len(updates[0]['lines'][0]['pv_moves'])==1
    assert all(u['lines'][0]['move']==r['lines'][0]['move'] for u in updates)
    assert calls[1].seconds<=.100001

def test_maia_controls_sync_and_save_without_enabling_fake_depth(qt):
    w=MainWindow()
    try:
        from chess_helper.engine_library import ENTRIES
        for identity in ('maia2','maia3','tiny17'):
            match=next((i for i,e in enumerate(ENTRIES) if e.identity==identity),None)
            if match is None:continue
            w.engine_kind.setCurrentIndex(match)
            w.phone.apply_settings({'prediction_plies':7,'prediction_seconds':1.7})
            s=w.search_settings();assert s.prediction_plies==7 and s.prediction_seconds==1.7
            assert w.prediction_plies.isEnabled() and w.prediction_seconds.isEnabled()
            assert not w.depth.isEnabled()
            if identity.startswith('maia'):assert not w.seconds.isEnabled()
        w.save(quiet=True);w.restore();assert w.search_settings().prediction_plies==7
        values,schema=w.phone.schema();assert values['prediction_seconds']==1.7
        w.predict_continuations.setChecked(False);assert not w.prediction_plies.isEnabled()
    finally:w.close()

def test_phone_does_not_finish_when_only_partial_recommendation_is_ready(qt):
    w=MainWindow()
    try:
        a=w.phone.analysis;a.state={'status':'thinking'};g=a.generation
        a.finish(g,'evaluation',{'lines':[{}]},'',True)
        a.finish(g,'recommendation',{'lines':[{}],'continuation_pending':True},'',False)
        assert a.state['status']=='thinking'
        a.finish(g,'recommendation',{'lines':[{}],'continuation_pending':False},'',True)
        assert a.state['status']=='ready'
    finally:w.close()

def test_reply_failure_retains_valid_primary_recommendation(monkeypatch):
    job=EngineJob();calls=[]
    def one(engine,board,settings):
        calls.append(1)
        if len(calls)>1:raise ValueError('No follow-up move')
        r=summarize(board,[{'pv':[chess.Move.from_uci('e2e4')]}],'bot',allow_unscored=True);r['elapsed']=0;return r
    monkeypatch.setattr(job,'_search_once',one)
    r=job._search(None,chess.Board(),SearchSettings(engine_kind='tiny17'))
    assert r['lines'][0]['move']=='e2e4' and r['prediction']['error']=='No follow-up move'
