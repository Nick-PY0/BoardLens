from types import SimpleNamespace
import sys
from chess_helper import native_chess
from chess_helper.app import MainWindow

def test_existing_access_never_opens_an_os_request(monkeypatch):
    calls=[]
    ax=SimpleNamespace(AXIsProcessTrusted=lambda:True,
        AXIsProcessTrustedWithOptions=lambda options:calls.append(options),kAXTrustedCheckOptionPrompt='prompt')
    monkeypatch.setattr(native_chess.sys,'platform','darwin');monkeypatch.setitem(sys.modules,'ApplicationServices',ax)
    assert native_chess.request_access() is True and calls==[]

def test_restoring_or_toggling_local_reader_checks_without_prompting(qt,monkeypatch):
    w=MainWindow();calls=[]
    try:
        monkeypatch.setattr(native_chess,'accessibility_allowed',lambda:False)
        monkeypatch.setattr(native_chess,'request_access',lambda:calls.append('prompt'))
        monkeypatch.setattr(native_chess.sys,'platform','darwin');monkeypatch.delenv('BOARDLENS_TEST_MODE',raising=False)
        w._ready=False;w.native_access_changed(True)
        w._ready=True;w.native_access_changed(True)
        assert calls==[] and w._native_access_ok is False
        assert 'Permissions' in w.status_label.text()
        monkeypatch.setattr(native_chess,'accessibility_allowed',lambda:True)
        w.native_access_changed(True);assert w._native_access_ok is True and calls==[]
    finally:w.close()
