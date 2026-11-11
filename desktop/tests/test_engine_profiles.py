import time
from dataclasses import replace
import chess,chess.engine,pytest
from PySide6.QtCore import QRectF,Qt
from PySide6.QtGui import QImage,QPainter
from chess_helper.app import MainWindow
from chess_helper.core import SearchSettings,find_engine
from chess_helper.engine import EngineJob,EngineSession,summarize
from chess_helper.overlay import paint_arrows
from chess_helper import engine_config


def test_reply_arrow_is_continuous_by_default_and_dash_is_optional(qt):
    def shaft(dashed):
        image=QImage(640,640,QImage.Format.Format_ARGB32);image.fill(Qt.GlobalColor.transparent)
        painter=QPainter(image);paint_arrows(painter,QRectF(0,0,640,640),True,[{'move':chess.Move.from_uci('c6c5'),'color':'#53e2e4','reply':True,'dashed':dashed}]);painter.end()
        return [image.pixelColor(200,y).alpha() for y in range(205,260)]
    assert min(shaft(False))>100
    assert min(shaft(True))==0


def test_real_strength_options_affect_chosen_recommendation_and_reset_to_full():
    path=find_engine()
    if not path:pytest.skip('Stockfish not installed')
    session=EngineSession()
    try:
        for settings in (SearchSettings(seconds=.15,skill=5,strength='Skill level'),SearchSettings(seconds=.15,elo=1500,strength='Elo rating')):
            job=EngineJob();job.session=session;updates=[];job.on_update=updates.append
            result=job.run(path,chess.Board(),settings)
            assert result['lines'][0]['move']==result['chosen_move']
            assert result['recommendation_type']=='strength-limited choice'
            # The chosen root stays fixed while later predictions are appended.
            assert all(update['chosen_move']==result['chosen_move'] for update in updates)
            config=session.engine.protocol.config
            if settings.strength=='Skill level':assert config['Skill Level']==5 and not config['UCI_LimitStrength']
            else:assert config['UCI_Elo']==1500 and config['UCI_LimitStrength']
        job=EngineJob();job.session=session;job.run(path,chess.Board(),SearchSettings(seconds=.1))
        assert session.engine.protocol.config['Skill Level']==20 and not session.engine.protocol.config['UCI_LimitStrength']
    finally:session.close()


def test_manual_engine_controls_configuration_and_missing_engine_do_not_fallback(qt):
    w=MainWindow()
    try:
        w.strength_mode.setCurrentText('Skill level');w.engine_skill.setValue(10);w.multipv.setValue(5)
        assert 'Skill 10/20' in w.engine_summary.text()
        assert w.search_settings().skill==10 and w.search_settings().multipv==5
        assert '"skill": 10' in engine_config.configuration(w)
        w.engine_kind.setCurrentIndex(1)
        assert w.search_settings().engine_kind=='maia3' and w.human_elo.isEnabled()
        assert not w.depth.isEnabled() and not w.seconds.isEnabled()
        with pytest.raises(ValueError):w.analysis_command()
        assert w.engine_kind.currentIndex()==1
        w.engine_kind.setCurrentIndex(2)
        with pytest.raises(ValueError):w.analysis_command()
        assert w.engine_kind.currentIndex()==2
    finally:w.close()


def test_engine_change_releases_old_move_lock_and_phone_exposes_profiles(qt):
    w=MainWindow()
    try:
        w.stick_to_move.setChecked(True)
        w.result=summarize(w.tracker.board,[{'pv':[chess.Move.from_uci('e2e4')],'score':chess.engine.PovScore(chess.engine.Cp(30),chess.WHITE)}],'QA')
        w.render_result(w.result);assert w._pinned_result
        w.engine_skill.setValue(10)
        assert w._pinned_result is None and w.result is None
        w.phone.apply_settings({'engine_kind':1,'human_elo':1700})
        values,schema=w.phone.schema()
        assert values['engine_kind']==1 and values['human_elo']==1700
        assert {'strength_mode','compare_a','compare_b','compare_c','dashed_reply'}<={item['key'] for item in schema}
    finally:w.close()


