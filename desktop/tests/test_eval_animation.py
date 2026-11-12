import math
from chess_helper.widgets import EvalBar
from chess_helper.app import MainWindow
from chess_helper.engine_library import ENTRIES


def test_evaluation_retargets_from_visible_fill_and_preserves_it_while_pending(qt):
    bar=EvalBar()
    bar.cp=400;bar.update();bar._animation.setCurrentTime(200)
    previous=bar._fraction
    assert previous>.8
    bar.cp=None;bar.update()
    assert bar._fraction==previous and bar._target==previous
    bar.cp=-400;bar.update()
    assert bar._animation.startValue()==previous
    bar._animation.setCurrentTime(100)
    assert bar._target<bar._fraction<previous
    visible=bar._fraction
    bar.cp=200;bar.update()
    assert bar._animation.startValue()==visible
    bar._animation.setCurrentTime(200)
    assert math.isclose(bar._fraction,1/(1+math.exp(-200/220)))


def test_refresh_retains_last_evaluation_and_controls_match_each_engine(qt):
    w=MainWindow()
    try:
        w.eval_bar.cp=125;w.eval_bar.update();w.invalidate()
        assert w.eval_bar.cp==125
        for index,entry in enumerate(ENTRIES):
            w.engine_kind.setCurrentIndex(index)
            if entry.kind in ('maia2','maia3'):
                assert not w.seconds.isEnabled() and not w.depth.isEnabled()
            elif entry.kind=='tiny':
                assert w.seconds.isEnabled() and not w.depth.isEnabled()
                w.seconds.setValue(.7)
                assert w.search_settings().seconds==.7
            else:
                w.mode.setCurrentText('Time + depth')
                assert w.seconds.isEnabled() and w.depth.isEnabled()
                w.seconds.setValue(.8);w.depth.setValue(14)
                s=w.search_settings();assert s.seconds==.8 and s.depth==14
    finally:w.close()
