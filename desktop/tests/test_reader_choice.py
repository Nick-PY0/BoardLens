import time
import chess
from chess_helper.app import MainWindow
from chess_helper.direct_boards import BrowserReader, exact_read
from chess_helper.live import LiveWorker
from chess_helper.capture import BoardRegion,screen_key
from PySide6.QtGui import QGuiApplication


def wait(qt, condition):
    end=time.monotonic()+5
    while not condition() and time.monotonic()<end:
        qt.processEvents();time.sleep(.01)
    assert condition()


def reader_factory(monkeypatch):
    monkeypatch.setattr('chess_helper.direct_boards.BrowserReader',lambda:BrowserReader(port=0))


def test_reader_choice_is_visible_saved_and_does_not_start_stopped_scanning(qt,monkeypatch):
    reader_factory(monkeypatch);w=MainWindow();w.show()
    try:
        w.source.blockSignals(True);w.source.setCurrentIndex(1);w.source.blockSignals(False);w.source_controls()
        w.readers_toggle.setChecked(False);qt.processEvents()
        assert w.browser_reader_button.isVisible()
        assert not w._monitoring
        w.browser_reader_button.setChecked(True)
        assert w.browser_reader and not w._monitoring
        assert w.readers_toggle.isChecked()
        assert 'fallback' in w.connection_hint.text()
        w.save(quiet=True);w.restore();assert w.browser_reader_button.isChecked()
        w.browser_reader_button.setChecked(False)
        assert not w.browser_reader and not w._monitoring
        w.save(quiet=True);w.restore();assert not w.browser_reader_button.isChecked()
        assert w.connection_hint.text()=='Screen scan · no extension needed'
    finally:w.close()


def test_switching_readers_releases_old_observations_and_browser_lock(qt,monkeypatch):
    reader_factory(monkeypatch);w=MainWindow()
    try:
        w.source.blockSignals(True);w.source.setCurrentIndex(1);w.source.blockSignals(False)
        w.native_reader_button.setChecked(True)
        w.browser_reader_button.setChecked(True);w.update_foreground('browser')
        w.browser_reader.accept({'source':'qa','boards':[{'fen':chess.STARTING_FEN,'white_bottom':True}]})
        w._last_read=exact_read(chess.STARTING_FEN,True,'browser:qa:0');w._screen_confirmed=True
        w.region=BoardRegion(screen_key(QGuiApplication.primaryScreen()),0,0,256,256,256)
        w.lock_target.setChecked(True);assert w.target_lock.active
        old=w.browser_reader;old.publish({'browser:qa:0':{'arrows':[]}})
        token=w._live_token;w._scan_busy=True
        w.browser_reader_button.setChecked(False)
        assert old.hints=={} and not w.target_lock.active and not w.lock_target.isChecked()
        assert w._live_token>token and not w._scan_busy and w._force_full_scan
        assert w.region is None and w._last_read is None and not w._screen_confirmed
        assert w.native_reader_button.isChecked() and not w._monitoring
        assert w.direct_reads()==[]
    finally:w.close()


def test_extension_has_priority_for_2d_and_no_extension_uses_capture(qt,monkeypatch):
    reader_factory(monkeypatch);w=MainWindow();worker=LiveWorker();results=[];captures=[]
    worker.signals.completed.connect(lambda token,reads,error:results.append((token,reads,error)))
    worker.provider=w.direct_reads
    try:
        w.browser_reader_button.setChecked(True);w.update_foreground('browser')
        w.browser_reader.accept({'source':'2d','boards':[{'fen':chess.STARTING_FEN,'white_bottom':True}]})
        def capture(cancelled):captures.append(True);return []
        worker.submit(1,capture);wait(qt,lambda:len(results)==1)
        assert not captures and results[0][1][0][0]=='browser:2d:0'
        # A temporary connection failure also resumes capture without a restart.
        with w.browser_reader.lock:w.browser_reader.frames.clear()
        worker.submit(2,capture);wait(qt,lambda:len(results)==2)
        assert len(captures)==1 and not results[-1][2]
        w.browser_reader_button.setChecked(False)
        worker.submit(3,capture);wait(qt,lambda:len(results)==3)
        assert len(captures)==2 and not results[-1][2]
    finally:worker.close();w.close()
