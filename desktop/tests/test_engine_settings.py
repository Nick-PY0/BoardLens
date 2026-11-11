import time

import chess
import pytest
from PySide6.QtTest import QTest

from chess_helper.app import MainWindow
from chess_helper.core import SearchSettings,find_engine
from chess_helper.engine import EngineJob,EngineSession


def test_real_engine_obeys_time_depth_combined_threads_hash_and_pv():
    path=find_engine()
    if not path:pytest.skip('Stockfish not installed')
    session=EngineSession();measurements={}
    # Load once, so process startup does not get counted as thinking time.
    session.get(path)
    def search(name,settings):
        job=EngineJob();job.session=session
        started=time.monotonic();result=job.run(path,chess.Board(),settings)
        elapsed=time.monotonic()-started
        measurements[name]=(elapsed,result['lines'][0]['depth'])
        return elapsed,result
    try:
        short,_=search('time .25',SearchSettings(seconds=.25,threads=1,hash_mb=32,multipv=1))
        assert .22<=short<1.5
        assert session.engine.protocol.config['Threads']==1
        assert session.engine.protocol.config['Hash']==32
        long,result=search('time 1.0',SearchSettings(seconds=1.,threads=2,hash_mb=64,multipv=3))
        assert .9<=long<2.5 and long>short+.5
        assert len(result['lines'])==3
        assert session.engine.protocol.config['Threads']==2
        assert session.engine.protocol.config['Hash']==64
        elapsed,result=search('depth 6',SearchSettings(mode='Depth',seconds=10,depth=6,multipv=2))
        assert result['lines'][0]['depth']==6 and elapsed<2
        elapsed,result=search('combined depth first',SearchSettings(mode='Time + depth',seconds=4,depth=8))
        assert result['lines'][0]['depth']==8 and elapsed<2
        elapsed,result=search('combined time first',SearchSettings(mode='Time + depth',seconds=.3,depth=60))
        assert .27<=elapsed<1.5 and result['lines'][0]['depth']<60
        print('Actual Stockfish limits:',measurements)
    finally:session.close()


def test_gui_early_arrows_do_not_shorten_selected_engine_time(qt):
    window=MainWindow()
    if not window.engine_path.text():
        window.close();pytest.skip('Stockfish not installed')
    window.seconds.setValue(.8)
    window.depth.setValue(22)
    window.threads.setValue(1)
    window.multipv.setValue(2)
    window.hash_mb.setValue(32)
    settings=window.search_settings()
    assert (settings.seconds,settings.depth,settings.threads,settings.multipv,settings.hash_mb)==(.8,22,1,2,32)
    window.suggest();started=time.monotonic()
    while window.result is None and time.monotonic()-started<.65:
        qt.processEvents();time.sleep(.01)
    assert window.result and window.result['provisional'] and window.job is not None
    while window.job is not None and time.monotonic()-started<3:
        qt.processEvents();time.sleep(.01)
    assert not window.result['provisional'] and time.monotonic()-started>=.75
    window.early_suggestions.setChecked(False)
    window.seconds.setValue(.5)
    window.suggest()
    started=time.monotonic()
    while time.monotonic()-started<.2:qt.processEvents();time.sleep(.01)
    assert window.result is None and window.job is not None
    while window.job is not None and time.monotonic()-started<2:qt.processEvents();time.sleep(.01)
    assert window.result and not window.result['provisional']
    window.close()


def test_auto_suggest_never_plays_practice_moves(qt):
    window=MainWindow()
    try:
        window.seconds.setValue(.1);window.multipv.setValue(1)
        window.live_button.setChecked(True);window.toggle_live(True)
        started=time.monotonic()
        while time.monotonic()-started<.6:qt.processEvents();time.sleep(.01)
        assert not window.tracker.board.move_stack
        assert not hasattr(window,'auto_button') and not hasattr(window,'move_delay')
        assert 'automove' not in window.key_fields
    finally:window.close()
