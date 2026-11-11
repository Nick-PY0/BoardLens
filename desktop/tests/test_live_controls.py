import threading
import time
from pathlib import Path

import chess
import chess.engine
import cv2
import numpy as np
import pytest

from chess_helper.app import MainWindow,SCREEN_REFRESH_MS
from chess_helper.core import PositionTracker,SearchSettings,find_engine,ordered_symbols
from chess_helper.engine import EngineJob,EngineSession,summarize
from chess_helper.recognition import Recognizer
from chess_helper.vision import Detection,complete_grid


def analysis(board):
    move=next(iter(board.legal_moves));probe=board.copy();probe.push(move)
    pv=[move]
    if not probe.is_game_over():pv.append(next(iter(probe.legal_moves)))
    return summarize(board,[{'pv':pv,'score':chess.engine.PovScore(chess.engine.Cp(25),board.turn),'depth':12}], 'test engine')


@pytest.mark.parametrize('bottom',[True,False])
def test_only_my_color_hides_opponent_and_follows_orientation(qt,bottom):
    window=MainWindow()
    window._white_bottom=bottom
    window.only_my_color.setChecked(True)
    window.result=analysis(window.tracker.board)
    window.render_result(window.result)
    assert window.allowed_colors()==(bottom,False)
    assert bool(window.board_view.arrows)==bottom
    assert not any(a.get('reply') for a in window.board_view.arrows)
    assert not window.show_white.isEnabled() and not window.show_black.isEnabled()
    assert not window.reply_label.text()
    board=chess.Board();board.push_uci('e2e4')
    window.tracker=PositionTracker(board)
    window.result=analysis(board)
    window.render_result(window.result)
    assert window.allowed_colors()==(not bottom,False)
    assert bool(window.board_view.arrows)==(not bottom)
    window.only_my_color.setChecked(False)
    assert window.allowed_colors()==(True,True)
    assert window.show_white.isEnabled()
    window.close()


def test_compact_keeps_geometry_and_settings_are_always_available(qt):
    window=MainWindow();window.show();qt.processEvents()
    geometry=window.geometry()
    for _ in range(3):
        window.toggle_compact(True);qt.processEvents()
        assert window.geometry()==geometry
        assert window.settings_button.isVisible()
        window.toggle_compact(False);qt.processEvents()
        assert window.geometry()==geometry
    window.settings_button.click();qt.processEvents()
    assert window.sidebar_host.isVisible() and window.settings_tabs.isVisible()
    assert window.settings_tabs.parentWidget()==window.sidebar_host
    window.toggle_compact(True)
    window.settings_button.click();qt.processEvents()
    assert window.settings_dialog.isVisible() and window.settings_tabs.isVisible()
    assert [window.settings_tabs.tabText(i) for i in range(4)]==['Board','Engine','Keys','Arrows']
    assert not window.findChildren(type(window.settings_button),'Manual crop…')
    window.close()


def test_scan_now_cancels_busy_scan_and_starts_fresh(qt,monkeypatch):
    window=MainWindow()
    window.source.blockSignals(True);window.source.setCurrentIndex(1);window.source.blockSignals(False)
    window._scan_busy=True
    window.region=object()
    window.result=analysis(window.tracker.board)
    old_token=window._live_token
    calls=[]
    monkeypatch.setattr(window,'request_scan',lambda **kw:calls.append(kw))
    window.scan_now()
    assert calls==[{'force':True}]
    assert window.region is None and window.result is None and window._last_read is None
    assert window.board_view.isHidden()
    assert window._force_full_scan and window._monitoring and window.live_button.isChecked()
    assert window._live_token>old_token and not window._scan_busy
    window.live_finished(old_token,None,'old frame')
    assert window.status_label.text().startswith('Refreshing')
    window.stop()
    assert not window._scan_again
    window.close()


def test_history_pauses_live_until_resume(qt,monkeypatch):
    window=MainWindow()
    window.source.blockSignals(True);window.source.setCurrentIndex(1);window.source.blockSignals(False)
    window.remember_position()
    window.tracker.board.push_uci('e2e4');window.remember_position()
    window.tracker.board.push_uci('e7e5');window.remember_position()
    latest=window.tracker.board.fen()
    window._monitoring=True
    window.history_previous()
    assert window._reviewing and not window._monitoring
    assert window.tracker.board.fullmove_number==1 and window.tracker.board.turn==chess.BLACK
    assert not window.overlay.isVisible()
    window.history_previous()
    assert window.tracker.board.fen()==chess.STARTING_FEN
    window.history_next()
    assert window.tracker.board.turn==chess.BLACK
    monkeypatch.setattr(window,'request_scan',lambda *a,**kw:None)
    window.resume_live()
    assert not window._reviewing and window._monitoring
    assert window.tracker.board.fen()==latest
    window.close()


@pytest.mark.parametrize('turn,cp',[(chess.WHITE,130),(chess.BLACK,130),(chess.BLACK,-130)])
def test_eval_perspective_and_plain_language(qt,turn,cp):
    window=MainWindow();board=chess.Board()
    if not turn:board.push_uci('e2e4')
    window.tracker=PositionTracker(board)
    move=next(iter(board.legal_moves))
    result=summarize(board,[{'pv':[move],'score':chess.engine.PovScore(chess.engine.Cp(cp),turn)}],'test')
    window.render_result(result)
    assert window.eval_bar.cp==(cp if turn else -cp)
    assert ('White:' if turn else 'Black:') in window.simple_label.text()
    assert '100%' not in window.lines.toPlainText()
    window.close()


