import json,time,urllib.request,urllib.error
import chess,pytest
from chess_helper.direct_boards import BrowserReader,exact_read
from chess_helper.recognition import position_from_read
from chess_helper.app import MainWindow


def test_reader_keeps_exact_metadata_and_flipped_orientation(qt,monkeypatch):
    w=MainWindow();w.source.blockSignals(True);w.source.setCurrentIndex(1);w.source.blockSignals(False)
    w._monitoring=True;monkeypatch.setattr(w,'suggest',lambda **kw:None)
    board=chess.Board();board.push_uci('e2e4');read=exact_read(board.fen(),False,'browser:qa:0')
    assert position_from_read(read)[0].fen()==board.fen()
    answer=('browser:qa:0','QA 3D reader',read,256,256)
    try:
        for _ in range(2):w.live_finished(w._live_token,[answer],'')
        assert w.tracker.board.fen()==board.fen() and not w.white_bottom
        assert w._screen_confirmed
        w.browser_reader=BrowserReader(port=0);w.publish_reader_hints()
        assert w.browser_reader.hints['browser:qa:0']['fen']==board.fen()
        w.stop();w.publish_reader_hints();assert w.browser_reader.hints=={}
    finally:w.close()


def test_browser_service_is_loopback_authenticated_and_positions_only():
    reader=BrowserReader(port=0)
    def request(data,token):
        req=urllib.request.Request(f'http://127.0.0.1:{reader.port}/boards',data=json.dumps(data).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req) as r:return r.status
        except urllib.error.HTTPError as e:return e.code
    payload={'source':'qa','boards':[{'fen':chess.STARTING_FEN,'white_bottom':True}]}
    try:
        assert reader.http.server_address[0]=='127.0.0.1'
        assert request(payload,'bad')==401 and reader.reads()==[]
        assert request(payload,reader.token)==200 and len(reader.reads())==1
        assert request({'source':'qa','boards':[{'fen':'bad','white_bottom':True}]},reader.token)==400
        assert len(reader.reads())==1
        with reader.lock:reader.frames['qa']=(time.monotonic()-2,reader.frames['qa'][1])
        assert reader.reads()==[]
    finally:reader.close()


def test_browser_reader_yields_immediately_when_switching_apps(qt):
    w=MainWindow();w.browser_reader=BrowserReader(port=0)
    try:
        w.browser_reader.accept({'source':'qa','boards':[{'fen':chess.STARTING_FEN,'white_bottom':True}]})
        w.update_foreground('browser');assert len(w.direct_reads())==1
        w._last_read=w.direct_reads()[0][2];w._screen_confirmed=True;w._position_locked=True
        w.update_foreground('other')
        assert w.direct_reads()==[] and w.region is None and w._last_read is None
        assert w._force_full_scan and not w._position_locked
        w.update_foreground('self');assert w._scan_route=='other'
        w.update_foreground('browser');assert len(w.direct_reads())==1
    finally:w.close()


def test_manual_rescan_remembers_the_other_app_while_stopped(qt,monkeypatch):
    w=MainWindow();w.browser_reader=BrowserReader(port=0)
    try:
        w.update_foreground('browser');w.stop()
        monkeypatch.setattr('chess_helper.app.foreground_kind',lambda:'other');w.poll()
        assert w._last_external_route=='other'
        token=w._live_token;w._scan_busy=True
        w.update_foreground('self')
        assert w._scan_route=='other' and not w._scan_busy and w._live_token>token
        assert w._force_full_scan
    finally:w.close()


def test_native_chess_coordinates_convert_from_appkit_to_desktop():
    from types import SimpleNamespace
    from chess_helper.native_chess import projected_center
    assert projected_center(SimpleNamespace(x=100,y=200),SimpleNamespace(width=40,height=20),982)==(120,772)


def test_reader_reports_connection_and_pairing_repair():
    reader=BrowserReader(port=0)
    try:
        assert 'Waiting' in reader.connection_status()
        reader.accept({'source':'qa','boards':[{'fen':chess.STARTING_FEN,'white_bottom':True}]})
        assert reader.connection_status()=='Connected · 1 visible board'
        reader.rejected_at=time.monotonic()+.001
        assert 'Needs pairing' in reader.connection_status()
    finally:reader.close()
