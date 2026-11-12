from dataclasses import replace
import random
import chess,chess.engine,pytest
from chess_helper.app import MainWindow
from chess_helper import engine_library as library,engine_config
from chess_helper.core import SearchSettings,find_engine
from chess_helper.engine import EngineJob,search_limit
from chess_helper.recommendation_styles import style_index,flounder_index


def test_catalog_capabilities_and_no_automatic_engine_fallback(qt):
    w=MainWindow()
    try:
        assert len(library.ENTRIES)==20
        assert [e.rating for e in library.ENTRIES if e.kind=='tiny']==[192,307,677,1085,1276,1569,1713,2001,2172,2246,2513,2772]
        for index,entry in enumerate(library.ENTRIES):
            w.engine_kind.setCurrentIndex(index)
            if entry.kind=='tiny':
                assert w.multipv.maximum()==1 and not w.depth.isEnabled() and not w.playing_style.isEnabled()
                assert w.search_settings().engine_kind==entry.identity
                with pytest.raises(ValueError):w.analysis_command()
            elif entry.kind in ('maia2','maia3'):
                assert not w.depth.isEnabled() and not w.playing_style.isEnabled()
            assert w.engine_kind.currentIndex()==index
        w.engine_kind.setCurrentIndex(0);w.mode.setCurrentText('Adaptive');w.playing_style.setCurrentText('Aggressive')
        assert w.search_settings().style=='Aggressive' and 'adaptive' in w.limit_label.text()
        w.save();w.close();w=MainWindow()
        assert w.mode.currentText()=='Adaptive' and w.playing_style.currentText()=='Aggressive'
    finally:w.close()


def test_adaptive_limits_respect_both_user_caps():
    for depth in (1,12,60):
        settings=SearchSettings(mode='Adaptive',seconds=.2,depth=depth)
        limit=search_limit(settings,chess.Board())
        assert 0<limit.time<=settings.seconds and 0<limit.depth<=depth


def test_styles_keep_choices_within_half_pawn_and_flounder_returns_existing_candidate():
    board=chess.Board();infos=[{'pv':[chess.Move.from_uci(move)],'score':chess.engine.PovScore(chess.engine.Cp(cp),chess.WHITE)} for move,cp in [('e2e4',50),('d2d4',30),('f2f3',-300)]]
    for style in ('Balanced','Aggressive','Defensive','Human-like','Maximum strength'):
        assert style_index(board,infos,style) in (0,1)
    assert style_index(board,infos,'Human-like')==style_index(board,infos,'Human-like')
    for elo in (600,1500,2400):assert flounder_index(board,infos,elo,random.Random(3)) in range(len(infos))


def test_style_and_adaptive_settings_reach_real_search():
    path=find_engine()
    if not path:pytest.skip('Stockfish not installed')
    settings=SearchSettings(mode='Adaptive',seconds=.2,depth=14,multipv=3,style='Aggressive')
    result=EngineJob().run(path,chess.Board(),settings)
    assert result['configuration']['style']=='Aggressive' and result['limits']['effective_depth']<=14
    assert len(result['lines'])==3 and result['recommendation_type']=='style-ranked recommendation'
    assert result['evaluation']['cp'] is not None
