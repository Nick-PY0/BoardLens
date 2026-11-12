from chess_helper.app import MainWindow
from chess_helper.permissions import Access, Permissions


def setup_window(qt, allowed):
    w = MainWindow()
    state = [allowed]
    w.permissions = Permissions(w, lambda: state[0])
    w.source.setCurrentIndex(1)
    return w, state


def test_first_live_scan_requires_access_and_practice_still_works(qt, monkeypatch):
    w, state = setup_window(qt, Access(False, False))
    calls = []
    monkeypatch.setattr(w.live_worker, 'submit', lambda *args: calls.append(args))
    try:
        w.scan_now()
        assert w.permissions.blocked
        assert w.workspace_stack.currentWidget() is w.permissions.page
        assert not w._monitoring and not calls
        assert 'Screen Recording' in w.status_label.text()
        w.status('Searching for a chessboard')
        assert 'permission required' in w.status_label.text()
        w.source.setCurrentIndex(0)
        w.permissions.refresh()
        assert not w.permissions.blocked
        assert w.workspace_stack.currentWidget() is not w.permissions.page
    finally:
        w.close()


def test_revocation_cancels_work_and_grant_resumes_a_fresh_scan(qt, monkeypatch):
    w, state = setup_window(qt, Access(True, False))
    rescans = []
    try:
        w._monitoring = True
        w._screen_confirmed = True
        w.region = object()
        state[0] = Access(False, False)
        w.permissions.refresh()
        assert w.permissions.blocked and not w._monitoring
        assert w.region is None and not w._screen_confirmed
        assert not w.overlay.isVisible()
        monkeypatch.setattr(w, 'scan_now', lambda: rescans.append('fresh'))
        state[0] = Access(True, False)
        w.permissions.refresh()
        assert not w.permissions.blocked and rescans == ['fresh']
    finally:
        w.close()


def test_stop_while_waiting_does_not_auto_resume(qt, monkeypatch):
    w, state = setup_window(qt, Access(False, False))
    rescans = []
    try:
        w.scan_now()
        w.stop()
        monkeypatch.setattr(w, 'scan_now', lambda: rescans.append('unexpected'))
        state[0] = Access(True, False)
        w.permissions.refresh()
        assert not rescans
    finally:
        w.close()