def test_warm_engine_streams_before_the_selected_time_and_reuses_process():
    path=find_engine()
    if not path:pytest.skip('Stockfish not installed')
    session=EngineSession()
    job=EngineJob();job.session=session
    updates=[];started=time.monotonic()
    job.on_update=lambda result:updates.append((time.monotonic()-started,result))
    try:
        final=job.run(path,chess.Board(),SearchSettings(seconds=.8,multipv=2))
        elapsed=time.monotonic()-started
        assert updates and updates[0][0]<elapsed-.15
        assert elapsed>=.75 and len(final['lines'])==2
        pid=session.engine.transport.get_pid()
        board=chess.Board();board.push_uci('e2e4')
        second=EngineJob();second.session=session
        second.run(path,board,SearchSettings(seconds=.1,multipv=1))
        assert session.engine.transport.get_pid()==pid
    finally:session.close()


def test_native_shortcut_parser_matches_mac_keys():
    from chess_helper.mac_hotkeys import parse_combo
    assert parse_combo('<ctrl>+<alt>+s')==(1,6144)
    assert parse_combo('<ctrl>+<alt>+left')==(123,6144)
    assert parse_combo('<cmd>+<shift>+b')==(11,768)
    with pytest.raises(ValueError):parse_combo('s')


def test_shifted_start_board_hint_reacquires_outer_files(qt,render_board):
    image=np.full((800,1000,3),28,np.uint8)
    board=render_board(chess.Board())
    image[130:642,220:732]=board
    recognizer=Recognizer()
    read=recognizer.scan(image,(284,130,512))
    assert read is not None
    assert read.symbols==ordered_symbols(chess.Board())
    assert abs(read.detection.x-220)<8


def test_live_move_orientation_is_preserved_in_pawnless_endgame(qt):
    from chess_helper.recognition import Read
    from chess_helper.capture import screen_key
    from PySide6.QtGui import QGuiApplication
    window=MainWindow()
    window.source.blockSignals(True);window.source.setCurrentIndex(1);window.source.blockSignals(False)
    board=chess.Board('8/8/8/8/3k4/8/4K3/4R3 w - - 0 1')
    window.tracker=PositionTracker(board);window._position_locked=True
    window._white_bottom=False
    symbols=ordered_symbols(board,False)
    read=Read(symbols,np.ones(64),np.ones((64,13)),True,None,np.zeros((512,512,3),np.uint8),Detection(0,0,512,1))
    key=screen_key(QGuiApplication.primaryScreen())
    window.live_finished(window._live_token,(key,'test',read,800,800),'')
    assert window.white_bottom is False
    window.close()


def test_single_uncertain_read_keeps_arrow_but_persistent_loss_hides_it(qt,monkeypatch):
    window=MainWindow()
    window._monitoring=True
    window._screen_confirmed=True
    visible=[True];hidden=[]
    monkeypatch.setattr(window.overlay,'hide',lambda:hidden.append(True))
    monkeypatch.setattr(window.overlay,'isVisible',lambda:visible[0])
    window.live_finished(window._live_token,None,'')
    assert not hidden and not window._screen_confirmed
    window.live_finished(window._live_token,None,'')
    assert not hidden
    window.live_finished(window._live_token,None,'')
    assert hidden and window._overlay_grace_until==0
    window.stop()
    assert not window._monitoring
    window.close()


def test_custom_local_shortcut_dispatches_chosen_action(qt,monkeypatch):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    window=MainWindow();window.show();window.activateWindow();window.setFocus();qt.processEvents()
    actions=[]
    monkeypatch.setattr(window,'dispatch',actions.append)
    window.key_fields['suggest'].setText('<ctrl>+<alt>+z')
    window.apply_keys();qt.processEvents()
    QTest.keyClick(window,Qt.Key.Key_Z,Qt.KeyboardModifier.ControlModifier|Qt.KeyboardModifier.AltModifier)
    qt.processEvents()
    assert actions==['suggest']
    window.close()


def test_scan_now_resets_to_visible_board_and_restarts_analysis_after_stop(qt,monkeypatch,render_board):
    from chess_helper.capture import screen_key
    from PySide6.QtGui import QGuiApplication
    window=MainWindow()
    window.source.blockSignals(True);window.source.setCurrentIndex(1);window.source.blockSignals(False)
    window.stop()
    monkeypatch.setattr(window,'request_scan',lambda **kw:None)
    seen=[]
    monkeypatch.setattr(window,'suggest',lambda **kw:seen.append(window.tracker.board.fen()))
    board=chess.Board();board.push_uci('e2e4')
    read=Recognizer().read(render_board(board));read.detection=Detection(0,0,512,1.)
    window.scan_now()
    assert window._monitoring and window.live_button.isChecked()
    key=screen_key(QGuiApplication.primaryScreen())
    answer=(key,'test',read,800,800)
    window.live_finished(window._live_token,answer,'')
    window.live_finished(window._live_token,answer,'')
    assert window.tracker.board.fen()==board.fen()
    assert seen==[board.fen()]
    window.close()
