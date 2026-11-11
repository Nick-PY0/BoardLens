from copy import deepcopy
from types import SimpleNamespace
import chess
import pytest
from PySide6.QtCore import QRect
from chess_helper.presets import PresetStore
from chess_helper.threats import analyze,presentation
from chess_helper.target_lock import TargetLock
from chess_helper.capture import BoardRegion
from chess_helper.core import load_settings
from chess_helper.app import MainWindow,SCREEN_REFRESH_MS


def test_threats_find_material_loss_and_respect_pinned_attackers():
    hanging=chess.Board('4k3/8/8/8/8/8/q7/R3K3 b - - 0 1');report=analyze(hanging.fen())
    assert any(p['square']==chess.A1 and p['color'] for p in report['hanging'])
    # Black rook e6 is pinned to its king by White's e1 rook.
    pinned=chess.Board('4k3/8/3Qr3/8/8/8/8/K3R3 b - - 0 1')
    assert pinned.is_valid() and not any(p['square']==chess.D6 for p in analyze(pinned.fen())['hanging'])
    defended=chess.Board('4k3/8/8/4p3/3P4/2P5/8/4K3 b - - 0 1')
    assert not any(p['square']==chess.D4 for p in analyze(defended.fen())['hanging'])

def test_mate_targets_and_attack_maps_are_optional():
    board=chess.Board();[board.push_uci(m) for m in ('f2f3','e7e5','g2g4')]
    report=analyze(board.fen());assert any(m['move']=='d8h4' for m in report['mates'])
    assert presentation(board,True,False)==([],[])
    marks,text=presentation(board,True,True,True,True)
    assert any(m['kind']=='mate' and m['square']==chess.H4 for m in marks)
    assert any(m['kind']=='attack' for m in marks) and any('mate in one' in t for t in text)
    assert not any(m['kind']=='mate' for m in presentation(board,True,True,False,False)[0])

def test_named_presets_roundtrip_and_missing_engine_does_not_mutate(qt):
    w=MainWindow()
    try:
        w.seconds.setValue(.7);w.depth.setValue(19);w.recommendation_preset(3);w.threats_enabled.setChecked(True)
        identity=w.analysis_presets.save_preset('My training');w.seconds.setValue(3);w.multipv.setValue(1);w.threats_enabled.setChecked(False)
        w.analysis_presets.apply_preset(identity)
        assert w.seconds.value()==.7 and w.depth.value()==19 and w.multipv.value()==3 and w.arrow_count.value()==3 and w.threats_enabled.isChecked()
        assert w.timer.interval()==SCREEN_REFRESH_MS==75
        assert w.preset_combo.currentData()==identity
        w.seconds.setValue(.8);assert w.preset_combo.currentData() is None
        bad=w.analysis_presets.store.save('Missing custom',{'engine_identity':'custom','custom_engine':'/nonexistent/engine','seconds':2.})
        before=w.search_settings()
        with pytest.raises(ValueError):w.analysis_presets.apply_preset(bad)
        assert w.search_settings()==before
        w.save(quiet=True);assert load_settings()['seconds']==.8 and load_settings()['threats_enabled']
    finally:w.close()

def test_preset_store_protects_builtins_and_saves_custom(tmp_path):
    path=tmp_path/'presets.json';store=PresetStore(path);identity=store.save('Custom',{'engine_identity':'stockfish','seconds':.8})
    assert PresetStore(path).get(identity)['settings']['seconds']==.8
    with pytest.raises(ValueError):store.delete('quick')
    with pytest.raises(ValueError):store.save('Bad',{'screen_refresh':999})
    store.delete(identity);assert len(store.list())==2

def test_target_lock_filters_sources_and_covered_window(monkeypatch):
    lock=TargetLock();region=BoardRegion('display',1000,1000,20,30,400)
    monkeypatch.setattr('chess_helper.target_lock.window_at',lambda *args,**kwargs:{'id':44,'pid':10})
    read=SimpleNamespace(source_id='native:10:board',desktop_rect=(20,30,400,400))
    lock.capture(read,region,'native');assert lock.active and lock.route=='native'
    other=SimpleNamespace(source_id='browser:20:1')
    answer=('display','Display',read,1000,1000);wrong=('display','Display',other,1000,1000)
    assert lock.filter([wrong,answer])==[answer] and lock.overlay_visible()
    saved=deepcopy(lock.target);restored=TargetLock();assert restored.restore(saved)
    monkeypatch.setattr('chess_helper.target_lock.window_at',lambda *args,**kwargs:{'id':55})
    assert not lock.pixel_visible();lock.clear();assert lock.filter([wrong])==[wrong]
    assert not lock.restore({'route':'native','region':{}})