def test_comparison_runs_independently_and_stop_prevents_restart(qt):
    w=MainWindow()
    if not w.engine_path.text():w.close();pytest.skip('Stockfish not installed')
    try:
        w.seconds.setValue(.15);w.strength_mode.setCurrentText('Skill level');w.engine_skill.setValue(5)
        w.compare_a.setCurrentIndex(0);w.compare_b.setCurrentIndex(1)
        w.open_engine_comparison(show=False);comparison=w.comparison
        end=time.monotonic()+5
        while comparison.jobs and time.monotonic()<end:qt.processEvents();time.sleep(.01)
        assert not comparison.jobs and len(comparison.results)==2
        assert all(item['result'] for item in comparison.results)
        assert comparison.results[0]['result']['recommendation_type']=='best moves'
        assert comparison.results[1]['result']['recommendation_type']=='strength-limited choice'
        assert w.result is None and w.engine_kind.currentIndex()==0
        w.stop();assert not comparison.following
        assert w.phone.snapshot()['comparison']['engines'][0]['result']
        w.tracker.board.push_uci('e2e4');comparison.poll()
        assert not comparison.jobs and comparison.snapshot() is None
    finally:w.close()


def test_selected_engine_and_strength_preferences_persist_without_auto_switch(qt):
    w=MainWindow();w.engine_kind.setCurrentIndex(1);w.human_elo.setValue(1700)
    w.strength_mode.setCurrentText('Elo rating');w.engine_elo.setValue(1800);w.engine_skill.setValue(10)
    w.compare_a.setCurrentIndex(1);w.compare_b.setCurrentIndex(2);w.compare_c.setCurrentIndex(1)
    w.dashed_reply.setChecked(True);w.save();w.close()
    restored=MainWindow()
    try:
        assert restored.engine_kind.currentIndex()==1 and restored.human_elo.value()==1700
        assert restored.strength_mode.currentText()=='Elo rating' and restored.engine_elo.value()==1800
        assert restored.compare_a.currentIndex()==1 and restored.compare_c.currentIndex()==1
        assert restored.dashed_reply.isChecked()
        restored.engine_kind.setCurrentIndex(0)
        assert restored.search_settings().strength=='Elo rating'
    finally:restored.close()


def test_engine_sidebar_and_new_toggle_fit_without_horizontal_scrolling(qt):
    w=MainWindow();w.resize(1400,900);w.show();w.settings_tabs.setCurrentIndex(1);qt.processEvents()
    try:
        for kind in range(3):
            w.engine_kind.setCurrentIndex(kind)
            for opened in (False,True):
                w.engine_files_toggle.setChecked(opened);qt.processEvents()
                area=w.settings_tabs.widget(1)
                assert area.horizontalScrollBar().maximum()==0,(kind,opened,area.widget().minimumSizeHint().toTuple())
        assert w.steady_arrows.isChecked()
        w.toggle_compact(True);w.resize(620,900);qt.processEvents()
        assert w.steady_arrows.isVisible() and w.quick_scan_button.geometry().right()<w.width()
    finally:w.close()


def test_steady_arrows_hold_hint_while_raw_evaluation_continues(qt,monkeypatch):
    import chess_helper.hints as hints_module
    w=MainWindow();w.steady_arrows.setChecked(True);w.stick_to_move.setChecked(False)
    clock=[0.];monkeypatch.setattr(hints_module.time,'monotonic',lambda:clock[0])
    def result(move,cp):
        return summarize(w.tracker.board,[{'pv':[chess.Move.from_uci(move)],'score':chess.engine.PovScore(chess.engine.Cp(cp),chess.WHITE),'depth':12}],'QA')
    try:
        w.engine_progress(w.generation,result('e2e4',10));clock[0]=.1
        w.engine_progress(w.generation,result('d2d4',99))
        assert w.result['lines'][0]['move']=='d2d4' and w.eval_bar.cp==99
        assert w.board_view.arrows[0]['move'].uci()=='e2e4'
        clock[0]=.4;w.engine_progress(w.generation,result('d2d4',110))
        assert w.board_view.arrows[0]['move'].uci()=='d2d4' and w.eval_bar.cp==110
        clock[0]=.41;w.engine_finished(w.generation,result('c2c4',45),'')
        assert w.board_view.arrows[0]['move'].uci()=='c2c4'
    finally:w.close()