def test_pixel_target_lock_will_not_pick_other_boards(monkeypatch):
    lock=TargetLock();region=BoardRegion('display',1000,1000,20,30,400)
    monkeypatch.setattr('chess_helper.target_lock.window_at',lambda *args,**kwargs:None)
    read=SimpleNamespace(source_id=None,desktop_rect=None,detection=SimpleNamespace(x=20,y=30,size=400))
    lock.capture(read,region,'other');answer=('display','Display',read,1000,1000)
    wrong=('display','Display',SimpleNamespace(source_id=None,detection=SimpleNamespace(x=550,y=30,size=400)),1000,1000)
    assert lock.filter([wrong,answer])==[answer]

def test_marks_only_overlay_remains_click_through(qt):
    from chess_helper.overlay import BoardOverlay
    from PySide6.QtCore import Qt
    overlay=BoardOverlay();marks=[{'square':chess.E4,'color':'#ff7185','kind':'hanging'}]
    overlay.set_arrows(QRect(0,0,400,400),True,[],None,marks);qt.processEvents()
    assert overlay.isVisible() and overlay.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    assert overlay.windowFlags()&Qt.WindowType.WindowDoesNotAcceptFocus
    assert not overlay.grab().toImage().isNull();overlay.close()

def test_locked_source_survives_app_switch_and_missing_reader_does_not_fall_back(qt,monkeypatch):
    from chess_helper.direct_boards import exact_read
    w=MainWindow();w.source.blockSignals(True);w.source.setCurrentIndex(1);w.source.blockSignals(False)
    read=exact_read(chess.STARTING_FEN,True,'browser:target:0');answer=('browser:target:0','Reader',read,256,256)
    w._monitoring=True;monkeypatch.setattr(w,'suggest',lambda **kw:None)
    monkeypatch.setattr('chess_helper.target_lock.window_at',lambda *args,**kwargs:None)
    try:
        w.live_finished(w._live_token,[answer],'');w.live_finished(w._live_token,[answer],'');assert w._screen_confirmed
        w.lock_target.setChecked(True);assert w.target_lock.active
        w.update_foreground('native');assert w._scan_route==w.target_lock.route
        wrong_read=exact_read(chess.STARTING_FEN,True,'browser:other:0')
        w.live_finished(w._live_token,[('browser:other:0','Other',wrong_read,256,256)],'')
        assert getattr(w._last_read,'source_id')=='browser:target:0'
        assert 'Locked board unavailable' in w.status_label.text()
        w.save(quiet=True);assert load_settings()['target_lock']['source']=='browser:target:0'
        w.settings=load_settings();w.restore();assert w.target_lock.active and w.lock_target.isChecked()
        w.lock_target.setChecked(False);assert not w.target_lock.active
    finally:w.close()

def test_connection_menus_hide_inactive_pairing_and_separate_local_chess_status(qt,monkeypatch):
    class Reader:
        token='test-pairing-key'
        def connection_status(self):return 'Connected · 1 board'
        def publish(self,value):pass
        def close(self):pass
    monkeypatch.setattr('chess_helper.direct_boards.BrowserReader',Reader)
    w=MainWindow();w.show()
    try:
        assert w.screen_setup.isHidden()
        w.source.blockSignals(True);w.source.setCurrentIndex(1);w.source.blockSignals(False);w.source_controls();w.readers_toggle.setChecked(True);qt.processEvents()
        assert w.screen_setup.isVisible() and w.reader_options.isVisible()
        assert not w.browser_connection_details.isVisible()
        assert 'Connect browser'==w.browser_reader_button.text()
        w.native_reader_button.setChecked(True);w.publish_reader_hints();qt.processEvents()
        assert 'local 3D chess' in w.native_connection_status.text()
        assert not w.browser_connection_details.isVisible()
        w.browser_reader_button.setChecked(True);w.publish_reader_hints();qt.processEvents()
        assert w.browser_connection_details.isVisible() and w.browser_reader_key.text()=='test-pairing-key'
        area=w.settings_tabs.widget(0);assert area.widget().width()<=area.viewport().width()
        assert 'Connected' in w.browser_reader_status.text()
        w.browser_reader_button.setChecked(False);assert not w.browser_connection_details.isVisible()
        assert w.native_reader_button.isChecked()
    finally:w.close()

def test_sidebar_fits_all_engines_and_long_saved_preset_names(qt):
    w=MainWindow();w.show();w.resize(1400,900)
    try:
        w.analysis_presets.save_preset('A saved training configuration with a deliberately long name')
        for tab in range(w.settings_tabs.count()):
            w.settings_tabs.setCurrentIndex(tab);qt.processEvents();area=w.settings_tabs.widget(tab)
            assert area.widget().width()<=area.viewport().width()
        w.settings_tabs.setCurrentIndex(1)
        for index in range(w.engine_kind.count()):
            w.engine_kind.setCurrentIndex(index);qt.processEvents();area=w.settings_tabs.widget(1)
            assert area.widget().width()<=area.viewport().width()
    finally:w.close()
